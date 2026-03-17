from __future__ import annotations

from dataclasses import dataclass
import unittest

from llm_computer.comparison import (
    build_json_report,
    render_markdown_report,
    run_closed_source_sidecar,
    run_direct_response,
    run_five_way_comparison,
    run_open_source_execution_block,
    run_open_source_wrapper,
)
from llm_computer.protocol import ExecutionMode, ExecutionRequest, ExecutionResponse, SourceKind


STRUCTURED_WAT_REQUEST = (
    '{"source_kind":"wat","source":"(module (func (export \\"main\\") (result i32) i32.const 6 i32.const 7 i32.mul))",'
    '"mode":"auto","trace_limit":1}'
)


class FakeExecutionService:
    def __init__(self) -> None:
        self.requests: list[ExecutionRequest] = []

    def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        self.requests.append(request)
        mode_used = request.mode if request.mode != ExecutionMode.AUTO else ExecutionMode.TRANSFORMER_HULL
        return ExecutionResponse(
            ok=True,
            mode_requested=request.mode,
            mode_used=mode_used,
            source_kind=request.source_kind,
            export_name=request.export_name,
            results=[42],
            steps=3,
            elapsed_s=0.001,
            tokens_per_s=3000.0,
            transformer_subset=True,
        )


class FakeRuntime:
    def __init__(self, outputs: list[str]) -> None:
        self.outputs = outputs[:]
        self.calls: list[list[dict[str, str]]] = []

    def generate(self, messages: list[dict[str, str]], settings) -> str:
        self.calls.append([{"role": message["role"], "content": message["content"]} for message in messages])
        if not self.outputs:
            raise AssertionError("No more fake outputs available")
        return self.outputs.pop(0)


@dataclass(slots=True)
class FakeGeminiResult:
    model: str
    text: str
    used_execution: bool
    tool_calls: int


class FakeGeminiRuntime:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def run(self, prompt: str, *, system_prompt: str | None = None, force_tool_use: bool = False) -> FakeGeminiResult:
        self.calls.append(
            {
                "prompt": prompt,
                "system_prompt": system_prompt,
                "force_tool_use": force_tool_use,
            }
        )
        return FakeGeminiResult(
            model="gemini-test",
            text="42",
            used_execution=True,
            tool_calls=1,
        )


class ComparisonHarnessTest(unittest.TestCase):
    def test_run_direct_response_uses_requested_mode(self) -> None:
        service = FakeExecutionService()

        result = run_direct_response("append_only_naive_direct", ExecutionMode.APPEND_ONLY_NAIVE, service)

        self.assertTrue(result.success)
        self.assertEqual("append_only_naive", result.backend_mode)
        self.assertEqual(ExecutionMode.APPEND_ONLY_NAIVE, service.requests[0].mode)

    def test_run_open_source_wrapper_collects_execution_metrics(self) -> None:
        service = FakeExecutionService()
        runtime = FakeRuntime([STRUCTURED_WAT_REQUEST, "42"])

        result = run_open_source_wrapper(runtime, service)

        self.assertTrue(result.success)
        self.assertEqual("42", result.final_text)
        self.assertEqual("transformer_hull", result.backend_mode)
        self.assertEqual(ExecutionMode.AUTO, service.requests[0].mode)
        self.assertTrue(result.used_execution)

    def test_run_open_source_execution_block_pins_transformer_backend(self) -> None:
        service = FakeExecutionService()
        runtime = FakeRuntime([STRUCTURED_WAT_REQUEST, "42"])

        result = run_open_source_execution_block(runtime, service)

        self.assertTrue(result.success)
        self.assertEqual(1, result.native_execution_rounds)
        self.assertEqual(ExecutionMode.TRANSFORMER_HULL, service.requests[0].mode)

    def test_run_closed_source_sidecar_uses_injected_runtime(self) -> None:
        runtime = FakeGeminiRuntime()

        result = run_closed_source_sidecar("gemini-test", runtime=runtime)

        self.assertTrue(result.success)
        self.assertEqual(1, result.tool_calls)
        self.assertTrue(runtime.calls[0]["force_tool_use"])
        self.assertIn("execution tool", str(runtime.calls[0]["prompt"]))

    def test_run_five_way_comparison_reuses_shared_runtime_and_service(self) -> None:
        service = FakeExecutionService()
        open_source_runtime = FakeRuntime([STRUCTURED_WAT_REQUEST, "42", STRUCTURED_WAT_REQUEST, "42"])
        closed_source_runtime = FakeGeminiRuntime()

        results = run_five_way_comparison(
            model_id="qwen-test",
            device="cpu",
            torch_dtype="auto",
            gemini_model="gemini-test",
            service=service,
            open_source_runtime=open_source_runtime,
            closed_source_runtime=closed_source_runtime,
        )

        self.assertEqual(
            [
                "reference_direct",
                "append_only_naive_direct",
                "open_source_wrapper",
                "open_source_execution_block",
                "closed_source_sidecar",
            ],
            [result.method_id for result in results],
        )
        self.assertEqual(4, len(service.requests))
        self.assertEqual(4, len(open_source_runtime.calls))

    def test_report_renderers_include_environment_and_rows(self) -> None:
        results = [
            run_direct_response("reference_direct", ExecutionMode.REFERENCE, FakeExecutionService()),
            run_direct_response("append_only_naive_direct", ExecutionMode.APPEND_ONLY_NAIVE, FakeExecutionService()),
        ]

        markdown = render_markdown_report(
            results,
            open_source_model="qwen-test",
            closed_source_model="gemini-test",
            device="cpu",
        )
        payload = build_json_report(
            results,
            open_source_model="qwen-test",
            closed_source_model="gemini-test",
            device="cpu",
        )

        self.assertIn("# Five-Way Comparison", markdown)
        self.assertIn("reference_direct", markdown)
        self.assertEqual("qwen-test", payload["environment"]["open_source_model"])
        self.assertEqual(2, len(payload["results"]))


if __name__ == "__main__":
    unittest.main()
