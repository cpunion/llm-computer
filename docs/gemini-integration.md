# Gemini Integration

Date: 2026-03-17

## Purpose

This document describes the closed-source validation path built around Gemini
and the repository's tool-style sidecar contract.

The validated closed-source target is:

- provider: Google Gemini
- model: `gemini-3-flash-preview`
- integration style: structured function call plus manual tool-response loop

## What is implemented

The repository now includes:

- `src/llm_computer/gemini_integration.py`
- `src/llm_computer/gemini_cli.py`

The implementation:

- loads `GEMINI_API_KEY` from `.env`
- publishes the sidecar through the same `run_llm_computer` schema used by the
  generic closed-source adapter
- sends a strict Gemini `FunctionDeclaration` derived from that schema
- handles Gemini function calls manually and returns tool responses back into
  the model conversation

This keeps the contract aligned with the repository's service layer instead of
creating a Gemini-only protocol.

## Why manual tool handling is used

Gemini can return `function_call` parts without completing the local function
execution loop on its own. The current implementation therefore handles the
loop explicitly:

1. send the prompt with the sidecar tool declaration
2. inspect `response.function_calls`
3. execute the tool through `ClosedSourceToolAdapter`
4. send a `function_response` part back to Gemini
5. collect the final natural-language answer

This makes the execution step explicit and auditable.

## Installation

```bash
uv sync --extra gemini
```

This currently installs:

- `google-genai`
- `python-dotenv`

## Example usage

```bash
uv run llm-computer-gemini \
  --model gemini-3-flash-preview \
  --force-tool-use \
  --prompt 'Execute this WAT module with the execution tool and return only the final integer: (module (func (export "main") (result i32) i32.const 6 i32.const 7 i32.mul))'
```

The `--force-tool-use` flag is the current stable validation path. Without it,
Gemini may answer simple requests directly and skip the sidecar.

## Current limitations

This integration still does not make Gemini an internal execution model.

It remains:

- a planner-plus-sidecar architecture
- dependent on tool calling rather than internal model state updates
- external to the model's own hidden state and KV cache

That limitation is fundamental for closed-source APIs and matches the design
described in `docs/model-integration-plan.md`.
