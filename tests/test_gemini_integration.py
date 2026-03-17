from __future__ import annotations

import types
import unittest

from llm_computer.gemini_integration import GeminiExecutionRuntime, gemini_available


class FakeResponse:
    def __init__(self, text: str | None, *, function_calls=None, content=None) -> None:
        self.text = text
        self.function_calls = function_calls or []
        self.candidates = [types.SimpleNamespace(content=content)] if content is not None else []


class FakeFunctionCall:
    def __init__(self, name: str, args: dict[str, object]) -> None:
        self.name = name
        self.args = args


class FakePart:
    @staticmethod
    def from_function_response(*, name: str, response: dict[str, object]):
        return types.SimpleNamespace(name=name, response=response)


class FakeModels:
    def __init__(self, outer: "FakeClient") -> None:
        self.outer = outer

    def generate_content(self, *, model: str, contents, config) -> FakeResponse:
        self.outer.calls.append(
            {
                "model": model,
                "contents": contents,
                "system_instruction": getattr(config, "system_instruction", None),
                "temperature": getattr(config, "temperature", None),
                "tools": getattr(config, "tools", []),
                "tool_config": getattr(config, "tool_config", None),
            }
        )
        if len(self.outer.calls) == 1:
            function_call = FakeFunctionCall(
                "run_llm_computer",
                {
                    "source_kind": "wat",
                    "source": '(module (func (export "main") (result i32) i32.const 8 i32.const 5 i32.add))',
                    "mode": "auto",
                    "trace_limit": 1,
                },
            )
            return FakeResponse(
                None,
                function_calls=[function_call],
                content=types.SimpleNamespace(parts=[types.SimpleNamespace(function_call=function_call)]),
            )

        function_response = contents[-1].parts[0].response["output"]
        self.outer.tool_results.append(function_response)
        return FakeResponse("The exact result is 13.", content=types.SimpleNamespace(parts=[types.SimpleNamespace(text="The exact result is 13.")]))


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.tool_results: list[dict[str, object]] = []
        self.models = FakeModels(self)


class FakeTypesModule:
    @staticmethod
    def GenerateContentConfig(**kwargs):
        return types.SimpleNamespace(**kwargs)

    @staticmethod
    def Tool(**kwargs):
        return types.SimpleNamespace(**kwargs)

    @staticmethod
    def FunctionDeclaration(**kwargs):
        return types.SimpleNamespace(**kwargs)

    @staticmethod
    def ToolConfig(**kwargs):
        return types.SimpleNamespace(**kwargs)

    @staticmethod
    def FunctionCallingConfig(**kwargs):
        return types.SimpleNamespace(**kwargs)

    class FunctionCallingConfigMode:
        ANY = "ANY"

    Part = FakePart

    @staticmethod
    def UserContent(*, parts):
        return types.SimpleNamespace(role="user", parts=parts)


class GeminiIntegrationTest(unittest.TestCase):
    def test_runtime_executes_tool_and_returns_result(self) -> None:
        client = FakeClient()
        runtime = GeminiExecutionRuntime(client=client, model="gemini-test")

        from llm_computer import gemini_integration as module

        original = module._require_gemini
        module._require_gemini = lambda: (lambda: None, object(), FakeTypesModule)
        try:
            result = runtime.run("Compute 8 + 5 exactly.", force_tool_use=True)
        finally:
            module._require_gemini = original

        self.assertEqual("gemini-test", result.model)
        self.assertEqual("The exact result is 13.", result.text)
        self.assertTrue(result.used_execution)
        self.assertEqual(1, result.tool_calls)
        self.assertEqual([13], client.tool_results[0]["results"])
        self.assertEqual("ANY", client.calls[0]["tool_config"].function_calling_config.mode)

    def test_missing_optional_dependencies_raise_helpful_error(self) -> None:
        if gemini_available():
            self.skipTest("Gemini dependencies are installed in this environment")
        from llm_computer.gemini_integration import _require_gemini

        with self.assertRaisesRegex(RuntimeError, "uv sync --extra gemini"):
            _require_gemini()


if __name__ == "__main__":
    unittest.main()
