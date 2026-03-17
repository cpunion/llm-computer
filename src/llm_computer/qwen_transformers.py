"""Qwen3 plus Transformers integration over the execution sidecar protocol."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from typing import Any, Protocol

from llm_computer.integration import OpenSourceRuntimeAdapter
from llm_computer.service import ExecutionService


DEFAULT_QWEN_MODEL_ID = "Qwen/Qwen3-8B"


@dataclass(slots=True)
class GenerationSettings:
    """Generation parameters for the Transformers-backed chat runtime."""

    max_new_tokens: int = 512
    do_sample: bool = False
    temperature: float = 0.0
    top_p: float | None = None
    add_generation_prompt: bool = True
    enable_thinking: bool | None = False


@dataclass(slots=True)
class ExecutionTurn:
    """One assistant turn and its optional execution response."""

    assistant_text: str
    exec_response: str | None = None


@dataclass(slots=True)
class ExecutionConversationResult:
    """Result of an execution-aware chat loop."""

    final_text: str
    stop_reason: str
    used_execution: bool
    turns: list[ExecutionTurn] = field(default_factory=list)
    messages: list[dict[str, str]] = field(default_factory=list)


class ChatRuntime(Protocol):
    """Minimal runtime surface needed by the execution loop."""

    def generate(self, messages: list[dict[str, str]], settings: GenerationSettings) -> str:
        ...


def transformers_available() -> bool:
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401
    except ImportError:
        return False
    return True


def _require_transformers() -> tuple[Any, Any, Any]:
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:  # pragma: no cover - exercised in unit tests
        raise RuntimeError(
            "Qwen3 Transformers integration requires optional dependencies. "
            "Install them with: uv sync --extra transformers"
        ) from exc
    return torch, AutoModelForCausalLM, AutoTokenizer


def resolve_device(requested_device: str = "auto") -> str:
    """Chooses a practical runtime device for local Transformers execution."""

    torch, _, _ = _require_transformers()

    if requested_device == "auto":
        if hasattr(torch, "cuda") and torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    if requested_device == "cuda" and not (hasattr(torch, "cuda") and torch.cuda.is_available()):
        raise RuntimeError("CUDA was requested but is not available")
    if requested_device == "mps" and not (hasattr(torch.backends, "mps") and torch.backends.mps.is_available()):
        raise RuntimeError("MPS was requested but is not available")
    return requested_device


def resolve_torch_dtype(torch_dtype: str | Any, device: str) -> str | Any:
    """Resolves a stable dtype choice for the requested runtime device."""

    torch, _, _ = _require_transformers()
    if torch_dtype != "auto":
        return getattr(torch, torch_dtype, torch_dtype) if isinstance(torch_dtype, str) else torch_dtype
    if device == "mps":
        return torch.float16
    return torch_dtype


class TransformersChatRuntime:
    """A minimal chat runtime around AutoTokenizer and AutoModelForCausalLM."""

    def __init__(self, tokenizer: Any, model: Any, model_id: str, device: str) -> None:
        self.tokenizer = tokenizer
        self.model = model
        self.model_id = model_id
        self.device = device

    @classmethod
    def from_pretrained(
        cls,
        model_id: str = DEFAULT_QWEN_MODEL_ID,
        *,
        torch_dtype: str | Any = "auto",
        device: str = "auto",
        device_map: str | dict[str, int | str] = "auto",
        use_device_map: bool | None = None,
        tokenizer_kwargs: dict[str, Any] | None = None,
        model_kwargs: dict[str, Any] | None = None,
    ) -> "TransformersChatRuntime":
        _, auto_model, auto_tokenizer = _require_transformers()
        resolved_device = resolve_device(device)
        resolved_dtype = resolve_torch_dtype(torch_dtype, resolved_device)
        load_with_device_map = use_device_map if use_device_map is not None else (resolved_device == "cuda")

        if resolved_device == "mps":
            os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

        tokenizer = auto_tokenizer.from_pretrained(model_id, **(tokenizer_kwargs or {}))
        final_model_kwargs = {"low_cpu_mem_usage": True}
        if model_kwargs:
            final_model_kwargs.update(model_kwargs)
        if load_with_device_map:
            final_model_kwargs["device_map"] = device_map
        try:
            model = auto_model.from_pretrained(model_id, dtype=resolved_dtype, **final_model_kwargs)
        except TypeError:
            model = auto_model.from_pretrained(model_id, torch_dtype=resolved_dtype, **final_model_kwargs)
        model.eval()
        if not load_with_device_map and resolved_device != "cpu":
            model.to(resolved_device)
        return cls(tokenizer=tokenizer, model=model, model_id=model_id, device=resolved_device)

    def render_prompt(self, messages: list[dict[str, str]], settings: GenerationSettings) -> str:
        if hasattr(self.tokenizer, "apply_chat_template"):
            kwargs: dict[str, Any] = {
                "tokenize": False,
                "add_generation_prompt": settings.add_generation_prompt,
            }
            if settings.enable_thinking is not None:
                kwargs["enable_thinking"] = settings.enable_thinking
            try:
                return self.tokenizer.apply_chat_template(messages, **kwargs)
            except TypeError:
                kwargs.pop("enable_thinking", None)
                return self.tokenizer.apply_chat_template(messages, **kwargs)

        lines: list[str] = []
        for message in messages:
            role = message["role"].upper()
            lines.append(f"{role}: {message['content']}")
        if settings.add_generation_prompt:
            lines.append("ASSISTANT:")
        return "\n".join(lines)

    def generate(self, messages: list[dict[str, str]], settings: GenerationSettings) -> str:
        prompt = self.render_prompt(messages, settings)
        model_inputs = self.tokenizer([prompt], return_tensors="pt")
        if hasattr(model_inputs, "to"):
            model_inputs = model_inputs.to(self.device)

        generate_kwargs: dict[str, Any] = {
            "max_new_tokens": settings.max_new_tokens,
            "do_sample": settings.do_sample,
        }
        if settings.do_sample:
            generate_kwargs["temperature"] = settings.temperature
            if settings.top_p is not None:
                generate_kwargs["top_p"] = settings.top_p

        generated_ids = self.model.generate(**model_inputs, **generate_kwargs)
        input_ids = model_inputs["input_ids"]
        output_ids = generated_ids[0][len(input_ids[0]) :]
        return self.tokenizer.decode(output_ids, skip_special_tokens=True)


class QwenExecutionOrchestrator:
    """Execution-aware chat loop for Qwen3 in Transformers."""

    def __init__(
        self,
        runtime: ChatRuntime,
        *,
        service: ExecutionService | None = None,
        response_role: str = "user",
    ) -> None:
        self.runtime = runtime
        self.response_role = response_role
        self.adapter = OpenSourceRuntimeAdapter(service=service)

    @classmethod
    def from_pretrained(
        cls,
        model_id: str = DEFAULT_QWEN_MODEL_ID,
        *,
        service: ExecutionService | None = None,
        response_role: str = "user",
        torch_dtype: str | Any = "auto",
        device: str = "auto",
        device_map: str | dict[str, int | str] = "auto",
        use_device_map: bool | None = None,
        tokenizer_kwargs: dict[str, Any] | None = None,
        model_kwargs: dict[str, Any] | None = None,
    ) -> "QwenExecutionOrchestrator":
        runtime = TransformersChatRuntime.from_pretrained(
            model_id=model_id,
            torch_dtype=torch_dtype,
            device=device,
            device_map=device_map,
            use_device_map=use_device_map,
            tokenizer_kwargs=tokenizer_kwargs,
            model_kwargs=model_kwargs,
        )
        return cls(runtime=runtime, service=service, response_role=response_role)

    @staticmethod
    def combined_system_prompt(base_prompt: str | None = None) -> str:
        runtime_prompt = OpenSourceRuntimeAdapter.system_prompt()
        if base_prompt is None or not base_prompt.strip():
            return runtime_prompt
        return f"{base_prompt.strip()}\n\n{runtime_prompt}"

    @classmethod
    def prepare_messages(
        cls,
        user_prompt: str,
        *,
        system_prompt: str | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        combined = cls.combined_system_prompt(system_prompt)
        if combined:
            messages.append({"role": "system", "content": combined})
        if history:
            messages.extend({"role": message["role"], "content": message["content"]} for message in history)
        messages.append({"role": "user", "content": user_prompt})
        return messages

    def render_runtime_feedback(self, exec_response: str) -> str:
        return (
            "Runtime execution response:\n"
            f"{exec_response}\n\n"
            "Continue from the runtime result. Do not repeat the execution request verbatim."
        )

    def run(
        self,
        messages: list[dict[str, str]],
        *,
        settings: GenerationSettings | None = None,
        max_round_trips: int = 4,
    ) -> ExecutionConversationResult:
        conversation = [{"role": message["role"], "content": message["content"]} for message in messages]
        settings = settings or GenerationSettings()
        turns: list[ExecutionTurn] = []
        used_execution = False

        for _ in range(max_round_trips):
            assistant_text = self.runtime.generate(conversation, settings)
            conversation.append({"role": "assistant", "content": assistant_text})
            resolved = self.adapter.maybe_resolve(assistant_text)
            if resolved == assistant_text:
                turns.append(ExecutionTurn(assistant_text=assistant_text))
                return ExecutionConversationResult(
                    final_text=assistant_text,
                    stop_reason="assistant_completed",
                    used_execution=used_execution,
                    turns=turns,
                    messages=conversation,
                )

            used_execution = True
            turns.append(ExecutionTurn(assistant_text=assistant_text, exec_response=resolved))
            conversation.append({"role": self.response_role, "content": self.render_runtime_feedback(resolved)})

        final_text = conversation[-1]["content"] if conversation else ""
        return ExecutionConversationResult(
            final_text=final_text,
            stop_reason="max_round_trips_reached",
            used_execution=used_execution,
            turns=turns,
            messages=conversation,
        )
