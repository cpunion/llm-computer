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

What did not complete in this session:

- a full live generation run from a downloaded Qwen checkpoint

Observed blocker:

- `Qwen/Qwen3-8B` began downloading successfully but the full checkpoint fetch
  did not finish within the session; the observed transfer reached roughly
  `12.5 / 16.4 GiB` before cancellation
- `Qwen/Qwen3-0.6B` was also attempted as a lighter fallback, but its
  `model.safetensors` transfer stalled early and did not complete either

Interpretation:

- the current blocker is checkpoint delivery throughput, not the repository's
  orchestration logic
- the open-source runtime path is implemented and testable, but this session
  does not yet claim a completed end-to-end Qwen generation trace

## What is not implemented yet

This is still not the article's end state.

It does not yet:

- modify Qwen's internal attention heads
- add an execution-only KV path inside the model runtime
- compile WASM semantics into model weights
- create a true in-model execution block

At this stage, the model remains a planner and language model, while the exact
execution lane remains external.

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
  --model-id Qwen/Qwen3-8B \
  --device mps \
  --max-round-trips 2 \
  --system 'You are a precise engineering assistant. For exact computation, first emit only one <exec_request>...</exec_request> block. After runtime feedback, answer with the final integer only.' \
  --prompt 'Compute 6 * 7 exactly. Use execution mode and do not do mental arithmetic.'
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
2. Replace the text-level request interception with runtime-level interception.
3. Add execution-segment handling that is separate from ordinary conversation
   tokens.
4. Prototype the same contract in `SGLang`.
5. Only then move toward execution heads or a true embedded execution block.

## Sources

- Qwen3 official repository: https://github.com/QwenLM/Qwen3
- Hugging Face Qwen3 docs: https://huggingface.co/docs/transformers/model_doc/qwen3
- Hugging Face custom model docs: https://huggingface.co/docs/transformers/en/custom_models
