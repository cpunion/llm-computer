# Qwen3 Transformers Integration

Date: 2026-03-17

## Purpose

This document describes the first concrete open-source model integration that
uses the repository's service protocol.

The selected baseline is:

- model: `Qwen/Qwen3-8B`
- runtime: `Hugging Face Transformers`

## What is implemented

The repository now includes a `Transformers` integration scaffold in
`src/llm_computer/qwen_transformers.py`.

It provides:

- `TransformersChatRuntime`
  - loads `AutoTokenizer` and `AutoModelForCausalLM`
  - renders chat prompts through `apply_chat_template` when available
  - resolves a practical local device in `cuda -> mps -> cpu` order
  - performs one generation step
  - optionally performs deterministic request-boundary interception and stops as
    soon as `</exec_request>` is emitted
- `QwenExecutionOrchestrator`
  - adds execution-lane system instructions
  - detects `<exec_request>...</exec_request>` blocks
  - resolves them through the local execution sidecar
  - feeds the resulting `<exec_response>...</exec_response>` back into the next
    generation step

This is a real runtime integration in the sense that it can drive an actual
`Transformers` model through the repository's sidecar protocol.

## Validation status on 2026-03-17

What completed successfully:

- the `uv`-managed Python 3.12 environment was created successfully
- optional `transformers` dependencies installed successfully
- repository tests passed under `uv run`
- the Qwen runtime scaffold can be imported and invoked locally
- a full live execution round-trip completed successfully with
  `Qwen/Qwen2.5-0.5B-Instruct` on the same `Transformers + sidecar` path
- a second full live execution round-trip completed successfully with the same
  model while request-boundary interception was enabled

Observed successful open-source live run:

- model: `Qwen/Qwen2.5-0.5B-Instruct`
- device: `mps`
- mode: few-shot protocol example enabled
- task: compute `6 * 7`
- model first emitted:
  - `<exec_request>{"source_kind":"wat","source":"(module ... i32.const 6 i32.const 7 i32.mul)","mode":"auto","trace_limit":1}</exec_request>`
- runtime returned an `exec_response` with final result `[42]`
- model then replied with `42`
- final orchestrator summary:
  - `used_execution=true`
  - `turns=2`

Observed successful open-source live run with request-boundary interception:

- model: `Qwen/Qwen2.5-0.5B-Instruct`
- device: `mps`
- mode: few-shot protocol example enabled
- interception: `--intercept-request-boundary`
- task: compute `6 * 7`
- runtime summary:
  - `used_execution=true`
  - `intercepted_requests=1`
  - `turns=2`

What did not complete in this session:

- a full live generation run from a downloaded `Qwen/Qwen3-8B` checkpoint

Observed blocker:

- `Qwen/Qwen3-8B` began downloading successfully but the full checkpoint fetch
  did not finish within the session; the observed transfer reached roughly
  `12.5 / 16.4 GiB` before cancellation
- `Qwen/Qwen3-0.6B` was also attempted as a lighter fallback, but its
  `model.safetensors` transfer stalled early and did not complete either

Interpretation:

- the current blocker for the chosen baseline model is checkpoint delivery
  throughput, not the repository's orchestration logic
- the open-source runtime path itself is now validated end-to-end through a real
  cached Qwen-family model
- the first runtime-interception prototype is also validated end-to-end through
  the same real cached Qwen-family model
- the remaining open-source gap is specifically `Qwen3-8B` live validation, not
  the generic `Transformers + sidecar` integration

## What is not implemented yet

This is still not the article's end state.

It does not yet:

- modify Qwen's internal attention heads
- add an execution-only KV path inside the model runtime
- compile WASM semantics into model weights
- create a true in-model execution block

At this stage, the model remains a planner and language model, while the exact
execution lane remains external. The new interception mode is still a runtime
wrapper around the base model rather than a modified model architecture.

## Installation

Optional dependencies are declared in `pyproject.toml`:

```bash
uv sync --extra transformers
```

This currently installs:

- `transformers>=4.51.0`
- `torch>=2.2.0`
- `accelerate>=0.30.0`

## Example usage

```bash
uv run llm-computer-qwen \
  --model-id Qwen/Qwen2.5-0.5B-Instruct \
  --device mps \
  --few-shot-example \
  --intercept-request-boundary \
  --max-round-trips 2 \
  --system 'Protocol requirement: your first reply must be exactly one <exec_request>...</exec_request> block and nothing else. Inside the tags output one valid JSON object only. Use source_kind="wat", mode="auto", and source containing a complete WAT module. Do not answer directly. Do not use Python. After runtime feedback, reply with only the final integer.' \
  --prompt 'Compute 6 * 7 exactly.'
```

## Why this is the right first step

This integration is intentionally conservative:

- it keeps the sidecar protocol unchanged
- it allows direct comparison against the current semantic reference
- it avoids inference-engine surgery during the first model integration
- it makes the next migration target, `SGLang`, much cleaner

## Next steps

The next implementation sequence should be:

1. Complete one real local Qwen3 checkpoint download and rerun the scaffold.
2. Replace the current request-boundary wrapper with a deeper runtime
   interception path inside the inference engine.
3. Add execution-segment handling that is separate from ordinary conversation
   tokens.
4. Prototype the same contract in `SGLang`.
5. Only then move toward execution heads or a true embedded execution block.

## Sources

- Qwen3 official repository: https://github.com/QwenLM/Qwen3
- Hugging Face Qwen3 docs: https://huggingface.co/docs/transformers/model_doc/qwen3
- Hugging Face custom model docs: https://huggingface.co/docs/transformers/en/custom_models
