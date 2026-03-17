"""Service boundary for executing WASM programs through a stable protocol."""

from __future__ import annotations

from base64 import b64decode
from dataclasses import replace
from time import perf_counter

from llm_computer.executor import AppendOnlyWasmExecutor, HullTimeline, NaiveTimeline
from llm_computer.protocol import ExecutionMode, ExecutionRequest, ExecutionResponse, SourceKind, TracePreviewEntry
from llm_computer.transformer import TinyExecutionTransformer, supports_transformer_verification
from llm_computer.wasm import ExecutionResult, ReferenceWasmExecutor, WasmFunction, compile_c_module, compile_wat_module, parse_module


class ExecutionService:
    """Routes structured execution requests to the available backends."""

    def _load_function(self, request: ExecutionRequest) -> WasmFunction:
        if request.source_kind == SourceKind.WAT:
            module = compile_wat_module(request.source)
        elif request.source_kind == SourceKind.C:
            module = compile_c_module(request.source, export_name=request.export_name, opt_level=request.c_opt_level)
        elif request.source_kind == SourceKind.WASM_BASE64:
            module = parse_module(b64decode(request.source.encode("ascii")))
        else:
            raise ValueError(f"Unsupported source kind: {request.source_kind}")
        return module.exported_function(request.export_name)

    def _resolve_mode(self, request: ExecutionRequest, function: WasmFunction) -> tuple[ExecutionMode, list[str], bool]:
        transformer_subset = supports_transformer_verification(function)
        notes: list[str] = []

        if request.mode == ExecutionMode.AUTO:
            if transformer_subset:
                notes.append("auto-selected transformer_hull because the function is inside the transformer subset")
                return ExecutionMode.TRANSFORMER_HULL, notes, transformer_subset
            notes.append("auto-fell back to append_only_hull because the function is outside the transformer subset")
            return ExecutionMode.APPEND_ONLY_HULL, notes, transformer_subset

        if request.mode in {ExecutionMode.TRANSFORMER_HULL, ExecutionMode.TRANSFORMER_NAIVE} and not transformer_subset:
            raise ValueError("Function is outside the transformer verification subset")

        return request.mode, notes, transformer_subset

    def _run_backend(self, function: WasmFunction, mode: ExecutionMode, max_steps: int) -> ExecutionResult:
        if mode == ExecutionMode.REFERENCE:
            return ReferenceWasmExecutor(function).run(max_steps=max_steps)
        if mode == ExecutionMode.APPEND_ONLY_NAIVE:
            return AppendOnlyWasmExecutor(function, NaiveTimeline).run(max_steps=max_steps)
        if mode == ExecutionMode.APPEND_ONLY_HULL:
            return AppendOnlyWasmExecutor(function, HullTimeline).run(max_steps=max_steps)
        if mode == ExecutionMode.TRANSFORMER_NAIVE:
            return TinyExecutionTransformer(function, NaiveTimeline).run(max_steps=max_steps)
        if mode == ExecutionMode.TRANSFORMER_HULL:
            return TinyExecutionTransformer(function, HullTimeline).run(max_steps=max_steps)
        raise ValueError(f"Unsupported execution mode: {mode}")

    def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        try:
            function = self._load_function(request)
            resolved_mode, notes, transformer_subset = self._resolve_mode(request, function)
            start = perf_counter()
            result = self._run_backend(function, resolved_mode, request.max_steps)
            elapsed = perf_counter() - start
            trace_preview = [
                TracePreviewEntry(
                    step=entry.step,
                    ip=entry.ip,
                    instruction=entry.instruction,
                    value=entry.value,
                    stack_delta=entry.stack_delta,
                    stack_size=entry.stack_size,
                    branch_taken=entry.branch_taken,
                )
                for entry in result.trace[: request.trace_limit]
            ]
            steps = len(result.trace)
            return ExecutionResponse(
                ok=True,
                mode_requested=request.mode,
                mode_used=resolved_mode,
                source_kind=request.source_kind,
                export_name=request.export_name,
                results=result.results,
                steps=steps,
                elapsed_s=elapsed,
                tokens_per_s=(steps / elapsed) if elapsed > 0 else float("inf"),
                transformer_subset=transformer_subset,
                trace_preview=trace_preview,
                notes=notes,
            )
        except Exception as exc:  # pragma: no cover - exercised by service tests
            return ExecutionResponse(
                ok=False,
                mode_requested=request.mode,
                mode_used=request.mode,
                source_kind=request.source_kind,
                export_name=request.export_name,
                transformer_subset=False,
                error=str(exc),
            )


class PinnedExecutionBackend:
    """Execution backend that forces all requests through one protocol mode."""

    def __init__(
        self,
        mode: ExecutionMode,
        *,
        service: ExecutionService | None = None,
    ) -> None:
        self.mode = mode
        self.service = service or ExecutionService()

    def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        return self.service.execute(replace(request, mode=self.mode))
