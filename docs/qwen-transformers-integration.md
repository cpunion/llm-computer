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
  - performs one generation step
- `QwenExecutionOrchestrator`
  - adds execution-lane system instructions
  - detects `<exec_request>...</exec_request>` blocks
  - resolves them through the local execution sidecar
  - feeds the resulting `<exec_response>...</exec_response>` back into the next
    generation step

This is a real runtime integration in the sense that it can drive an actual
`Transformers` model through the repository's sidecar protocol.

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
pip install -e .[transformers]
```

This currently installs:

- `transformers>=4.51.0`
- `torch>=2.2.0`
- `accelerate>=0.30.0`

## Example usage

```python
from llm_computer.qwen_transformers import QwenExecutionOrchestrator

orchestrator = QwenExecutionOrchestrator.from_pretrained("Qwen/Qwen3-8B")
messages = QwenExecutionOrchestrator.prepare_messages(
    "Compute 6 * 7 exactly using execution mode if needed.",
    system_prompt="You are a precise engineering assistant.",
)
result = orchestrator.run(messages)
print(result.final_text)
```

## Why this is the right first step

This integration is intentionally conservative:

- it keeps the sidecar protocol unchanged
- it allows direct comparison against the current semantic reference
- it avoids inference-engine surgery during the first model integration
- it makes the next migration target, `SGLang`, much cleaner

## Next steps

The next implementation sequence should be:

1. Run the scaffold against a real local Qwen3 checkpoint.
2. Replace the text-level request interception with runtime-level interception.
3. Add execution-segment handling that is separate from ordinary conversation
   tokens.
4. Prototype the same contract in `SGLang`.
5. Only then move toward execution heads or a true embedded execution block.

## Sources

- Qwen3 official repository: https://github.com/QwenLM/Qwen3
- Hugging Face Qwen3 docs: https://huggingface.co/docs/transformers/model_doc/qwen3
- Hugging Face custom model docs: https://huggingface.co/docs/transformers/en/custom_models
