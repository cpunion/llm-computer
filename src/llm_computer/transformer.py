"""Tiny transformer-style execution verification for a restricted WASM subset."""

from __future__ import annotations

from dataclasses import dataclass
import time

from llm_computer.executor import HullTimeline, NaiveTimeline, PrefixSumCounter, Timeline
from llm_computer.hull import NaiveCache
from llm_computer.wasm import ExecutionResult, TraceEntry, WasmFunction, WasmInstruction, WasmOpcode, mask_u32, to_signed_i32


SUPPORTED_OPCODES = {
    WasmOpcode.BLOCK,
    WasmOpcode.LOOP,
    WasmOpcode.IF,
    WasmOpcode.ELSE,
    WasmOpcode.END,
    WasmOpcode.I32_CONST,
    WasmOpcode.LOCAL_GET,
    WasmOpcode.LOCAL_SET,
    WasmOpcode.LOCAL_TEE,
    WasmOpcode.I32_LOAD,
    WasmOpcode.I32_STORE,
    WasmOpcode.I32_LT_S,
    WasmOpcode.I32_GT_S,
    WasmOpcode.I32_LE_S,
    WasmOpcode.I32_ADD,
    WasmOpcode.I32_SUB,
    WasmOpcode.I32_MUL,
    WasmOpcode.I32_EQZ,
    WasmOpcode.BR,
    WasmOpcode.BR_IF,
}


@dataclass(slots=True)
class TransformerRunStats:
    name: str
    elapsed_s: float
    steps: int
    tokens_per_s: float
    results: list[int]


@dataclass(slots=True)
class DecodedInstruction:
    opcode: WasmOpcode
    immediate: int | None = None
    branch_target: int | None = None
    end_target: int | None = None
    false_target: int | None = None
    memory_align: int | None = None
    memory_offset: int | None = None

    def as_wasm_instruction(self) -> WasmInstruction:
        return WasmInstruction(
            opcode=self.opcode,
            immediate=self.immediate,
            branch_target=self.branch_target,
            end_target=self.end_target,
            false_target=self.false_target,
            memory_align=self.memory_align,
            memory_offset=self.memory_offset,
        )


class StaticFieldHead:
    """A static attention head over program tokens indexed by instruction pointer."""

    def __init__(self, values: list[int]) -> None:
        self._cache = NaiveCache()
        for index, value in enumerate(values):
            self._cache.insert((2.0 * index, -(index ** 2)), float(value))

    def read(self, instruction_index: int) -> int:
        return int(self._cache.query((float(instruction_index), 1.0)))


class DynamicStateHead:
    """A dynamic append-only attention head over execution steps."""

    def __init__(self, timeline_cls: type[Timeline]) -> None:
        self._timeline = timeline_cls()

    def write(self, step: int, value: int) -> None:
        self._timeline.insert(step, mask_u32(value))

    def read(self, step: int) -> int:
        return self._timeline.query(step)


def supports_transformer_verification(function: WasmFunction) -> bool:
    for instruction in function.instructions:
        if instruction.opcode not in SUPPORTED_OPCODES:
            return False
    return True


class TinyExecutionTransformer:
    """A hand-wired transformer-style executor for a restricted WASM subset."""

    def __init__(self, function: WasmFunction, timeline_cls: type[Timeline]) -> None:
        if not supports_transformer_verification(function):
            raise ValueError("Function is outside the transformer verification subset")

        self.function = function
        self.timeline_cls = timeline_cls
        self.trace: list[TraceEntry] = []
        self.locals_snapshot = [0] * function.local_count
        self.results: list[int] = []
        self.depth_counter = PrefixSumCounter()

        self.ip_head = DynamicStateHead(timeline_cls)
        self.local_heads = [DynamicStateHead(timeline_cls) for _ in range(function.local_count)]
        self.stack_heads: dict[int, DynamicStateHead] = {}
        self.memory_heads: dict[int, DynamicStateHead] = {}

        self.opcode_head = StaticFieldHead([int(instruction.opcode) for instruction in function.instructions])
        self.immediate_head = StaticFieldHead([(instruction.immediate or 0) for instruction in function.instructions])
        self.branch_head = StaticFieldHead([(instruction.branch_target or 0) for instruction in function.instructions])
        self.end_head = StaticFieldHead([(instruction.end_target or 0) for instruction in function.instructions])
        self.false_head = StaticFieldHead([(instruction.false_target or 0) for instruction in function.instructions])
        self.memory_align_head = StaticFieldHead([(instruction.memory_align or 0) for instruction in function.instructions])
        self.memory_offset_head = StaticFieldHead([(instruction.memory_offset or 0) for instruction in function.instructions])
        for address, byte in function.initial_memory.items():
            self._memory_head(address).write(-1, byte)

    def _depth_before(self, step: int) -> int:
        return self.depth_counter.query(step)

    def _stack_head(self, slot: int) -> DynamicStateHead:
        if slot not in self.stack_heads:
            self.stack_heads[slot] = DynamicStateHead(self.timeline_cls)
        return self.stack_heads[slot]

    def _stack_read(self, slot: int, step: int) -> int:
        if slot < 0:
            return 0
        head = self.stack_heads.get(slot)
        if head is None:
            return 0
        return head.read(step)

    def _stack_write(self, slot: int, step: int, value: int) -> None:
        if slot < 0:
            return
        self._stack_head(slot).write(step, value)

    def _local_read(self, index: int, step: int) -> int:
        if not 0 <= index < len(self.local_heads):
            return 0
        return self.local_heads[index].read(step)

    def _local_write(self, index: int, step: int, value: int) -> None:
        if not 0 <= index < len(self.local_heads):
            return
        masked = mask_u32(value)
        self.local_heads[index].write(step, masked)
        self.locals_snapshot[index] = masked

    def _memory_head(self, address: int) -> DynamicStateHead:
        if address not in self.memory_heads:
            self.memory_heads[address] = DynamicStateHead(self.timeline_cls)
        return self.memory_heads[address]

    def _check_memory_bounds(self, address: int, size: int) -> None:
        if address < 0:
            raise ValueError("Negative memory access")
        limit = self.function.initial_memory_pages * 65536
        if address + size > limit:
            raise ValueError("Out-of-bounds memory access")

    def _memory_read_i32(self, address: int, step: int) -> int:
        self._check_memory_bounds(address, 4)
        value = 0
        for offset in range(4):
            head = self.memory_heads.get(address + offset)
            byte_value = head.read(step) if head is not None else 0
            value |= (byte_value & 0xFF) << (offset * 8)
        return mask_u32(value)

    def _memory_write_i32(self, address: int, step: int, value: int) -> None:
        self._check_memory_bounds(address, 4)
        masked = mask_u32(value)
        for offset in range(4):
            self._memory_head(address + offset).write(step, (masked >> (offset * 8)) & 0xFF)

    def _current_ip(self, step: int) -> int:
        if step == 0:
            return 0
        return self.ip_head.read(step)

    def _read_instruction(self, ip: int) -> DecodedInstruction:
        opcode = WasmOpcode(self.opcode_head.read(ip))
        raw_immediate = self.immediate_head.read(ip)
        branch_target = self.branch_head.read(ip)
        end_target = self.end_head.read(ip)
        false_target = self.false_head.read(ip)
        memory_align = self.memory_align_head.read(ip)
        memory_offset = self.memory_offset_head.read(ip)
        immediate_opcodes = {
            WasmOpcode.BLOCK,
            WasmOpcode.LOOP,
            WasmOpcode.IF,
            WasmOpcode.I32_CONST,
            WasmOpcode.LOCAL_GET,
            WasmOpcode.LOCAL_SET,
            WasmOpcode.LOCAL_TEE,
            WasmOpcode.BR,
            WasmOpcode.BR_IF,
        }
        return DecodedInstruction(
            opcode=opcode,
            immediate=raw_immediate if opcode in immediate_opcodes else None,
            branch_target=branch_target if opcode in {WasmOpcode.BR, WasmOpcode.BR_IF} else None,
            end_target=end_target if end_target != 0 else None,
            false_target=false_target if false_target != 0 else None,
            memory_align=memory_align if opcode in {WasmOpcode.I32_LOAD, WasmOpcode.I32_STORE} else None,
            memory_offset=memory_offset if opcode in {WasmOpcode.I32_LOAD, WasmOpcode.I32_STORE} else None,
        )

    def _collect_results(self, step: int, depth: int) -> list[int]:
        if self.function.result_count == 0:
            return []
        base = depth - self.function.result_count
        return [mask_u32(self._stack_read(base + offset, step)) for offset in range(self.function.result_count)]

    def _transition(
        self,
        instruction: DecodedInstruction,
        ip: int,
        step: int,
        depth_before: int,
    ) -> tuple[int, int, int, bool]:
        branch_taken = False
        value = 0
        depth_after = depth_before
        next_ip = ip + 1

        if instruction.opcode in {WasmOpcode.BLOCK, WasmOpcode.LOOP, WasmOpcode.END}:
            return next_ip, depth_after, value, branch_taken

        if instruction.opcode == WasmOpcode.IF:
            cond = self._stack_read(depth_before - 1, step)
            depth_after -= 1
            if cond == 0:
                return instruction.false_target or instruction.end_target or next_ip, depth_after, 0, True
            return next_ip, depth_after, 0, False

        if instruction.opcode == WasmOpcode.ELSE:
            return instruction.end_target or next_ip, depth_after, 0, True

        if instruction.opcode == WasmOpcode.I32_CONST:
            value = instruction.immediate or 0
            self._stack_write(depth_before, step, value)
            return next_ip, depth_before + 1, value, branch_taken

        if instruction.opcode == WasmOpcode.LOCAL_GET:
            index = instruction.immediate or 0
            value = self._local_read(index, step)
            self._stack_write(depth_before, step, value)
            return next_ip, depth_before + 1, value, branch_taken

        if instruction.opcode == WasmOpcode.LOCAL_SET:
            index = instruction.immediate or 0
            value = self._stack_read(depth_before - 1, step)
            self._local_write(index, step, value)
            return next_ip, depth_before - 1, value, branch_taken

        if instruction.opcode == WasmOpcode.LOCAL_TEE:
            index = instruction.immediate or 0
            value = self._stack_read(depth_before - 1, step)
            self._local_write(index, step, value)
            return next_ip, depth_before, value, branch_taken

        if instruction.opcode == WasmOpcode.I32_LOAD:
            base = self._stack_read(depth_before - 1, step)
            address = base + (instruction.memory_offset or 0)
            value = self._memory_read_i32(address, step)
            self._stack_write(depth_before - 1, step, value)
            return next_ip, depth_before, value, branch_taken

        if instruction.opcode == WasmOpcode.I32_STORE:
            value = self._stack_read(depth_before - 1, step)
            base = self._stack_read(depth_before - 2, step)
            address = base + (instruction.memory_offset or 0)
            self._memory_write_i32(address, step, value)
            return next_ip, depth_before - 2, value, branch_taken

        if instruction.opcode == WasmOpcode.I32_LT_S:
            rhs = self._stack_read(depth_before - 1, step)
            lhs = self._stack_read(depth_before - 2, step)
            value = 1 if to_signed_i32(lhs) < to_signed_i32(rhs) else 0
            self._stack_write(depth_before - 2, step, value)
            return next_ip, depth_before - 1, value, branch_taken

        if instruction.opcode == WasmOpcode.I32_GT_S:
            rhs = self._stack_read(depth_before - 1, step)
            lhs = self._stack_read(depth_before - 2, step)
            value = 1 if to_signed_i32(lhs) > to_signed_i32(rhs) else 0
            self._stack_write(depth_before - 2, step, value)
            return next_ip, depth_before - 1, value, branch_taken

        if instruction.opcode == WasmOpcode.I32_LE_S:
            rhs = self._stack_read(depth_before - 1, step)
            lhs = self._stack_read(depth_before - 2, step)
            value = 1 if to_signed_i32(lhs) <= to_signed_i32(rhs) else 0
            self._stack_write(depth_before - 2, step, value)
            return next_ip, depth_before - 1, value, branch_taken

        if instruction.opcode == WasmOpcode.I32_ADD:
            rhs = self._stack_read(depth_before - 1, step)
            lhs = self._stack_read(depth_before - 2, step)
            value = lhs + rhs
            self._stack_write(depth_before - 2, step, value)
            return next_ip, depth_before - 1, value, branch_taken

        if instruction.opcode == WasmOpcode.I32_SUB:
            rhs = self._stack_read(depth_before - 1, step)
            lhs = self._stack_read(depth_before - 2, step)
            value = lhs - rhs
            self._stack_write(depth_before - 2, step, value)
            return next_ip, depth_before - 1, value, branch_taken

        if instruction.opcode == WasmOpcode.I32_MUL:
            rhs = self._stack_read(depth_before - 1, step)
            lhs = self._stack_read(depth_before - 2, step)
            value = lhs * rhs
            self._stack_write(depth_before - 2, step, value)
            return next_ip, depth_before - 1, value, branch_taken

        if instruction.opcode == WasmOpcode.I32_EQZ:
            top = self._stack_read(depth_before - 1, step)
            value = 1 if top == 0 else 0
            self._stack_write(depth_before - 1, step, value)
            return next_ip, depth_before, value, branch_taken

        if instruction.opcode == WasmOpcode.BR:
            target = instruction.branch_target or 0
            return target, depth_before, target, True

        if instruction.opcode == WasmOpcode.BR_IF:
            cond = self._stack_read(depth_before - 1, step)
            target = instruction.branch_target or 0
            if cond != 0:
                return target, depth_before - 1, target, True
            return next_ip, depth_before - 1, 0, False

        raise ValueError(f"Unsupported opcode: {instruction.opcode}")

    def run(self, max_steps: int = 200_000) -> ExecutionResult:
        step = 0
        while step < max_steps:
            ip = self._current_ip(step)
            if not 0 <= ip < len(self.function.instructions):
                break

            instruction = self._read_instruction(ip)
            depth_before = self._depth_before(step)
            next_ip, depth_after, value, branch_taken = self._transition(instruction, ip, step, depth_before)

            self.trace.append(
                TraceEntry(
                    step=step,
                    ip=ip,
                    instruction=str(instruction.as_wasm_instruction()),
                    value=mask_u32(value),
                    stack_delta=depth_after - depth_before,
                    stack_size=depth_after,
                    branch_taken=branch_taken,
                )
            )
            self.depth_counter.append(depth_after - depth_before)
            self.ip_head.write(step, next_ip)
            step += 1

        final_depth = self._depth_before(step)
        self.results = self._collect_results(step, final_depth)
        return ExecutionResult(results=self.results[:], trace=self.trace[:], locals_=self.locals_snapshot[:])


class TransformerVerificationBenchmark:
    """Benchmarks the tiny transformer-style executor."""

    def __init__(self, function: WasmFunction, timeline_cls: type[Timeline]) -> None:
        self.function = function
        self.timeline_cls = timeline_cls

    def run(self, name: str) -> TransformerRunStats:
        start = time.perf_counter()
        result = TinyExecutionTransformer(self.function, self.timeline_cls).run()
        elapsed = time.perf_counter() - start
        steps = len(result.trace)
        return TransformerRunStats(
            name=name,
            elapsed_s=elapsed,
            steps=steps,
            tokens_per_s=(steps / elapsed) if elapsed > 0 else float("inf"),
            results=result.results,
        )


def compare_transformer_to_reference(function: WasmFunction) -> tuple[ExecutionResult, ExecutionResult, ExecutionResult]:
    # Keep the reference executor import local to make the dependency explicit here.
    from llm_computer.wasm import ReferenceWasmExecutor

    reference = ReferenceWasmExecutor(function).run()
    naive = TinyExecutionTransformer(function, NaiveTimeline).run()
    hull = TinyExecutionTransformer(function, HullTimeline).run()
    return reference, naive, hull
