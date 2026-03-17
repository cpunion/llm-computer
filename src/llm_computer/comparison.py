"""Unified comparison harness for direct, open-source, and closed-source paths."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import date
import json
from pathlib import Path
from time import perf_counter

from llm_computer.gemini_integration import DEFAULT_GEMINI_MODEL, GeminiExecutionRuntime
from llm_computer.protocol import ExecutionMode, ExecutionRequest, ExecutionResponse, SourceKind
from llm_computer.qwen_transformers import (
    DEFAULT_QWEN_MODEL_ID,
    ExecutionPromptMode,
    GenerationSettings,
    QwenExecutionBlockOrchestrator,
    QwenExecutionOrchestrator,
    TransformersChatRuntime,
)
from llm_computer.service import ExecutionService, PinnedExecutionBackend


CANONICAL_WAT_MODULE = '(module (func (export "main") (result i32) i32.const 6 i32.const 7 i32.mul))'
CANONICAL_WAT_MODULE_JSON = CANONICAL_WAT_MODULE.replace('"', '\\"')
OPEN_SOURCE_PROMPT = "Compute 6 * 7 exactly."
OPEN_SOURCE_SYSTEM = (
    "Protocol requirement: do not answer directly. "
    'The runtime has already emitted the opening { of the JSON object. Continue with the remaining keys only, '
    'without restarting the object. Set source_kind to "wat", mode to "auto", export_name to "main", '
    f'and source to exactly this WAT module string: {CANONICAL_WAT_MODULE_JSON}. '
    "After runtime feedback, reply with only the final integer."
)
GEMINI_PROMPT = (
    "Use the execution tool once. Set source_kind to \"wat\", mode to \"auto\", export_name to \"main\", "
    f"and source to exactly this WAT module: {CANONICAL_WAT_MODULE}. "
    "After the tool result is available, reply with only the final integer."
)
GEMINI_SYSTEM = (
    "You are a precise engineering assistant. "
    "Do not answer arithmetic directly. Always use the execution tool for the exact result and then return only "
    "the final integer."
)


@dataclass(slots=True)
class ComparisonResult:
    method_id: str
    category: str
    success: bool
    final_text: str
    final_value: int | None
    used_execution: bool
    end_to_end_s: float
    backend_mode: str | None = None
    backend_elapsed_s: float | None = None
    steps: int | None = None
    intercepted_requests: int | None = None
    structured_captures: int | None = None
    runtime_answer_fallbacks: int | None = None
    native_execution_rounds: int | None = None
    tool_calls: int | None = None
    notes: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _parse_exact_int(text: str) -> int | None:
    stripped = text.strip()
    if not stripped:
        return None
    if stripped.startswith(("+", "-")):
        sign, digits = stripped[0], stripped[1:]
        if digits.isdigit():
            return int(sign + digits)
        return None
    return int(stripped) if stripped.isdigit() else None


def _format_seconds(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value * 1e3:.2f} ms" if value < 1 else f"{value:.3f} s"


def _response_to_value(response: ExecutionResponse) -> int | None:
    if response.ok and len(response.results) == 1:
        return int(response.results[0])
    return None


def _extract_exec_response(result: object) -> ExecutionResponse | None:
    turns = getattr(result, "turns", [])
    for turn in turns:
        if turn.exec_response:
            return QwenExecutionOrchestrator._parse_exec_response(turn.exec_response)
    return None


def _build_open_source_settings() -> GenerationSettings:
    return GenerationSettings(
        max_new_tokens=128,
        intercept_request_boundary=True,
        request_prefix=QwenExecutionOrchestrator.default_request_prefix(ExecutionPromptMode.STRUCTURED),
    )


def _build_open_source_messages() -> list[dict[str, str]]:
    return QwenExecutionOrchestrator.prepare_messages(
        OPEN_SOURCE_PROMPT,
        system_prompt=OPEN_SOURCE_SYSTEM,
        execution_prompt_mode=ExecutionPromptMode.STRUCTURED,
    )


def run_direct_response(method_id: str, mode: ExecutionMode, service: ExecutionService) -> ComparisonResult:
    request = ExecutionRequest(
        source_kind=SourceKind.WAT,
        source=CANONICAL_WAT_MODULE,
        mode=mode,
        trace_limit=4,
    )
    start = perf_counter()
    response = service.execute(request)
    elapsed = perf_counter() - start
    value = _response_to_value(response)
    return ComparisonResult(
        method_id=method_id,
        category="direct",
        success=response.ok and value == 42,
        final_text=str(value) if value is not None else (response.error or ""),
        final_value=value,
        used_execution=True,
        end_to_end_s=elapsed,
        backend_mode=response.mode_used.value,
        backend_elapsed_s=response.elapsed_s,
        steps=response.steps,
        notes="direct service execution",
    )


def run_open_source_wrapper(runtime: TransformersChatRuntime, service: ExecutionService) -> ComparisonResult:
    orchestrator = QwenExecutionOrchestrator(runtime, service=service)
    start = perf_counter()
    result = orchestrator.run(
        _build_open_source_messages(),
        settings=_build_open_source_settings(),
        max_round_trips=3,
    )
    elapsed = perf_counter() - start
    exec_response = _extract_exec_response(result)
    return ComparisonResult(
        method_id="open_source_wrapper",
        category="open_source",
        success=result.final_text.strip() == "42",
        final_text=result.final_text,
        final_value=_parse_exact_int(result.final_text),
        used_execution=result.used_execution,
        end_to_end_s=elapsed,
        backend_mode=exec_response.mode_used.value if exec_response is not None else None,
        backend_elapsed_s=exec_response.elapsed_s if exec_response is not None else None,
        steps=exec_response.steps if exec_response is not None else None,
        intercepted_requests=result.intercepted_requests,
        structured_captures=result.structured_captures,
        runtime_answer_fallbacks=result.runtime_answer_fallbacks,
        native_execution_rounds=result.native_execution_rounds,
        notes="wrapper + structured + prefilled prefix",
    )


def run_open_source_execution_block(runtime: TransformersChatRuntime, service: ExecutionService) -> ComparisonResult:
    orchestrator = QwenExecutionBlockOrchestrator(
        runtime,
        backend=PinnedExecutionBackend(ExecutionMode.TRANSFORMER_HULL, service=service),
    )
    start = perf_counter()
    result = orchestrator.run(
        _build_open_source_messages(),
        settings=_build_open_source_settings(),
        max_round_trips=3,
    )
    elapsed = perf_counter() - start
    exec_response = _extract_exec_response(result)
    return ComparisonResult(
        method_id="open_source_execution_block",
        category="open_source",
        success=result.final_text.strip() == "42",
        final_text=result.final_text,
        final_value=_parse_exact_int(result.final_text),
        used_execution=result.used_execution,
        end_to_end_s=elapsed,
        backend_mode=exec_response.mode_used.value if exec_response is not None else None,
        backend_elapsed_s=exec_response.elapsed_s if exec_response is not None else None,
        steps=exec_response.steps if exec_response is not None else None,
        intercepted_requests=result.intercepted_requests,
        structured_captures=result.structured_captures,
        runtime_answer_fallbacks=result.runtime_answer_fallbacks,
        native_execution_rounds=result.native_execution_rounds,
        notes="native execution-block + pinned transformer_hull backend",
    )


def run_closed_source_sidecar(
    model: str,
    *,
    runtime: GeminiExecutionRuntime | None = None,
) -> ComparisonResult:
    active_runtime = runtime or GeminiExecutionRuntime.from_env(model=model)
    start = perf_counter()
    result = active_runtime.run(
        GEMINI_PROMPT,
        system_prompt=GEMINI_SYSTEM,
        force_tool_use=True,
    )
    elapsed = perf_counter() - start
    return ComparisonResult(
        method_id="closed_source_sidecar",
        category="closed_source",
        success=result.text.strip() == "42",
        final_text=result.text,
        final_value=_parse_exact_int(result.text),
        used_execution=result.used_execution,
        end_to_end_s=elapsed,
        tool_calls=result.tool_calls,
        notes=f"Gemini tool-calling via {result.model}",
    )


def run_five_way_comparison(
    *,
    model_id: str = DEFAULT_QWEN_MODEL_ID,
    device: str = "auto",
    torch_dtype: str = "auto",
    gemini_model: str = DEFAULT_GEMINI_MODEL,
    service: ExecutionService | None = None,
    open_source_runtime: TransformersChatRuntime | None = None,
    closed_source_runtime: GeminiExecutionRuntime | None = None,
) -> list[ComparisonResult]:
    active_service = service or ExecutionService()
    runtime = open_source_runtime or TransformersChatRuntime.from_pretrained(
        model_id=model_id,
        device=device,
        torch_dtype=torch_dtype,
    )
    return [
        run_direct_response("reference_direct", ExecutionMode.REFERENCE, active_service),
        run_direct_response("append_only_naive_direct", ExecutionMode.APPEND_ONLY_NAIVE, active_service),
        run_open_source_wrapper(runtime, active_service),
        run_open_source_execution_block(runtime, active_service),
        run_closed_source_sidecar(gemini_model, runtime=closed_source_runtime),
    ]


def build_json_report(
    results: list[ComparisonResult],
    *,
    open_source_model: str,
    closed_source_model: str,
    device: str,
) -> dict[str, object]:
    return {
        "date": date.today().isoformat(),
        "scenario": {
            "wat_module": CANONICAL_WAT_MODULE,
            "expected_final_value": 42,
        },
        "environment": {
            "open_source_model": open_source_model,
            "closed_source_model": closed_source_model,
            "device": device,
        },
        "results": [result.to_dict() for result in results],
    }


def render_markdown_report(
    results: list[ComparisonResult],
    *,
    open_source_model: str,
    closed_source_model: str,
    device: str,
) -> str:
    successful_results = [result for result in results if result.success]
    fastest = min(successful_results, key=lambda result: result.end_to_end_s) if successful_results else None
    success_count = len(successful_results)
    lines = [
        "# Five-Way Comparison",
        "",
        f"Date: {date.today().isoformat()}",
        "",
        "## Scenario",
        "",
        f"- WAT module: `{CANONICAL_WAT_MODULE}`",
        "- Expected final value: `42`",
        "- Comparison set: semantic control, naive direct baseline, open-source wrapper, open-source execution block, closed-source sidecar",
        "",
        "## Environment",
        "",
        f"- Open-source model: `{open_source_model}`",
        f"- Closed-source model: `{closed_source_model}`",
        f"- Open-source device: `{device}`",
        "",
        "## Results",
        "",
        "| Method | Category | Success | Final Text | Used Execution | End-to-End | Backend | Backend Elapsed | Steps | Intercepted | Structured | Native Rounds | Tool Calls | Notes |",
        "| --- | --- | --- | --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for result in results:
        lines.append(
            "| "
            + " | ".join(
                [
                    result.method_id,
                    result.category,
                    "yes" if result.success else "no",
                    f"`{result.final_text.strip()}`" if result.final_text.strip() else "-",
                    "yes" if result.used_execution else "no",
                    _format_seconds(result.end_to_end_s),
                    result.backend_mode or "-",
                    _format_seconds(result.backend_elapsed_s),
                    str(result.steps) if result.steps is not None else "-",
                    str(result.intercepted_requests) if result.intercepted_requests is not None else "-",
                    str(result.structured_captures) if result.structured_captures is not None else "-",
                    str(result.native_execution_rounds) if result.native_execution_rounds is not None else "-",
                    str(result.tool_calls) if result.tool_calls is not None else "-",
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
            f"- Successful paths: `{success_count}/{len(results)}`",
            f"- Fastest successful path in this run: `{fastest.method_id}` at {_format_seconds(fastest.end_to_end_s)}" if fastest else "- No successful path was recorded.",
            "- `reference_direct` is the semantic control and does not include any model orchestration overhead.",
            "- `append_only_naive_direct` is the direct naive baseline for the article-style append-only execution path.",
            "- `open_source_wrapper` and `open_source_execution_block` share the same Qwen-family runtime and request extraction logic; the difference is whether execution returns through `<exec_response>` text or through native execution feedback.",
            "- `closed_source_sidecar` uses hosted Gemini tool-calling and is not directly latency-comparable to local open-source runs.",
            "",
            "## Raw Results",
            "",
            "```json",
            json.dumps(
                build_json_report(
                    results,
                    open_source_model=open_source_model,
                    closed_source_model=closed_source_model,
                    device=device,
                ),
                indent=2,
                sort_keys=True,
            ),
            "```",
        ]
    )
    return "\n".join(lines)


def write_report(path: str | Path, content: str) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8")


def write_json_report(
    path: str | Path,
    results: list[ComparisonResult],
    *,
    open_source_model: str,
    closed_source_model: str,
    device: str,
) -> None:
    payload = build_json_report(
        results,
        open_source_model=open_source_model,
        closed_source_model=closed_source_model,
        device=device,
    )
    write_report(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the five-way comparison harness.")
    parser.add_argument("--model-id", default=DEFAULT_QWEN_MODEL_ID, help="Hugging Face model identifier for the open-source path.")
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "mps", "cuda"], help="Torch device for the open-source runtime.")
    parser.add_argument("--torch-dtype", default="auto", help="Torch dtype or 'auto'.")
    parser.add_argument("--gemini-model", default=DEFAULT_GEMINI_MODEL, help="Gemini model name for the closed-source path.")
    parser.add_argument("--markdown-output", help="Optional path to write the markdown report.")
    parser.add_argument("--json-output", help="Optional path to write the JSON report.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    results = run_five_way_comparison(
        model_id=args.model_id,
        device=args.device,
        torch_dtype=args.torch_dtype,
        gemini_model=args.gemini_model,
    )
    report = render_markdown_report(
        results,
        open_source_model=args.model_id,
        closed_source_model=args.gemini_model,
        device=args.device,
    )
    print(report)
    if args.markdown_output:
        write_report(args.markdown_output, report + "\n")
    if args.json_output:
        write_json_report(
            args.json_output,
            results,
            open_source_model=args.model_id,
            closed_source_model=args.gemini_model,
            device=args.device,
        )


if __name__ == "__main__":
    main()
