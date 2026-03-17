"""Stable request and response protocol for execution sidecars."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
import json


class SourceKind(StrEnum):
    """Program source formats accepted by the execution service."""

    WAT = "wat"
    C = "c"
    WASM_BASE64 = "wasm_base64"


class ExecutionMode(StrEnum):
    """Execution backends exposed through the stable protocol."""

    AUTO = "auto"
    REFERENCE = "reference"
    APPEND_ONLY_NAIVE = "append_only_naive"
    APPEND_ONLY_HULL = "append_only_hull"
    TRANSFORMER_NAIVE = "transformer_naive"
    TRANSFORMER_HULL = "transformer_hull"


@dataclass(slots=True)
class TracePreviewEntry:
    step: int
    ip: int
    instruction: str
    value: int
    stack_delta: int
    stack_size: int
    branch_taken: bool


@dataclass(slots=True)
class ExecutionRequest:
    """A transport-safe request that can be emitted by an LLM or runtime."""

    source_kind: SourceKind
    source: str
    export_name: str = "main"
    mode: ExecutionMode = ExecutionMode.AUTO
    max_steps: int = 200_000
    trace_limit: int = 8
    c_opt_level: str = "-O2"

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["source_kind"] = self.source_kind.value
        payload["mode"] = self.mode.value
        return payload

    def to_json(self, *, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ExecutionRequest":
        return cls(
            source_kind=SourceKind(str(payload["source_kind"])),
            source=str(payload["source"]),
            export_name=str(payload.get("export_name", "main")),
            mode=ExecutionMode(str(payload.get("mode", ExecutionMode.AUTO.value))),
            max_steps=int(payload.get("max_steps", 200_000)),
            trace_limit=int(payload.get("trace_limit", 8)),
            c_opt_level=str(payload.get("c_opt_level", "-O2")),
        )

    @classmethod
    def from_json(cls, raw: str) -> "ExecutionRequest":
        return cls.from_dict(json.loads(raw))

    @classmethod
    def json_schema(cls) -> dict[str, object]:
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["source_kind", "source"],
            "properties": {
                "source_kind": {"type": "string", "enum": [kind.value for kind in SourceKind]},
                "source": {"type": "string"},
                "export_name": {"type": "string", "default": "main"},
                "mode": {"type": "string", "enum": [mode.value for mode in ExecutionMode], "default": "auto"},
                "max_steps": {"type": "integer", "minimum": 1, "default": 200000},
                "trace_limit": {"type": "integer", "minimum": 0, "default": 8},
                "c_opt_level": {"type": "string", "default": "-O2"},
            },
        }


@dataclass(slots=True)
class ExecutionResponse:
    """Structured result returned by the execution service."""

    ok: bool
    mode_requested: ExecutionMode
    mode_used: ExecutionMode
    source_kind: SourceKind
    export_name: str
    results: list[int] = field(default_factory=list)
    steps: int = 0
    elapsed_s: float = 0.0
    tokens_per_s: float = 0.0
    transformer_subset: bool = False
    trace_preview: list[TracePreviewEntry] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["mode_requested"] = self.mode_requested.value
        payload["mode_used"] = self.mode_used.value
        payload["source_kind"] = self.source_kind.value
        return payload

    def to_json(self, *, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ExecutionResponse":
        trace_payload = payload.get("trace_preview", [])
        return cls(
            ok=bool(payload["ok"]),
            mode_requested=ExecutionMode(str(payload["mode_requested"])),
            mode_used=ExecutionMode(str(payload["mode_used"])),
            source_kind=SourceKind(str(payload["source_kind"])),
            export_name=str(payload["export_name"]),
            results=[int(value) for value in payload.get("results", [])],
            steps=int(payload.get("steps", 0)),
            elapsed_s=float(payload.get("elapsed_s", 0.0)),
            tokens_per_s=float(payload.get("tokens_per_s", 0.0)),
            transformer_subset=bool(payload.get("transformer_subset", False)),
            trace_preview=[
                TracePreviewEntry(
                    step=int(entry["step"]),
                    ip=int(entry["ip"]),
                    instruction=str(entry["instruction"]),
                    value=int(entry["value"]),
                    stack_delta=int(entry["stack_delta"]),
                    stack_size=int(entry["stack_size"]),
                    branch_taken=bool(entry["branch_taken"]),
                )
                for entry in trace_payload
            ],
            notes=[str(note) for note in payload.get("notes", [])],
            error=str(payload["error"]) if payload.get("error") is not None else None,
        )

    @classmethod
    def from_json(cls, raw: str) -> "ExecutionResponse":
        return cls.from_dict(json.loads(raw))

    @classmethod
    def json_schema(cls) -> dict[str, object]:
        return {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "ok",
                "mode_requested",
                "mode_used",
                "source_kind",
                "export_name",
                "results",
                "steps",
                "elapsed_s",
                "tokens_per_s",
                "transformer_subset",
                "trace_preview",
                "notes",
            ],
            "properties": {
                "ok": {"type": "boolean"},
                "mode_requested": {"type": "string", "enum": [mode.value for mode in ExecutionMode]},
                "mode_used": {"type": "string", "enum": [mode.value for mode in ExecutionMode]},
                "source_kind": {"type": "string", "enum": [kind.value for kind in SourceKind]},
                "export_name": {"type": "string"},
                "results": {"type": "array", "items": {"type": "integer"}},
                "steps": {"type": "integer"},
                "elapsed_s": {"type": "number"},
                "tokens_per_s": {"type": "number"},
                "transformer_subset": {"type": "boolean"},
                "trace_preview": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "step",
                            "ip",
                            "instruction",
                            "value",
                            "stack_delta",
                            "stack_size",
                            "branch_taken",
                        ],
                        "properties": {
                            "step": {"type": "integer"},
                            "ip": {"type": "integer"},
                            "instruction": {"type": "string"},
                            "value": {"type": "integer"},
                            "stack_delta": {"type": "integer"},
                            "stack_size": {"type": "integer"},
                            "branch_taken": {"type": "boolean"},
                        },
                    },
                },
                "notes": {"type": "array", "items": {"type": "string"}},
                "error": {"type": ["string", "null"]},
            },
        }
