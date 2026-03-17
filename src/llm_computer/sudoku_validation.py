"""Sudoku-specific validation for result checks and prefix-state equivalence."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import date
import json
from pathlib import Path
from time import perf_counter

from llm_computer.examples import ARTICLE_SUDOKU_EXPECTED_CHECKSUM, ARTICLE_SUDOKU_PUZZLE, article_sudoku_module
from llm_computer.executor import AppendOnlyWasmExecutor, HullTimeline, NaiveTimeline
from llm_computer.transformer import TinyExecutionTransformer
from llm_computer.wasm import ExecutionResult, ReferenceWasmExecutor, WasmFunction, mask_u32


DEFAULT_PREFIX_BUDGETS = (1_000, 10_000, 100_000)
DEFAULT_MAX_BUDGET_BY_MODE = {
    "append_only_naive": 10_000,
    "append_only_hull": 100_000,
    "transformer_hull": 100_000,
}
_FNV_OFFSET = 0xCBF29CE484222325
_FNV_PRIME = 0x100000001B3


@dataclass(slots=True)
class SudokuStateDigest:
    ip: int
    next_instruction: str | None
    depth: int
    results: list[int]
    locals_digest: str
    local_nonzero_count: int
    stack_digest: str
    stack_top: list[int]
    memory_digest: str
    nonzero_memory_bytes: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class SudokuPrefixValidationRow:
    budget: int
    mode: str
    matches_reference: bool
    steps: int
    elapsed_s: float
    finished: bool
    result: int | None
    snapshot: SudokuStateDigest
    notes: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["snapshot"] = self.snapshot.to_dict()
        return payload


@dataclass(slots=True)
class SudokuChecksumValidation:
    mode: str
    success: bool
    result: int | None
    expected: int
    steps: int
    elapsed_s: float
    snapshot: SudokuStateDigest
    notes: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["snapshot"] = self.snapshot.to_dict()
        return payload


def _format_seconds(value: float) -> str:
    return f"{value * 1e3:.2f} ms" if value < 1 else f"{value:.3f} s"


def _mix_u64(state: int, value: int) -> int:
    chunk = value & 0xFFFFFFFFFFFFFFFF
    for shift in range(8):
        state ^= (chunk >> (shift * 8)) & 0xFF
        state = (state * _FNV_PRIME) & 0xFFFFFFFFFFFFFFFF
    return state


def _digest_values(values: list[int]) -> str:
    state = _FNV_OFFSET
    state = _mix_u64(state, len(values))
    for value in values:
        state = _mix_u64(state, mask_u32(value))
    return f"0x{state:016x}"


def _digest_memory(items: list[tuple[int, int]]) -> str:
    state = _FNV_OFFSET
    state = _mix_u64(state, len(items))
    for address, byte_value in items:
        state = _mix_u64(state, address)
        state = _mix_u64(state, byte_value & 0xFF)
    return f"0x{state:016x}"


def _next_instruction(function: WasmFunction, ip: int) -> str | None:
    if not 0 <= ip < len(function.instructions):
        return None
    return str(function.instructions[ip])


def _build_snapshot(
    function: WasmFunction,
    ip: int,
    stack: list[int],
    locals_values: list[int],
    memory_items: list[tuple[int, int]],
    results: list[int],
) -> SudokuStateDigest:
    normalized_stack = [mask_u32(value) for value in stack]
    normalized_locals = [mask_u32(value) for value in locals_values]
    normalized_results = [mask_u32(value) for value in results]
    return SudokuStateDigest(
        ip=ip,
        next_instruction=_next_instruction(function, ip),
        depth=len(normalized_stack),
        results=normalized_results,
        locals_digest=_digest_values(normalized_locals),
        local_nonzero_count=sum(1 for value in normalized_locals if value != 0),
        stack_digest=_digest_values(normalized_stack),
        stack_top=normalized_stack[-8:],
        memory_digest=_digest_memory(memory_items),
        nonzero_memory_bytes=len(memory_items),
    )


def _capture_reference_snapshot(executor: ReferenceWasmExecutor, execution: ExecutionResult) -> SudokuStateDigest:
    memory_items = sorted((address, byte) for address, byte in executor.memory.items() if byte != 0)
    return _build_snapshot(
        executor.function,
        executor.ip,
        executor.stack[:],
        executor.locals[:],
        memory_items,
        execution.results,
    )


def _capture_append_only_snapshot(executor: AppendOnlyWasmExecutor, execution: ExecutionResult) -> SudokuStateDigest:
    step = len(execution.trace)
    depth = executor._depth_before(step)
    memory_items = sorted(
        (address, timeline.query(step))
        for address, timeline in executor.memory_timelines.items()
        if timeline.query(step) != 0
    )
    return _build_snapshot(
        executor.function,
        executor._current_ip(step),
        [executor._stack_read(slot, step) for slot in range(depth)],
        executor.locals_snapshot[:],
        memory_items,
        execution.results,
    )


def _capture_transformer_snapshot(executor: TinyExecutionTransformer, execution: ExecutionResult) -> SudokuStateDigest:
    step = len(execution.trace)
    depth = executor._depth_before(step)
    memory_items = sorted(
        (address, head.read(step))
        for address, head in executor.memory_heads.items()
        if head.read(step) != 0
    )
    return _build_snapshot(
        executor.function,
        executor._current_ip(step),
        [executor.stack_read(slot, step) for slot in range(depth)],
        executor.locals_snapshot[:],
        memory_items,
        execution.results,
    )


def _finished(function: WasmFunction, ip: int) -> bool:
    return not 0 <= ip < len(function.instructions)


def run_sudoku_reference_checksum_validation(max_steps: int = 50_000_000) -> SudokuChecksumValidation:
    function = article_sudoku_module().exported_function("sudoku_checksum")
    executor = ReferenceWasmExecutor(function)
    start = perf_counter()
    execution = executor.run(max_steps=max_steps)
    elapsed = perf_counter() - start
    value = execution.results[0] if execution.results else None
    notes = None
    if value != ARTICLE_SUDOKU_EXPECTED_CHECKSUM:
        notes = f"reference run did not finish before max_steps={max_steps}"
    return SudokuChecksumValidation(
        mode="reference",
        success=value == ARTICLE_SUDOKU_EXPECTED_CHECKSUM,
        result=value,
        expected=ARTICLE_SUDOKU_EXPECTED_CHECKSUM,
        steps=len(execution.trace),
        elapsed_s=elapsed,
        snapshot=_capture_reference_snapshot(executor, execution),
        notes=notes,
    )


def run_sudoku_prefix_validation(
    budgets: tuple[int, ...] = DEFAULT_PREFIX_BUDGETS,
    max_budget_by_mode: dict[str, int] | None = None,
) -> list[SudokuPrefixValidationRow]:
    function = article_sudoku_module().exported_function("sudoku_checksum")
    budget_limits = dict(DEFAULT_MAX_BUDGET_BY_MODE)
    if max_budget_by_mode is not None:
        budget_limits.update(max_budget_by_mode)

    rows: list[SudokuPrefixValidationRow] = []
    for budget in budgets:
        reference_executor = ReferenceWasmExecutor(function)
        start = perf_counter()
        reference_execution = reference_executor.run(max_steps=budget)
        reference_elapsed = perf_counter() - start
        reference_snapshot = _capture_reference_snapshot(reference_executor, reference_execution)
        rows.append(
            SudokuPrefixValidationRow(
                budget=budget,
                mode="reference",
                matches_reference=True,
                steps=len(reference_execution.trace),
                elapsed_s=reference_elapsed,
                finished=_finished(function, reference_snapshot.ip),
                result=reference_execution.results[0] if reference_execution.results else None,
                snapshot=reference_snapshot,
            )
        )

        mode_runners = [
            (
                "append_only_naive",
                budget_limits["append_only_naive"],
                lambda: (
                    AppendOnlyWasmExecutor(function, NaiveTimeline),
                    _capture_append_only_snapshot,
                ),
            ),
            (
                "append_only_hull",
                budget_limits["append_only_hull"],
                lambda: (
                    AppendOnlyWasmExecutor(function, HullTimeline),
                    _capture_append_only_snapshot,
                ),
            ),
            (
                "transformer_hull",
                budget_limits["transformer_hull"],
                lambda: (
                    TinyExecutionTransformer(function, HullTimeline),
                    _capture_transformer_snapshot,
                ),
            ),
        ]

        for mode, max_budget, factory in mode_runners:
            if budget > max_budget:
                continue
            executor, snapshot_builder = factory()
            start = perf_counter()
            execution = executor.run(max_steps=budget)
            elapsed = perf_counter() - start
            snapshot = snapshot_builder(executor, execution)
            matches_reference = snapshot == reference_snapshot
            rows.append(
                SudokuPrefixValidationRow(
                    budget=budget,
                    mode=mode,
                    matches_reference=matches_reference,
                    steps=len(execution.trace),
                    elapsed_s=elapsed,
                    finished=_finished(function, snapshot.ip),
                    result=execution.results[0] if execution.results else None,
                    snapshot=snapshot,
                    notes=None if matches_reference else "snapshot diverged from reference",
                )
            )
    return rows


def build_json_report(
    checksum_result: SudokuChecksumValidation,
    prefix_rows: list[SudokuPrefixValidationRow],
) -> dict[str, object]:
    return {
        "date": date.today().isoformat(),
        "sudoku_puzzle": ARTICLE_SUDOKU_PUZZLE,
        "sudoku_expected_checksum": ARTICLE_SUDOKU_EXPECTED_CHECKSUM,
        "prefix_budgets": sorted({row.budget for row in prefix_rows}),
        "checksum_result": checksum_result.to_dict(),
        "prefix_results": [row.to_dict() for row in prefix_rows],
    }


def render_markdown_report(
    checksum_result: SudokuChecksumValidation,
    prefix_rows: list[SudokuPrefixValidationRow],
) -> str:
    checksum_interpretation = (
        "- The full Sudoku checksum is validated under the reference WASM executor."
        if checksum_result.success
        else "- The reference checksum row records the current best partial run and explicitly notes that the full checksum did not finish within the configured step budget."
    )
    lines = [
        "# Sudoku Result Validation",
        "",
        f"Date: {date.today().isoformat()}",
        "",
        "## Source Example",
        "",
        "- Source: the article's published Sudoku puzzle",
        f"- Puzzle: `{ARTICLE_SUDOKU_PUZZLE}`",
        f"- Expected checksum: `{ARTICLE_SUDOKU_EXPECTED_CHECKSUM}`",
        "",
        "## Full Checksum Validation",
        "",
        "| Mode | Success | Result | Expected | Steps | Elapsed | IP | Depth | Memory Bytes | Notes |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        "| "
        + " | ".join(
            [
                checksum_result.mode,
                "yes" if checksum_result.success else "no",
                str(checksum_result.result) if checksum_result.result is not None else "-",
                str(checksum_result.expected),
                str(checksum_result.steps),
                _format_seconds(checksum_result.elapsed_s),
                str(checksum_result.snapshot.ip),
                str(checksum_result.snapshot.depth),
                str(checksum_result.snapshot.nonzero_memory_bytes),
                checksum_result.notes or "-",
            ]
        )
        + " |",
        "",
        "## Prefix-State Validation",
        "",
        "| Budget | Mode | Matches Reference | Finished | Result | Steps | Elapsed | IP | Depth | Stack Digest | Memory Digest | Notes |",
        "| ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for row in prefix_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.budget),
                    row.mode,
                    "yes" if row.matches_reference else "no",
                    "yes" if row.finished else "no",
                    str(row.result) if row.result is not None else "-",
                    str(row.steps),
                    _format_seconds(row.elapsed_s),
                    str(row.snapshot.ip),
                    str(row.snapshot.depth),
                    row.snapshot.stack_digest,
                    row.snapshot.memory_digest,
                    row.notes or "-",
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            checksum_interpretation,
            "- Prefix-state validation compares exact execution snapshots against the reference path at fixed step budgets.",
            "- By default, `append_only_naive` is capped at `10,000` steps because it becomes disproportionately expensive on this trace, while `append_only_hull` and `transformer_hull` are validated through `100,000` steps.",
            "",
            "## Raw Results",
            "",
            "```json",
            json.dumps(build_json_report(checksum_result, prefix_rows), indent=2, sort_keys=True),
            "```",
        ]
    )
    return "\n".join(lines)


def write_report(path: str | Path, content: str) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate Sudoku results and prefix-state equivalence.")
    parser.add_argument(
        "--prefix-budgets",
        type=int,
        nargs="+",
        default=list(DEFAULT_PREFIX_BUDGETS),
        help="Prefix budgets for reference and local-mode equivalence checks.",
    )
    parser.add_argument(
        "--naive-max-budget",
        type=int,
        default=DEFAULT_MAX_BUDGET_BY_MODE["append_only_naive"],
        help="Maximum prefix budget for append_only_naive validation.",
    )
    parser.add_argument(
        "--hull-max-budget",
        type=int,
        default=DEFAULT_MAX_BUDGET_BY_MODE["append_only_hull"],
        help="Maximum prefix budget for append_only_hull validation.",
    )
    parser.add_argument(
        "--transformer-max-budget",
        type=int,
        default=DEFAULT_MAX_BUDGET_BY_MODE["transformer_hull"],
        help="Maximum prefix budget for transformer_hull validation.",
    )
    parser.add_argument(
        "--full-reference-max-steps",
        type=int,
        default=50_000_000,
        help="Maximum number of reference steps for the full Sudoku checksum run.",
    )
    parser.add_argument("--markdown-output", help="Optional path to write the markdown report.")
    parser.add_argument("--json-output", help="Optional path to write the JSON report.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    checksum_result = run_sudoku_reference_checksum_validation(max_steps=args.full_reference_max_steps)
    prefix_rows = run_sudoku_prefix_validation(
        budgets=tuple(args.prefix_budgets),
        max_budget_by_mode={
            "append_only_naive": args.naive_max_budget,
            "append_only_hull": args.hull_max_budget,
            "transformer_hull": args.transformer_max_budget,
        },
    )
    report = render_markdown_report(checksum_result, prefix_rows)
    print(report)
    if args.markdown_output:
        write_report(args.markdown_output, report + "\n")
    if args.json_output:
        write_report(
            args.json_output,
            json.dumps(build_json_report(checksum_result, prefix_rows), indent=2, sort_keys=True) + "\n",
        )


if __name__ == "__main__":
    main()
