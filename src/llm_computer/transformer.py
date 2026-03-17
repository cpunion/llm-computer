"""Tiny transformer-style execution verification for a restricted WASM subset."""

from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Protocol

from llm_computer.executor import HullTimeline, NaiveTimeline, PrefixSumCounter, Timeline
from llm_computer.hull import NaiveCache
from llm_computer.wasm import (
    ExecutionResult,
    TraceEntry,
    WasmFunction,
    WasmInstruction,
    WasmOpcode,
    mask_u32,
    to_signed_i32,
)


SUPPORTED_OPCODES = {
    WasmOpcode.BLOCK,
    WasmOpcode.LOOP,
    WasmOpcode.IF,
    WasmOpcode.ELSE,
    WasmOpcode.END,
    WasmOpcode.DROP,
    WasmOpcode.I32_CONST,
    WasmOpcode.LOCAL_GET,
    WasmOpcode.LOCAL_SET,
    WasmOpcode.LOCAL_TEE,
    WasmOpcode.I32_LOAD,
    WasmOpcode.I32_STORE,
    WasmOpcode.I32_EQ,
    WasmOpcode.I32_NE,
    WasmOpcode.I32_LT_S,
    WasmOpcode.I32_GT_S,
    WasmOpcode.I32_LE_S,
    WasmOpcode.I32_GE_S,
    WasmOpcode.I32_GE_U,
    WasmOpcode.I32_ADD,
    WasmOpcode.I32_SUB,
    WasmOpcode.I32_MUL,
    WasmOpcode.I32_AND,
    WasmOpcode.I32_XOR,
    WasmOpcode.I32_SHL,
    WasmOpcode.I32_SHR_U,
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


@dataclass(slots=True)
class ExecutionWrite:
    target: str
    index: int
    value: int


@dataclass(slots=True)
class ExecutionFeatures:
    instruction: DecodedInstruction
    ip: int
    step: int
    depth_before: int
    next_ip: int
    top: int
    second: int
    local_index: int | None = None
    local_value: int = 0
    effective_address: int | None = None
    memory_value: int = 0


@dataclass(slots=True)
class TransitionSignal:
    next_ip: int
    depth_after: int
    value: int
    branch_taken: bool
    writeback_mode: str = "none"


@dataclass(slots=True)
class BlockTransition:
    next_ip: int
    depth_after: int
    value: int
    branch_taken: bool
    writes: list[ExecutionWrite] = field(default_factory=list)


class StateReader(Protocol):
    def stack_read(self, slot: int, step: int) -> int:
        ...

    def local_read(self, index: int, step: int) -> int:
        ...

    def memory_read_i32(self, address: int, step: int) -> int:
        ...


class ExecutionFeatureExtractor:
    """Collects the local execution context that the transition layer consumes."""

    def extract(
        self,
        instruction: DecodedInstruction,
        ip: int,
        step: int,
        depth_before: int,
        state: StateReader,
    ) -> ExecutionFeatures:
        top = state.stack_read(depth_before - 1, step)
        second = state.stack_read(depth_before - 2, step)
        local_index = instruction.immediate if instruction.opcode in {WasmOpcode.LOCAL_GET, WasmOpcode.LOCAL_SET, WasmOpcode.LOCAL_TEE} else None
        local_value = state.local_read(local_index, step) if local_index is not None else 0
        effective_address = None
        memory_value = 0
        if instruction.opcode == WasmOpcode.I32_LOAD:
            effective_address = top + (instruction.memory_offset or 0)
            memory_value = state.memory_read_i32(effective_address, step)
        elif instruction.opcode == WasmOpcode.I32_STORE:
            effective_address = second + (instruction.memory_offset or 0)

        return ExecutionFeatures(
            instruction=instruction,
            ip=ip,
            step=step,
            depth_before=depth_before,
            next_ip=ip + 1,
            top=top,
            second=second,
            local_index=local_index,
            local_value=local_value,
            effective_address=effective_address,
            memory_value=memory_value,
        )


class ExecutionTransitionLayer:
    """Maps execution features onto a state-transition signal."""

    def __init__(self) -> None:
        self._comparison_ops = {
            WasmOpcode.I32_EQ: lambda lhs, rhs: 1 if mask_u32(lhs) == mask_u32(rhs) else 0,
            WasmOpcode.I32_NE: lambda lhs, rhs: 1 if mask_u32(lhs) != mask_u32(rhs) else 0,
            WasmOpcode.I32_LT_S: lambda lhs, rhs: 1 if to_signed_i32(lhs) < to_signed_i32(rhs) else 0,
            WasmOpcode.I32_GT_S: lambda lhs, rhs: 1 if to_signed_i32(lhs) > to_signed_i32(rhs) else 0,
            WasmOpcode.I32_LE_S: lambda lhs, rhs: 1 if to_signed_i32(lhs) <= to_signed_i32(rhs) else 0,
            WasmOpcode.I32_GE_S: lambda lhs, rhs: 1 if to_signed_i32(lhs) >= to_signed_i32(rhs) else 0,
            WasmOpcode.I32_GE_U: lambda lhs, rhs: 1 if mask_u32(lhs) >= mask_u32(rhs) else 0,
        }
        self._binary_ops = {
            WasmOpcode.I32_ADD: lambda lhs, rhs: lhs + rhs,
            WasmOpcode.I32_SUB: lambda lhs, rhs: lhs - rhs,
            WasmOpcode.I32_MUL: lambda lhs, rhs: lhs * rhs,
            WasmOpcode.I32_AND: lambda lhs, rhs: mask_u32(lhs) & mask_u32(rhs),
            WasmOpcode.I32_XOR: lambda lhs, rhs: mask_u32(lhs) ^ mask_u32(rhs),
            WasmOpcode.I32_SHL: lambda lhs, rhs: mask_u32(lhs) << (mask_u32(rhs) & 31),
            WasmOpcode.I32_SHR_U: lambda lhs, rhs: mask_u32(lhs) >> (mask_u32(rhs) & 31),
        }

    def transition(self, features: ExecutionFeatures) -> TransitionSignal:
        opcode = features.instruction.opcode

        if opcode in {WasmOpcode.BLOCK, WasmOpcode.LOOP, WasmOpcode.END}:
            return TransitionSignal(
                next_ip=features.next_ip,
                depth_after=features.depth_before,
                value=0,
                branch_taken=False,
            )

        if opcode == WasmOpcode.IF:
            depth_after = features.depth_before - 1
            if features.top == 0:
                return TransitionSignal(
                    next_ip=features.instruction.false_target or features.instruction.end_target or features.next_ip,
                    depth_after=depth_after,
                    value=0,
                    branch_taken=True,
                )
            return TransitionSignal(next_ip=features.next_ip, depth_after=depth_after, value=0, branch_taken=False)

        if opcode == WasmOpcode.ELSE:
            return TransitionSignal(
                next_ip=features.instruction.end_target or features.next_ip,
                depth_after=features.depth_before,
                value=0,
                branch_taken=True,
            )

        if opcode == WasmOpcode.I32_CONST:
            return TransitionSignal(
                next_ip=features.next_ip,
                depth_after=features.depth_before + 1,
                value=features.instruction.immediate or 0,
                branch_taken=False,
                writeback_mode="push_value",
            )

        if opcode == WasmOpcode.LOCAL_GET:
            return TransitionSignal(
                next_ip=features.next_ip,
                depth_after=features.depth_before + 1,
                value=features.local_value,
                branch_taken=False,
                writeback_mode="push_value",
            )

        if opcode == WasmOpcode.LOCAL_SET:
            return TransitionSignal(
                next_ip=features.next_ip,
                depth_after=features.depth_before - 1,
                value=features.top,
                branch_taken=False,
                writeback_mode="write_local_from_top",
            )

        if opcode == WasmOpcode.LOCAL_TEE:
            return TransitionSignal(
                next_ip=features.next_ip,
                depth_after=features.depth_before,
                value=features.top,
                branch_taken=False,
                writeback_mode="write_local_from_top",
            )

        if opcode == WasmOpcode.I32_LOAD:
            return TransitionSignal(
                next_ip=features.next_ip,
                depth_after=features.depth_before,
                value=features.memory_value,
                branch_taken=False,
                writeback_mode="replace_top",
            )

        if opcode == WasmOpcode.I32_STORE:
            return TransitionSignal(
                next_ip=features.next_ip,
                depth_after=features.depth_before - 2,
                value=features.top,
                branch_taken=False,
                writeback_mode="store_i32",
            )

        if opcode in self._comparison_ops:
            return TransitionSignal(
                next_ip=features.next_ip,
                depth_after=features.depth_before - 1,
                value=self._comparison_ops[opcode](features.second, features.top),
                branch_taken=False,
                writeback_mode="replace_second",
            )

        if opcode in self._binary_ops:
            return TransitionSignal(
                next_ip=features.next_ip,
                depth_after=features.depth_before - 1,
                value=self._binary_ops[opcode](features.second, features.top),
                branch_taken=False,
                writeback_mode="replace_second",
            )

        if opcode == WasmOpcode.I32_EQZ:
            return TransitionSignal(
                next_ip=features.next_ip,
                depth_after=features.depth_before,
                value=1 if features.top == 0 else 0,
                branch_taken=False,
                writeback_mode="replace_top",
            )

        if opcode == WasmOpcode.BR:
            target = features.instruction.branch_target or 0
            return TransitionSignal(next_ip=target, depth_after=features.depth_before, value=target, branch_taken=True)

        if opcode == WasmOpcode.BR_IF:
            target = features.instruction.branch_target or 0
            if features.top != 0:
                return TransitionSignal(next_ip=target, depth_after=features.depth_before - 1, value=target, branch_taken=True)
            return TransitionSignal(next_ip=features.next_ip, depth_after=features.depth_before - 1, value=0, branch_taken=False)

        if opcode == WasmOpcode.DROP:
            return TransitionSignal(
                next_ip=features.next_ip,
                depth_after=features.depth_before - 1,
                value=features.top,
                branch_taken=False,
            )

        raise ValueError(f"Unsupported opcode: {opcode}")


class ExecutionWritebackLayer:
    """Converts transition signals into append-only state writes."""

    def build(self, features: ExecutionFeatures, signal: TransitionSignal) -> list[ExecutionWrite]:
        mode = signal.writeback_mode
        if mode == "none":
            return []
        if mode == "push_value":
            return [ExecutionWrite(target="stack", index=features.depth_before, value=signal.value)]
        if mode == "replace_top":
            return [ExecutionWrite(target="stack", index=features.depth_before - 1, value=signal.value)]
        if mode == "replace_second":
            return [ExecutionWrite(target="stack", index=features.depth_before - 2, value=signal.value)]
        if mode == "write_local_from_top":
            if features.local_index is None:
                raise ValueError("Local writeback requires a local index")
            return [ExecutionWrite(target="local", index=features.local_index, value=features.top)]
        if mode == "store_i32":
            if features.effective_address is None:
                raise ValueError("Store writeback requires an effective address")
            masked = mask_u32(features.top)
            return [
                ExecutionWrite(
                    target="memory",
                    index=features.effective_address + offset,
                    value=(masked >> (offset * 8)) & 0xFF,
                )
                for offset in range(4)
            ]
        raise ValueError(f"Unknown writeback mode: {mode}")


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
    return all(instruction.opcode in SUPPORTED_OPCODES for instruction in function.instructions)


class TinyExecutionBlock:
    """A small transition block that consumes retrieved state and emits writes."""

    def __init__(self) -> None:
        self.feature_extractor = ExecutionFeatureExtractor()
        self.transition_layer = ExecutionTransitionLayer()
        self.writeback_layer = ExecutionWritebackLayer()

    def extract_features(
        self,
        instruction: DecodedInstruction,
        ip: int,
        step: int,
        depth_before: int,
        state: StateReader,
    ) -> ExecutionFeatures:
        return self.feature_extractor.extract(instruction, ip, step, depth_before, state)

    def apply_transition(self, features: ExecutionFeatures) -> TransitionSignal:
        return self.transition_layer.transition(features)

    def plan_writeback(self, features: ExecutionFeatures, signal: TransitionSignal) -> list[ExecutionWrite]:
        return self.writeback_layer.build(features, signal)

    def apply(
        self,
        instruction: DecodedInstruction,
        ip: int,
        step: int,
        depth_before: int,
        state: StateReader,
    ) -> BlockTransition:
        features = self.extract_features(instruction, ip, step, depth_before, state)
        signal = self.apply_transition(features)
        return BlockTransition(
            next_ip=signal.next_ip,
            depth_after=signal.depth_after,
            value=signal.value,
            branch_taken=signal.branch_taken,
            writes=self.plan_writeback(features, signal),
        )


class TinyExecutionTransformer:
    """A tiny transformer-style executor composed of retrieval heads and a transition block."""

    def __init__(self, function: WasmFunction, timeline_cls: type[Timeline]) -> None:
        if not supports_transformer_verification(function):
            raise ValueError("Function is outside the transformer verification subset")

        self.function = function
        self.timeline_cls = timeline_cls
        self.block = TinyExecutionBlock()
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

    def _memory_head(self, address: int) -> DynamicStateHead:
        if address not in self.memory_heads:
            self.memory_heads[address] = DynamicStateHead(self.timeline_cls)
        return self.memory_heads[address]

    def stack_read(self, slot: int, step: int) -> int:
        if slot < 0:
            return 0
        head = self.stack_heads.get(slot)
        return head.read(step) if head is not None else 0

    def local_read(self, index: int, step: int) -> int:
        if not 0 <= index < len(self.local_heads):
            return 0
        return self.local_heads[index].read(step)

    def _check_memory_bounds(self, address: int, size: int) -> None:
        if address < 0:
            raise ValueError("Negative memory access")
        limit = self.function.initial_memory_pages * 65536
        if address + size > limit:
            raise ValueError("Out-of-bounds memory access")

    def memory_read_i32(self, address: int, step: int) -> int:
        self._check_memory_bounds(address, 4)
        value = 0
        for offset in range(4):
            head = self.memory_heads.get(address + offset)
            byte_value = head.read(step) if head is not None else 0
            value |= (byte_value & 0xFF) << (offset * 8)
        return mask_u32(value)

    def _stack_write(self, slot: int, step: int, value: int) -> None:
        if slot < 0:
            return
        self._stack_head(slot).write(step, value)

    def _local_write(self, index: int, step: int, value: int) -> None:
        if not 0 <= index < len(self.local_heads):
            return
        masked = mask_u32(value)
        self.local_heads[index].write(step, masked)
        self.locals_snapshot[index] = masked

    def _memory_write_byte(self, address: int, step: int, value: int) -> None:
        self._memory_head(address).write(step, value & 0xFF)

    def _current_ip(self, step: int) -> int:
        return 0 if step == 0 else self.ip_head.read(step)

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

    def _apply_writes(self, step: int, writes: list[ExecutionWrite]) -> None:
        for write in writes:
            if write.target == "stack":
                self._stack_write(write.index, step, write.value)
            elif write.target == "local":
                self._local_write(write.index, step, write.value)
            elif write.target == "memory":
                self._memory_write_byte(write.index, step, write.value)
            else:
                raise ValueError(f"Unknown write target: {write.target}")

    def _collect_results(self, step: int, depth: int) -> list[int]:
        if self.function.result_count == 0:
            return []
        base = depth - self.function.result_count
        return [mask_u32(self.stack_read(base + offset, step)) for offset in range(self.function.result_count)]

    def run(self, max_steps: int = 200_000) -> ExecutionResult:
        step = 0
        while step < max_steps:
            ip = self._current_ip(step)
            if not 0 <= ip < len(self.function.instructions):
                break

            instruction = self._read_instruction(ip)
            depth_before = self._depth_before(step)
            transition = self.block.apply(instruction, ip, step, depth_before, self)
            self._apply_writes(step, transition.writes)

            self.trace.append(
                TraceEntry(
                    step=step,
                    ip=ip,
                    instruction=str(instruction.as_wasm_instruction()),
                    value=mask_u32(transition.value),
                    stack_delta=transition.depth_after - depth_before,
                    stack_size=transition.depth_after,
                    branch_taken=transition.branch_taken,
                )
            )
            self.depth_counter.append(transition.depth_after - depth_before)
            self.ip_head.write(step, transition.next_ip)
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
    from llm_computer.wasm import ReferenceWasmExecutor

    reference = ReferenceWasmExecutor(function).run()
    naive = TinyExecutionTransformer(function, NaiveTimeline).run()
    hull = TinyExecutionTransformer(function, HullTimeline).run()
    return reference, naive, hull
