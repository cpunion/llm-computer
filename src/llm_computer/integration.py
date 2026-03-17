"""Open-source and closed-source integration prototypes over the service API."""

from __future__ import annotations

import json
from typing import Protocol

from llm_computer.protocol import ExecutionRequest, ExecutionResponse
from llm_computer.service import ExecutionService


class ExecutionBackend(Protocol):
    """Execution backend shared by wrapper, execution-block, and tool adapters."""

    def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        ...


class OpenSourceRuntimeAdapter:
    """Prototype runtime hook for open-weight models using tagged execution spans."""

    REQUEST_TAG = "exec_request"
    RESPONSE_TAG = "exec_response"

    def __init__(
        self,
        *,
        backend: ExecutionBackend | None = None,
        service: ExecutionService | None = None,
    ) -> None:
        self.backend = backend or service or ExecutionService()

    @classmethod
    def system_prompt(cls) -> str:
        return (
            "When exact execution is needed, emit exactly one <exec_request>...</exec_request> block. "
            "Inside the tags, output a single valid JSON object with keys such as "
            "\"source_kind\", \"source\", \"mode\", and optional \"export_name\". "
            "Do not add markdown fences, explanations, or surrounding prose inside the tags. "
            "Wait for the runtime to inject an <exec_response>...</exec_response> block before continuing."
        )

    @classmethod
    def contains_request(cls, text: str) -> bool:
        return cls.try_extract_request_segment(text) is not None

    @classmethod
    def contains_request_marker(cls, text: str) -> bool:
        start_tag = f"<{cls.REQUEST_TAG}>"
        end_tag = f"</{cls.REQUEST_TAG}>"
        return start_tag in text or end_tag in text

    @classmethod
    def render_request_segment(cls, request: ExecutionRequest) -> str:
        return f"<{cls.REQUEST_TAG}>{request.to_json()}</{cls.REQUEST_TAG}>"

    @classmethod
    def render_response_segment(cls, response: ExecutionResponse) -> str:
        return f"<{cls.RESPONSE_TAG}>{response.to_json()}</{cls.RESPONSE_TAG}>"

    @staticmethod
    def _extract_json_object(payload: str) -> str:
        trimmed = payload.strip()
        if trimmed.startswith("```"):
            lines = trimmed.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            trimmed = "\n".join(lines).strip()

        decoder = json.JSONDecoder()
        for index, char in enumerate(trimmed):
            if char != "{":
                continue
            try:
                _, end = decoder.raw_decode(trimmed[index:])
                return trimmed[index : index + end]
            except json.JSONDecodeError:
                continue
        raise ValueError("Could not extract a valid JSON object from the execution request block")

    @classmethod
    def try_extract_request_segment(cls, text: str) -> str | None:
        start_tag = f"<{cls.REQUEST_TAG}>"
        end_tag = f"</{cls.REQUEST_TAG}>"
        start_index = text.find(start_tag)
        end_index = text.find(end_tag, start_index + len(start_tag)) if start_index >= 0 else -1

        if start_index >= 0:
            payload_end = end_index if end_index >= 0 else len(text)
            payload = text[start_index + len(start_tag) : payload_end].strip()
        else:
            trimmed = text.strip()
            if not (trimmed.startswith("{") or trimmed.startswith("```")):
                return None
            payload = trimmed

        try:
            request = ExecutionRequest.from_json(cls._extract_json_object(payload))
        except Exception:
            return None
        return cls.render_request_segment(request)

    @classmethod
    def parse_request(cls, text: str) -> ExecutionRequest | None:
        canonical_segment = cls.try_extract_request_segment(text)
        if canonical_segment is None:
            if cls.contains_request_marker(text):
                raise ValueError("Could not extract a valid JSON object from the execution request block")
            return None
        return ExecutionRequest.from_json(cls._extract_json_object(canonical_segment))

    def maybe_resolve(self, text: str) -> str:
        start_tag = f"<{self.REQUEST_TAG}>"
        end_tag = f"</{self.REQUEST_TAG}>"
        start_index = text.find(start_tag)
        end_index = text.find(end_tag, start_index + len(start_tag))
        request = self.parse_request(text)
        if request is None:
            return text
        response = self.backend.execute(request)
        response_segment = self.render_response_segment(response)
        if start_index < 0 or end_index < 0:
            return response_segment
        return (
            text[:start_index]
            + response_segment
            + text[end_index + len(end_tag) :]
        )


class ClosedSourceToolAdapter:
    """Prototype tool interface for hosted LLM APIs with structured tool calls."""

    TOOL_NAME = "run_llm_computer"

    def __init__(
        self,
        *,
        backend: ExecutionBackend | None = None,
        service: ExecutionService | None = None,
    ) -> None:
        self.backend = backend or service or ExecutionService()

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
        response = self.backend.execute(request)
        return response.to_json()

    def invoke_dict(self, arguments: dict[str, object]) -> dict[str, object]:
        return json.loads(self.invoke(json.dumps(arguments)))
