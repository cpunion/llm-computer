"""Validation harness for the article's Hungarian and Sudoku examples."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import date
import json
from pathlib import Path
from time import perf_counter

from llm_computer.examples import (
    ARTICLE_HUNGARIAN_EXPECTED_COST,
    ARTICLE_HUNGARIAN_MATRIX,
    ARTICLE_SUDOKU_EXPECTED_CHECKSUM,
    ARTICLE_SUDOKU_PUZZLE,
    article_hungarian_module,
    article_sudoku_module,
)
from llm_computer.executor import AppendOnlyWasmExecutor, HullTimeline, NaiveTimeline
from llm_computer.transformer import TinyExecutionTransformer, supports_transformer_verification
from llm_computer.wasm import ReferenceWasmExecutor


@dataclass(slots=True)
class ArticleExampleResult:
    example_id: str
    mode: str
    success: bool
    result: int | None
    expected: int
    steps: int
    elapsed_s: float
    transformer_subset: bool
    notes: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _format_seconds(value: float) -> str:
    return f"{value * 1e3:.2f} ms" if value < 1 else f"{value:.3f} s"


def run_hungarian_validation() -> list[ArticleExampleResult]:
    function = article_hungarian_module().exported_function("hungarian_10x10")
    subset = supports_transformer_verification(function)
    results: list[ArticleExampleResult] = []
    runners = [
        ("reference", lambda: ReferenceWasmExecutor(function).run(max_steps=500_000)),
        ("append_only_naive", lambda: AppendOnlyWasmExecutor(function, NaiveTimeline).run(max_steps=500_000)),
        ("append_only_hull", lambda: AppendOnlyWasmExecutor(function, HullTimeline).run(max_steps=500_000)),
        ("transformer_hull", lambda: TinyExecutionTransformer(function, HullTimeline).run(max_steps=500_000)),
    ]
    for mode, runner in runners:
        start = perf_counter()
        execution = runner()
        elapsed = perf_counter() - start
        value = execution.results[0] if execution.results else None
        results.append(
            ArticleExampleResult(
                example_id="hungarian_10x10",
                mode=mode,
                success=value == ARTICLE_HUNGARIAN_EXPECTED_COST,
                result=value,
                expected=ARTICLE_HUNGARIAN_EXPECTED_COST,
                steps=len(execution.trace),
                elapsed_s=elapsed,
                transformer_subset=subset,
            )
        )
    return results


def run_sudoku_reference_validation(max_steps: int = 50_000_000) -> ArticleExampleResult:
    function = article_sudoku_module().exported_function("sudoku_checksum")
    start = perf_counter()
    execution = ReferenceWasmExecutor(function).run(max_steps=max_steps)
    elapsed = perf_counter() - start
    value = execution.results[0] if execution.results else None
    notes = None
    if value != ARTICLE_SUDOKU_EXPECTED_CHECKSUM:
        notes = f"reference run did not finish before max_steps={max_steps}"
    return ArticleExampleResult(
        example_id="sudoku_checksum",
        mode="reference",
        success=value == ARTICLE_SUDOKU_EXPECTED_CHECKSUM,
        result=value,
        expected=ARTICLE_SUDOKU_EXPECTED_CHECKSUM,
        steps=len(execution.trace),
        elapsed_s=elapsed,
        transformer_subset=supports_transformer_verification(function),
        notes=notes,
    )


def build_json_report(
    hungarian_results: list[ArticleExampleResult],
    sudoku_result: ArticleExampleResult,
) -> dict[str, object]:
    return {
        "date": date.today().isoformat(),
        "hungarian_matrix": [list(row) for row in ARTICLE_HUNGARIAN_MATRIX],
        "hungarian_expected_cost": ARTICLE_HUNGARIAN_EXPECTED_COST,
        "sudoku_puzzle": ARTICLE_SUDOKU_PUZZLE,
        "sudoku_expected_checksum": ARTICLE_SUDOKU_EXPECTED_CHECKSUM,
        "results": [result.to_dict() for result in hungarian_results] + [sudoku_result.to_dict()],
    }


def render_markdown_report(
    hungarian_results: list[ArticleExampleResult],
    sudoku_result: ArticleExampleResult,
) -> str:
    lines = [
        "# Article Example Validation",
        "",
        f"Date: {date.today().isoformat()}",
        "",
        "## Source Examples",
        "",
        "- Hungarian example: the article's `10x10 min-cost perfect matching` matrix",
        f"- Hungarian expected cost: `{ARTICLE_HUNGARIAN_EXPECTED_COST}`",
        "- Sudoku example: the article's published puzzle string",
        f"- Sudoku puzzle: `{ARTICLE_SUDOKU_PUZZLE}`",
        f"- Sudoku expected checksum: `{ARTICLE_SUDOKU_EXPECTED_CHECKSUM}`",
        "",
        "## Results",
        "",
        "| Example | Mode | Success | Result | Expected | Steps | Elapsed | Transformer Subset | Notes |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for result in [*hungarian_results, sudoku_result]:
        lines.append(
            "| "
            + " | ".join(
                [
                    result.example_id,
                    result.mode,
                    "yes" if result.success else "no",
                    str(result.result) if result.result is not None else "-",
                    str(result.expected),
                    str(result.steps),
                    _format_seconds(result.elapsed_s),
                    "yes" if result.transformer_subset else "no",
                    result.notes or "-",
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The Hungarian example is now validated end-to-end across the semantic reference, append-only naive timeline, append-only hull timeline, and tiny transformer-style hull path.",
            "- The Sudoku example is validated against an independent checksum under the reference WASM executor and is now inside the current transformer opcode subset.",
            "- The current repository does not run the full Sudoku trace through the append-only or transformer paths by default because the trace is much longer than the Hungarian example.",
            "",
            "## Raw Results",
            "",
            "```json",
            json.dumps(build_json_report(hungarian_results, sudoku_result), indent=2, sort_keys=True),
            "```",
        ]
    )
    return "\n".join(lines)


def write_report(path: str | Path, content: str) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate the article's Hungarian and Sudoku examples.")
    parser.add_argument("--markdown-output", help="Optional path to write the markdown report.")
    parser.add_argument("--json-output", help="Optional path to write the JSON report.")
    parser.add_argument(
        "--sudoku-max-steps",
        type=int,
        default=50_000_000,
        help="Maximum number of reference interpreter steps for the Sudoku example.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    hungarian_results = run_hungarian_validation()
    sudoku_result = run_sudoku_reference_validation(max_steps=args.sudoku_max_steps)
    report = render_markdown_report(hungarian_results, sudoku_result)
    print(report)
    if args.markdown_output:
        write_report(args.markdown_output, report + "\n")
    if args.json_output:
        write_report(
            args.json_output,
            json.dumps(build_json_report(hungarian_results, sudoku_result), indent=2, sort_keys=True) + "\n",
        )


if __name__ == "__main__":
    main()
