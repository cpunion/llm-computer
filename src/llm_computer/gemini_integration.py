"""Gemini integration over the closed-source tool-style execution adapter."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any

from llm_computer.integration import ClosedSourceToolAdapter


DEFAULT_GEMINI_MODEL = "gemini-3-flash-preview"


@dataclass(slots=True)
class GeminiRunResult:
    """Structured result from one Gemini execution-aware request."""

    model: str
    text: str
    used_execution: bool
    tool_calls: int


def _require_gemini() -> tuple[Any, Any, Any]:
    try:
        from dotenv import load_dotenv
        from google import genai
        from google.genai import types
    except ImportError as exc:  # pragma: no cover - exercised in tests
        raise RuntimeError(
            "Gemini integration requires optional dependencies. "
            "Install them with: uv sync --extra gemini"
        ) from exc
    return load_dotenv, genai, types


def gemini_available() -> bool:
    try:
        _require_gemini()
    except RuntimeError:
        return False
    return True


class GeminiExecutionRuntime:
    """Executes prompts through Gemini with the llm-computer tool adapter."""

    def __init__(self, client: Any, *, model: str = DEFAULT_GEMINI_MODEL, adapter: ClosedSourceToolAdapter | None = None) -> None:
        self.client = client
        self.model = model
        self.adapter = adapter or ClosedSourceToolAdapter()

    @classmethod
    def from_env(
        cls,
        *,
        model: str = DEFAULT_GEMINI_MODEL,
        api_key: str | None = None,
        load_dotenv_file: bool = True,
    ) -> "GeminiExecutionRuntime":
        load_dotenv, genai, _ = _require_gemini()
        if load_dotenv_file:
            load_dotenv(".env")
        key = api_key or os.getenv("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        client = genai.Client(api_key=key)
        return cls(client=client, model=model)

    def _system_instruction(self, system_prompt: str | None) -> str:
        planner = ClosedSourceToolAdapter.planner_instructions()
        if system_prompt:
            return f"{system_prompt.strip()}\n\n{planner}"
        return planner

    def _tool(self, types: Any) -> Any:
        spec = ClosedSourceToolAdapter.tool_spec()["function"]
        return types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name=spec["name"],
                    description=spec["description"],
                    parameters_json_schema=spec["parameters"],
                )
            ]
        )

    def _config(self, types: Any, *, system_prompt: str | None, temperature: float, force_tool_use: bool) -> Any:
        config_kwargs: dict[str, object] = {
            "temperature": temperature,
            "tools": [self._tool(types)],
            "system_instruction": self._system_instruction(system_prompt),
        }
        if force_tool_use:
            config_kwargs["tool_config"] = types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(
                    mode=types.FunctionCallingConfigMode.ANY,
                    allowed_function_names=[ClosedSourceToolAdapter.TOOL_NAME],
                )
            )
        return types.GenerateContentConfig(**config_kwargs)

    def run(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        force_tool_use: bool = False,
    ) -> GeminiRunResult:
        _, _, types = _require_gemini()
        conversation: list[Any] = [prompt]
        response = self.client.models.generate_content(
            model=self.model,
            contents=conversation,
            config=self._config(
                types,
                system_prompt=system_prompt,
                temperature=temperature,
                force_tool_use=force_tool_use,
            ),
        )
        function_calls = list(getattr(response, "function_calls", []) or [])
        if function_calls:
            conversation.append(response.candidates[0].content)
            response_parts: list[Any] = []
            for function_call in function_calls:
                try:
                    tool_result = self.adapter.invoke_dict(dict(function_call.args))
                except Exception as exc:  # pragma: no cover - defensive in live mode
                    tool_result = {"ok": False, "error": str(exc)}
                response_parts.append(
                    types.Part.from_function_response(
                        name=function_call.name,
                        response={"output": tool_result},
                    )
                )
            conversation.append(types.UserContent(parts=response_parts))
            response = self.client.models.generate_content(
                model=self.model,
                contents=conversation,
                config=self._config(
                    types,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    force_tool_use=False,
                ),
            )
        return GeminiRunResult(
            model=self.model,
            text=getattr(response, "text", "") or "",
            used_execution=bool(function_calls),
            tool_calls=len(function_calls),
        )
