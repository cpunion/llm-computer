from __future__ import annotations

import unittest

from llm_computer.qwen_transformers import (
    GenerationSettings,
    QwenExecutionOrchestrator,
    TransformersChatRuntime,
    transformers_available,
)


SUPPORTED_WAT_REQUEST = """
<exec_request>{
  "source_kind": "wat",
  "source": "(module (func (export \\"main\\") (result i32) i32.const 6 i32.const 7 i32.mul))",
  "mode": "auto",
  "trace_limit": 1
}</exec_request>
"""


class FakeRuntime:
    def __init__(self, outputs: list[str]) -> None:
        self.outputs = outputs[:]
        self.calls: list[list[dict[str, str]]] = []

    def generate(self, messages: list[dict[str, str]], settings: GenerationSettings) -> str:
        self.calls.append([{"role": message["role"], "content": message["content"]} for message in messages])
        if not self.outputs:
            raise AssertionError("No more fake outputs available")
        return self.outputs.pop(0)


class FakeInterceptRuntime(FakeRuntime):
    def __init__(self, outputs: list[str], intercepted_outputs: list[str]) -> None:
        super().__init__(outputs)
        self.intercepted_outputs = intercepted_outputs[:]
        self.intercept_calls: list[list[dict[str, str]]] = []

    def generate_until_request_boundary(self, messages: list[dict[str, str]], settings: GenerationSettings) -> str:
        self.intercept_calls.append([{"role": message["role"], "content": message["content"]} for message in messages])
        if not self.intercepted_outputs:
            raise AssertionError("No more fake intercepted outputs available")
        return self.intercepted_outputs.pop(0)


class QwenTransformersOrchestratorTest(unittest.TestCase):
    def test_prepare_messages_includes_execution_prompt(self) -> None:
        messages = QwenExecutionOrchestrator.prepare_messages(
            "Compute exactly.",
            system_prompt="You are a precise assistant.",
        )
        self.assertEqual("system", messages[0]["role"])
        self.assertIn("You are a precise assistant.", messages[0]["content"])
        self.assertIn("<exec_request>...</exec_request>", messages[0]["content"])
        self.assertIn("Do not add markdown fences", messages[0]["content"])
        self.assertEqual("user", messages[1]["role"])

    def test_prepare_messages_can_include_protocol_example(self) -> None:
        messages = QwenExecutionOrchestrator.prepare_messages(
            "Compute exactly.",
            include_protocol_example=True,
        )
        self.assertEqual("system", messages[0]["role"])
        self.assertIn("<exec_request>", messages[2]["content"])
        self.assertIn("<exec_response>", messages[3]["content"])
        self.assertEqual("6", messages[4]["content"])

    def test_run_handles_execution_round_trip(self) -> None:
        runtime = FakeRuntime(
            [
                SUPPORTED_WAT_REQUEST,
                "The exact result is 42.",
            ]
        )
        orchestrator = QwenExecutionOrchestrator(runtime)
        messages = QwenExecutionOrchestrator.prepare_messages("What is 6 * 7?")
        result = orchestrator.run(messages)

        self.assertTrue(result.used_execution)
        self.assertEqual("assistant_completed", result.stop_reason)
        self.assertEqual("The exact result is 42.", result.final_text)
        self.assertEqual(2, len(result.turns))
        self.assertIn("<exec_response>", result.turns[0].exec_response or "")
        self.assertEqual(2, len(runtime.calls))
        self.assertIn("Runtime execution response:", runtime.calls[1][-1]["content"])
        self.assertIn("[42]", runtime.calls[1][-1]["content"])

    def test_run_stops_without_execution(self) -> None:
        runtime = FakeRuntime(["No exact execution was needed."])
        orchestrator = QwenExecutionOrchestrator(runtime)
        result = orchestrator.run(QwenExecutionOrchestrator.prepare_messages("Say hello."))

        self.assertFalse(result.used_execution)
        self.assertEqual("assistant_completed", result.stop_reason)
        self.assertEqual("No exact execution was needed.", result.final_text)

    def test_run_recovers_from_malformed_execution_request(self) -> None:
        runtime = FakeRuntime(
            [
                "<exec_request>not json</exec_request>",
                SUPPORTED_WAT_REQUEST,
                "42",
            ]
        )
        orchestrator = QwenExecutionOrchestrator(runtime)
        result = orchestrator.run(QwenExecutionOrchestrator.prepare_messages("Compute exactly."), max_round_trips=3)

        self.assertTrue(result.used_execution)
        self.assertEqual("assistant_completed", result.stop_reason)
        self.assertEqual("42", result.final_text)
        self.assertIn("Runtime parsing error:", runtime.calls[1][-1]["content"])

    def test_run_uses_request_interception_when_supported(self) -> None:
        runtime = FakeInterceptRuntime(
            outputs=["42"],
            intercepted_outputs=[SUPPORTED_WAT_REQUEST],
        )
        orchestrator = QwenExecutionOrchestrator(runtime)
        result = orchestrator.run(
            QwenExecutionOrchestrator.prepare_messages("Compute exactly."),
            settings=GenerationSettings(intercept_request_boundary=True),
        )

        self.assertTrue(result.used_execution)
        self.assertEqual(1, result.intercepted_requests)
        self.assertEqual("42", result.final_text)
        self.assertEqual(1, len(runtime.intercept_calls))
        self.assertEqual(1, len(runtime.calls))

    def test_run_falls_back_when_request_interception_is_unavailable(self) -> None:
        runtime = FakeRuntime([SUPPORTED_WAT_REQUEST, "42"])
        orchestrator = QwenExecutionOrchestrator(runtime)
        result = orchestrator.run(
            QwenExecutionOrchestrator.prepare_messages("Compute exactly."),
            settings=GenerationSettings(intercept_request_boundary=True),
        )

        self.assertTrue(result.used_execution)
        self.assertEqual(0, result.intercepted_requests)
        self.assertEqual("42", result.final_text)

    def test_from_pretrained_requires_optional_dependencies(self) -> None:
        if transformers_available():
            self.skipTest("Transformers dependencies are installed in this environment")
        with self.assertRaisesRegex(RuntimeError, "uv sync --extra transformers"):
            TransformersChatRuntime.from_pretrained()


if __name__ == "__main__":
    unittest.main()
