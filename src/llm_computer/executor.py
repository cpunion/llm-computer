"""Append-only execution driven by time-indexed retrieval over WASM traces."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Protocol

from llm_computer.hull import NaiveCache, OnlineHullCache, StaticHullCache
from llm_computer.wasm import (
    ExecutionResult,
    ReferenceWasmExecutor,
    TraceEntry,
    WasmFunction,
    WasmModule,
    WasmOpcode,
    mask_u32,
    to_signed_i32,
)


@dataclass(slots=True)
class RunStats:
    name: str
    elapsed_s: float
    steps: int
    tokens_per_s: float
    results: list[int]


def encode_time_key(step: int) -> tuple[float, float]:
    """Maps a trace position onto the parabola used in the article's example."""
    step_f = float(step)
    return (2.0 * step_f, -(step_f ** 2))


def latest_query(step: int) -> tuple[float, float]:
    return (float(step), 1.0)


class Timeline(Protocol):
    def insert(self, step: int, value: int) -> None:
        ...

    def query(self, step: int) -> int:
        ...


class NaiveTimeline:
    """Standard attention-style scan over all previous keys."""

    def __init__(self) -> None:
        self._cache = NaiveCache()

    def insert(self, step: int, value: int) -> None:
        self._cache.insert(encode_time_key(step), float(mask_u32(value)))

    def query(self, step: int) -> int:
        return int(self._cache.query(latest_query(step)))


class HullTimeline:
    """Append-only timeline backed by the online hull cache."""

    def __init__(self) -> None:
        self._cache = OnlineHullCache()

    def insert(self, step: int, value: int) -> None:
        self._cache.insert(encode_time_key(step), float(mask_u32(value)))

    def query(self, step: int) -> int:
        return int(self._cache.query(latest_query(step)))


class PrefixSumCounter:
    """Append-only cumulative state recovered from per-step deltas."""

    def __init__(self) -> None:
        self._totals: list[int] = []

    def append(self, delta: int) -> None:
        total = delta if not self._totals else self._totals[-1] + delta
        self._totals.append(total)

    def query(self, step: int) -> int:
        if step <= 0 or not self._totals:
            return 0
        index = min(step - 1, len(self._totals) - 1)
        return self._totals[index]


class AppendOnlyWasmExecutor:
    """Executes a flattened WASM function using append-only timelines."""

    def __init__(self, function: WasmFunction, timeline_cls: type[Timeline]) -> None:
        self.function = function
        self.timeline_cls = timeline_cls
        self.ip_timeline: Timeline = timeline_cls()
        self.local_timelines: list[Timeline] = [timeline_cls() for _ in range(function.local_count)]
        self.stack_timelines: dict[int, Timeline] = {}
        self.memory_timelines: dict[int, Timeline] = {}
        self.trace: list[TraceEntry] = []
        self.depth_counter = PrefixSumCounter()
        self.locals_snapshot = [0] * function.local_count
        self.results: list[int] = []
        for address, byte in function.initial_memory.items():
            self._memory_timeline(address).insert(-1, byte)

    def _depth_before(self, step: int) -> int:
        return self.depth_counter.query(step)

    def _stack_timeline(self, slot: int) -> Timeline:
        if slot not in self.stack_timelines:
            self.stack_timelines[slot] = self.timeline_cls()
        return self.stack_timelines[slot]

    def _stack_read(self, slot: int, step: int) -> int:
        if slot < 0:
            return 0
        timeline = self.stack_timelines.get(slot)
        if timeline is None:
            return 0
        return timeline.query(step)

    def _stack_write(self, slot: int, step: int, value: int) -> None:
        if slot < 0:
            return
        self._stack_timeline(slot).insert(step, mask_u32(value))

    def _local_read(self, index: int, step: int) -> int:
        if not 0 <= index < len(self.local_timelines):
            return 0
        return self.local_timelines[index].query(step)

    def _local_write(self, index: int, step: int, value: int) -> None:
        if not 0 <= index < len(self.local_timelines):
            return
        masked = mask_u32(value)
        self.local_timelines[index].insert(step, masked)
        self.locals_snapshot[index] = masked

    def _memory_timeline(self, address: int) -> Timeline:
        if address not in self.memory_timelines:
            self.memory_timelines[address] = self.timeline_cls()
        return self.memory_timelines[address]

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
            timeline = self.memory_timelines.get(address + offset)
            byte_value = timeline.query(step) if timeline is not None else 0
            value |= (byte_value & 0xFF) << (offset * 8)
        return mask_u32(value)

    def _memory_write_i32(self, address: int, step: int, value: int) -> None:
        self._check_memory_bounds(address, 4)
        masked = mask_u32(value)
        for offset in range(4):
            self._memory_timeline(address + offset).insert(step, (masked >> (offset * 8)) & 0xFF)

    def _current_ip(self, step: int) -> int:
        if step == 0:
            return 0
        return self.ip_timeline.query(step)

    def _collect_results(self, step: int, depth: int) -> list[int]:
        if self.function.result_count == 0:
            return []
        base = depth - self.function.result_count
        return [mask_u32(self._stack_read(base + offset, step)) for offset in range(self.function.result_count)]

    def run(self, max_steps: int = 200_000) -> ExecutionResult:
        step = 0
        while step < max_steps:
            ip = self._current_ip(step)
            if not 0 <= ip < len(self.function.instructions):
                break

            instruction = self.function.instructions[ip]
            depth_before = self._depth_before(step)
            branch_taken = False
            value = 0
            depth_after = depth_before
            next_ip = ip + 1

            if instruction.opcode in {WasmOpcode.BLOCK, WasmOpcode.LOOP, WasmOpcode.END}:
                pass
            elif instruction.opcode == WasmOpcode.IF:
                cond = self._stack_read(depth_before - 1, step)
                depth_after -= 1
                if cond == 0:
                    next_ip = instruction.false_target or instruction.end_target or (ip + 1)
                    branch_taken = True
            elif instruction.opcode == WasmOpcode.ELSE:
                next_ip = instruction.end_target or (ip + 1)
                branch_taken = True
            elif instruction.opcode == WasmOpcode.I32_CONST:
                value = instruction.immediate or 0
                self._stack_write(depth_before, step, value)
                depth_after += 1
            elif instruction.opcode == WasmOpcode.LOCAL_GET:
                index = instruction.immediate or 0
                value = self._local_read(index, step)
                self._stack_write(depth_before, step, value)
                depth_after += 1
            elif instruction.opcode == WasmOpcode.LOCAL_SET:
                index = instruction.immediate or 0
                value = self._stack_read(depth_before - 1, step)
                self._local_write(index, step, value)
                depth_after -= 1
            elif instruction.opcode == WasmOpcode.LOCAL_TEE:
                index = instruction.immediate or 0
                value = self._stack_read(depth_before - 1, step)
                self._local_write(index, step, value)
            elif instruction.opcode == WasmOpcode.I32_LOAD:
                base = self._stack_read(depth_before - 1, step)
                address = base + (instruction.memory_offset or 0)
                value = self._memory_read_i32(address, step)
                self._stack_write(depth_before - 1, step, value)
            elif instruction.opcode == WasmOpcode.I32_STORE:
                value = self._stack_read(depth_before - 1, step)
                base = self._stack_read(depth_before - 2, step)
                address = base + (instruction.memory_offset or 0)
                self._memory_write_i32(address, step, value)
                depth_after -= 2
            elif instruction.opcode == WasmOpcode.I32_LT_S:
                rhs = self._stack_read(depth_before - 1, step)
                lhs = self._stack_read(depth_before - 2, step)
                value = 1 if to_signed_i32(lhs) < to_signed_i32(rhs) else 0
                self._stack_write(depth_before - 2, step, value)
                depth_after -= 1
            elif instruction.opcode == WasmOpcode.I32_GT_S:
                rhs = self._stack_read(depth_before - 1, step)
                lhs = self._stack_read(depth_before - 2, step)
                value = 1 if to_signed_i32(lhs) > to_signed_i32(rhs) else 0
                self._stack_write(depth_before - 2, step, value)
                depth_after -= 1
            elif instruction.opcode == WasmOpcode.I32_LE_S:
                rhs = self._stack_read(depth_before - 1, step)
                lhs = self._stack_read(depth_before - 2, step)
                value = 1 if to_signed_i32(lhs) <= to_signed_i32(rhs) else 0
                self._stack_write(depth_before - 2, step, value)
                depth_after -= 1
            elif instruction.opcode == WasmOpcode.I32_ADD:
                rhs = self._stack_read(depth_before - 1, step)
                lhs = self._stack_read(depth_before - 2, step)
                value = lhs + rhs
                self._stack_write(depth_before - 2, step, value)
                depth_after -= 1
            elif instruction.opcode == WasmOpcode.I32_SUB:
                rhs = self._stack_read(depth_before - 1, step)
                lhs = self._stack_read(depth_before - 2, step)
                value = lhs - rhs
                self._stack_write(depth_before - 2, step, value)
                depth_after -= 1
            elif instruction.opcode == WasmOpcode.I32_MUL:
                rhs = self._stack_read(depth_before - 1, step)
                lhs = self._stack_read(depth_before - 2, step)
                value = lhs * rhs
                self._stack_write(depth_before - 2, step, value)
                depth_after -= 1
            elif instruction.opcode == WasmOpcode.I32_EQZ:
                top = self._stack_read(depth_before - 1, step)
                value = 1 if top == 0 else 0
                self._stack_write(depth_before - 1, step, value)
            elif instruction.opcode == WasmOpcode.BR:
                next_ip = instruction.branch_target or 0
                branch_taken = True
                value = next_ip
            elif instruction.opcode == WasmOpcode.BR_IF:
                cond = self._stack_read(depth_before - 1, step)
                depth_after -= 1
                if cond != 0:
                    next_ip = instruction.branch_target or 0
                    branch_taken = True
                    value = next_ip
            elif instruction.opcode == WasmOpcode.RETURN:
                self.trace.append(
                    TraceEntry(
                        step=step,
                        ip=ip,
                        instruction=str(instruction),
                        value=0,
                        stack_delta=0,
                        stack_size=depth_before,
                        branch_taken=False,
                    )
                )
                self.results = self._collect_results(step, depth_before)
                return ExecutionResult(results=self.results[:], trace=self.trace[:], locals_=self.locals_snapshot[:])
            elif instruction.opcode == WasmOpcode.DROP:
                value = self._stack_read(depth_before - 1, step)
                depth_after -= 1
            else:
                raise ValueError(f"Unsupported opcode: {instruction.opcode}")

            self.trace.append(
                TraceEntry(
                    step=step,
                    ip=ip,
                    instruction=str(instruction),
                    value=mask_u32(value),
                    stack_delta=depth_after - depth_before,
                    stack_size=depth_after,
                    branch_taken=branch_taken,
                )
            )
            self.depth_counter.append(depth_after - depth_before)
            self.ip_timeline.insert(step, next_ip)
            step += 1

        final_depth = self._depth_before(step)
        return ExecutionResult(
            results=self._collect_results(step, final_depth),
            trace=self.trace[:],
            locals_=self.locals_snapshot[:],
        )


class FunctionBenchmark:
    """Benchmarks append-only execution with either retrieval backend."""

    def __init__(self, function: WasmFunction, timeline_cls: type[Timeline]) -> None:
        self.function = function
        self.timeline_cls = timeline_cls

    def run(self, name: str) -> RunStats:
        start = time.perf_counter()
        result = AppendOnlyWasmExecutor(self.function, self.timeline_cls).run()
        elapsed = time.perf_counter() - start
        steps = len(result.trace)
        return RunStats(
            name=name,
            elapsed_s=elapsed,
            steps=steps,
            tokens_per_s=(steps / elapsed) if elapsed > 0 else float("inf"),
            results=result.results,
        )


def static_lookup_benchmark(lengths: list[int], seed: int = 42) -> list[tuple[int, float, float, float]]:
    rows: list[tuple[int, float, float, float]] = []
    for length in lengths:
        values = [float((seed + step) & 0xFF) for step in range(length)]
        queries = [latest_query(step) for step in range(length, length + 300)]

        static_cache = StaticHullCache()
        naive_cache = NaiveCache()
        for step, value in enumerate(values):
            key = encode_time_key(step)
            static_cache.insert(key, value)
            naive_cache.insert(key, value)

        start = time.perf_counter()
        for query in queries:
            static_cache.query(query)
        static_us = (time.perf_counter() - start) * 1e6 / len(queries)

        start = time.perf_counter()
        for query in queries:
            naive_cache.query(query)
        naive_us = (time.perf_counter() - start) * 1e6 / len(queries)

        rows.append((length, static_us, naive_us, naive_us / static_us if static_us > 0 else float("inf")))
    return rows


def online_lookup_benchmark(lengths: list[int], seed: int = 42) -> list[tuple[int, float, float, float]]:
    rows: list[tuple[int, float, float, float]] = []
    for length in lengths:
        online_cache = HullTimeline()
        naive_cache = NaiveTimeline()

        start = time.perf_counter()
        for step in range(length):
            online_cache.query(step)
            online_cache.insert(step, seed + step)
        online_ms = (time.perf_counter() - start) * 1e3

        start = time.perf_counter()
        for step in range(length):
            naive_cache.query(step)
            naive_cache.insert(step, seed + step)
        naive_ms = (time.perf_counter() - start) * 1e3

        rows.append((length, online_ms, naive_ms, naive_ms / online_ms if online_ms > 0 else float("inf")))
    return rows


def compare_against_reference(module: WasmModule, export_name: str, timeline_cls: type[Timeline]) -> tuple[ExecutionResult, ExecutionResult]:
    function = module.exported_function(export_name)
    reference = ReferenceWasmExecutor(function).run()
    append_only = AppendOnlyWasmExecutor(function, timeline_cls).run()
    return reference, append_only
