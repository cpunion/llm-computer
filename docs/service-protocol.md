# Service Protocol

Date: 2026-03-17

## Purpose

This document defines the stable execution protocol shared by:

- the local sidecar service,
- open-source runtime adapters,
- closed-source tool integrations.

The goal is to keep the execution contract fixed while the backend evolves from
an external sidecar toward tighter transformer integration.

## Request schema

The service accepts an `ExecutionRequest` JSON object with these fields:

- `source_kind`: one of `wat`, `c`, or `wasm_base64`
- `source`: the source payload
- `export_name`: function export to execute
- `mode`: one of `auto`, `reference`, `append_only_naive`,
  `append_only_hull`, `transformer_naive`, `transformer_hull`
- `max_steps`: safety bound for execution length
- `trace_limit`: number of trace entries returned in the preview
- `c_opt_level`: `clang` optimization flag when `source_kind=c`

`auto` currently resolves as:

- `transformer_hull` when the function is inside the transformer verification
  subset
- `append_only_hull` otherwise

## Response schema

The service returns an `ExecutionResponse` JSON object with:

- `ok`: whether execution succeeded
- `mode_requested`: requested backend
- `mode_used`: resolved backend
- `source_kind`: echoed request source kind
- `export_name`: executed export
- `results`: final result values
- `steps`: executed trace length
- `elapsed_s`: wall-clock runtime
- `tokens_per_s`: trace steps per second
- `transformer_subset`: whether the target function is inside the transformer
  subset
- `trace_preview`: truncated execution trace
- `notes`: backend-resolution notes
- `error`: error string when `ok=false`

## Open-source runtime form

The prototype open-source adapter uses tagged spans:

```text
<exec_request>{"source_kind":"wat", ...}</exec_request>
<exec_response>{"ok":true, ...}</exec_response>
```

This keeps the execution lane orthogonal to the model's normal text stream.

## Closed-source tool form

The prototype closed-source adapter exposes the same request schema as a tool
definition:

- tool name: `run_llm_computer`
- parameters: `ExecutionRequest.json_schema()`

That allows hosted models to stay in a planner role while exact execution
remains in the sidecar.
