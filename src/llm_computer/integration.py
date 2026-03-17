"""Open-source and closed-source integration prototypes over the service API."""

from __future__ import annotations

import json

from llm_computer.protocol import ExecutionRequest, ExecutionResponse
from llm_computer.service import ExecutionService


class OpenSourceRuntimeAdapter:
    """Prototype runtime hook for open-weight models using tagged execution spans."""

    REQUEST_TAG = "exec_request"
    RESPONSE_TAG = "exec_response"

    def __init__(self, service: ExecutionService | None = None) -> None:
        self.service = service or ExecutionService()

    @classmethod
    def system_prompt(cls) -> str:
        return (
            "When exact execution is needed, emit exactly one <exec_request>{...}</exec_request> block "
            "that matches the execution schema. Wait for the runtime to inject an "
            "<exec_response>{...}</exec_response> block before continuing."
        )

    @classmethod
    def render_request_segment(cls, request: ExecutionRequest) -> str:
        return f"<{cls.REQUEST_TAG}>{request.to_json()}</{cls.REQUEST_TAG}>"

    @classmethod
    def render_response_segment(cls, response: ExecutionResponse) -> str:
        return f"<{cls.RESPONSE_TAG}>{response.to_json()}</{cls.RESPONSE_TAG}>"

    def maybe_resolve(self, text: str) -> str:
        start_tag = f"<{self.REQUEST_TAG}>"
        end_tag = f"</{self.REQUEST_TAG}>"
        start_index = text.find(start_tag)
        end_index = text.find(end_tag, start_index + len(start_tag))
        if start_index < 0 or end_index < 0:
            return text
        payload = text[start_index + len(start_tag) : end_index].strip()
        request = ExecutionRequest.from_json(payload)
        response = self.service.execute(request)
        return (
            text[:start_index]
            + self.render_response_segment(response)
            + text[end_index + len(end_tag) :]
        )


class ClosedSourceToolAdapter:
    """Prototype tool interface for hosted LLM APIs with structured tool calls."""

    TOOL_NAME = "run_llm_computer"

    def __init__(self, service: ExecutionService | None = None) -> None:
        self.service = service or ExecutionService()

    @classmethod
    def planner_instructions(cls) -> str:
        return (
            "Use the run_llm_computer tool whenever exact WASM execution is needed. "
            "Pass only valid JSON that matches the published request schema."
        )

    @classmethod
    def tool_spec(cls) -> dict[str, object]:
        return {
            "type": "function",
            "function": {
                "name": cls.TOOL_NAME,
                "description": "Execute WAT, C, or base64-encoded WASM through the llm-computer sidecar.",
                "parameters": ExecutionRequest.json_schema(),
            },
        }

    def invoke(self, arguments_json: str) -> str:
        request = ExecutionRequest.from_json(arguments_json)
        response = self.service.execute(request)
        return response.to_json()

    def invoke_dict(self, arguments: dict[str, object]) -> dict[str, object]:
        return json.loads(self.invoke(json.dumps(arguments)))
