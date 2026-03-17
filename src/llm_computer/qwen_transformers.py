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
    intercept_request_boundary: bool = False


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
    intercepted_requests: int = 0
    structured_captures: int = 0
    turns: list[ExecutionTurn] = field(default_factory=list)
    messages: list[dict[str, str]] = field(default_factory=list)


class ChatRuntime(Protocol):
    """Minimal runtime surface needed by the execution loop."""

    def generate(self, messages: list[dict[str, str]], settings: GenerationSettings) -> str:
        ...


class InterceptingChatRuntime(ChatRuntime, Protocol):
    """Runtime surface for request-boundary interception."""

    def generate_until_request_boundary(
        self,
        messages: list[dict[str, str]],
        settings: GenerationSettings,
    ) -> tuple[str, bool]:
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

        generation_config = getattr(self.model, "generation_config", None)
        restore_fields: list[tuple[str, Any]] = []
        if generation_config is not None and not settings.do_sample:
            for field_name in ("temperature", "top_p", "top_k"):
                if hasattr(generation_config, field_name):
                    restore_fields.append((field_name, getattr(generation_config, field_name)))
                    setattr(generation_config, field_name, None)

        try:
            generated_ids = self.model.generate(**model_inputs, **generate_kwargs)
        finally:
            for field_name, value in restore_fields:
                setattr(generation_config, field_name, value)
        input_ids = model_inputs["input_ids"]
        output_ids = generated_ids[0][len(input_ids[0]) :]
        return self.tokenizer.decode(output_ids, skip_special_tokens=True)

    def generate_until_request_boundary(
        self,
        messages: list[dict[str, str]],
        settings: GenerationSettings,
    ) -> tuple[str, bool]:
        torch, _, _ = _require_transformers()
        if settings.do_sample:
            raise RuntimeError("Request-boundary interception currently supports only deterministic generation")

        prompt = self.render_prompt(messages, settings)
        model_inputs = self.tokenizer([prompt], return_tensors="pt")
        if hasattr(model_inputs, "to"):
            model_inputs = model_inputs.to(self.device)

        input_ids = model_inputs["input_ids"]
        attention_mask = model_inputs.get("attention_mask")
        current_input_ids = input_ids
        current_attention_mask = attention_mask
        generated_token_ids: list[int] = []
        past_key_values = None
        request_end_tag = f"</{OpenSourceRuntimeAdapter.REQUEST_TAG}>"

        eos_ids: set[int] = set()
        tokenizer_eos = getattr(self.tokenizer, "eos_token_id", None)
        if isinstance(tokenizer_eos, int):
            eos_ids.add(tokenizer_eos)
        generation_config = getattr(self.model, "generation_config", None)
        config_eos = getattr(generation_config, "eos_token_id", None)
        if isinstance(config_eos, int):
            eos_ids.add(config_eos)
        elif isinstance(config_eos, list):
            eos_ids.update(token_id for token_id in config_eos if isinstance(token_id, int))

        with torch.no_grad():
            for _ in range(settings.max_new_tokens):
                outputs = self.model(
                    input_ids=current_input_ids,
                    attention_mask=current_attention_mask,
                    use_cache=True,
                    past_key_values=past_key_values,
                )
                next_token_id = int(outputs.logits[:, -1, :].argmax(dim=-1).item())
                generated_token_ids.append(next_token_id)
                past_key_values = outputs.past_key_values

                text = self.tokenizer.decode(generated_token_ids, skip_special_tokens=True)
                canonical_request = OpenSourceRuntimeAdapter.try_extract_request_segment(text)
                if canonical_request is not None:
                    end_index = text.find(request_end_tag)
                    if end_index >= 0:
                        return text[: end_index + len(request_end_tag)], False
                    return canonical_request, True
                if next_token_id in eos_ids:
                    return text, False

                current_input_ids = torch.tensor([[next_token_id]], device=input_ids.device, dtype=input_ids.dtype)
                if current_attention_mask is not None:
                    current_attention_mask = torch.cat(
                        [current_attention_mask, current_attention_mask.new_ones((1, 1))],
                        dim=-1,
                    )

        return self.tokenizer.decode(generated_token_ids, skip_special_tokens=True), False


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
    def execution_protocol_example(cls) -> list[dict[str, str]]:
        request = (
            '<exec_request>{"source_kind":"wat","source":"(module (func (export \\"main\\") '
            '(result i32) i32.const 2 i32.const 3 i32.mul))","mode":"auto","trace_limit":1}</exec_request>'
        )
        response = (
            '<exec_response>{"ok":true,"mode_requested":"auto","mode_used":"transformer_hull",'
            '"source_kind":"wat","export_name":"main","results":[6],"steps":4,"elapsed_s":0.001,'
            '"tokens_per_s":4000.0,"transformer_subset":true,"trace_preview":[],"notes":[],"error":null}'
            "</exec_response>"
        )
        return [
            {"role": "user", "content": "Compute 2 * 3 exactly."},
            {"role": "assistant", "content": request},
            {"role": "user", "content": cls(runtime=DummyChatRuntime()).render_runtime_feedback(response)},
            {"role": "assistant", "content": "6"},
        ]

    @classmethod
    def prepare_messages(
        cls,
        user_prompt: str,
        *,
        system_prompt: str | None = None,
        history: list[dict[str, str]] | None = None,
        include_protocol_example: bool = False,
    ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        combined = cls.combined_system_prompt(system_prompt)
        if combined:
            messages.append({"role": "system", "content": combined})
        if include_protocol_example:
            messages.extend(cls.execution_protocol_example())
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

    def render_runtime_error(self, error: str) -> str:
        return (
            "Runtime parsing error:\n"
            f"{error}\n\n"
            "If exact execution is still needed, emit one corrected <exec_request>...</exec_request> block "
            "containing only a valid JSON object. Otherwise answer directly."
        )

    @staticmethod
    def _runtime_supports_request_interception(runtime: ChatRuntime) -> bool:
        return hasattr(runtime, "generate_until_request_boundary")

    def _generate_assistant_text(
        self,
        conversation: list[dict[str, str]],
        settings: GenerationSettings,
        *,
        prefer_interception: bool,
    ) -> tuple[str, bool, bool]:
        if prefer_interception and settings.intercept_request_boundary and self._runtime_supports_request_interception(self.runtime):
            runtime = self.runtime
            assistant_text, structured_capture = runtime.generate_until_request_boundary(conversation, settings)  # type: ignore[attr-defined]
            return assistant_text, self.adapter.contains_request(assistant_text), structured_capture
        return self.runtime.generate(conversation, settings), False, False

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
        intercepted_requests = 0
        structured_captures = 0

        for _ in range(max_round_trips):
            assistant_text, intercepted_request, structured_capture = self._generate_assistant_text(
                conversation,
                settings,
                prefer_interception=not used_execution,
            )
            if intercepted_request:
                intercepted_requests += 1
            if structured_capture:
                structured_captures += 1
            conversation.append({"role": "assistant", "content": assistant_text})
            try:
                resolved = self.adapter.maybe_resolve(assistant_text)
            except Exception as exc:
                if not self.adapter.contains_request_marker(assistant_text):
                    turns.append(ExecutionTurn(assistant_text=assistant_text))
                    return ExecutionConversationResult(
                        final_text=assistant_text,
                        stop_reason="assistant_completed",
                        used_execution=used_execution,
                        intercepted_requests=intercepted_requests,
                        structured_captures=structured_captures,
                        turns=turns,
                        messages=conversation,
                    )
                turns.append(ExecutionTurn(assistant_text=assistant_text))
                conversation.append({"role": self.response_role, "content": self.render_runtime_error(str(exc))})
                continue
            if resolved == assistant_text:
                turns.append(ExecutionTurn(assistant_text=assistant_text))
                return ExecutionConversationResult(
                    final_text=assistant_text,
                    stop_reason="assistant_completed",
                    used_execution=used_execution,
                    intercepted_requests=intercepted_requests,
                    structured_captures=structured_captures,
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
            intercepted_requests=intercepted_requests,
            structured_captures=structured_captures,
            turns=turns,
            messages=conversation,
        )


class DummyChatRuntime:
    """Placeholder runtime for class-level prompt helpers."""

    def generate(self, messages: list[dict[str, str]], settings: GenerationSettings) -> str:
        raise NotImplementedError
