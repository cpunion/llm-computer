# LLM Computer

Fresh reimplementation inspired by Percepta's article
"Can LLMs Be Computers?".

## Goal

This repository focuses on the parts of the article that are concrete enough to
reproduce from the public write-up:

1. A real WebAssembly binary frontend compiled from WAT example programs.
2. A parsed WASM instruction trace that fits into an autoregressive execution
   trace.
3. Two-dimensional attention-style retrieval implemented as convex-hull support
   point queries.
4. An append-only executor that recovers instruction pointer, locals, and stack
   values from time-indexed retrieval rather than mutable runtime state.
5. Sparse linear memory recovered from append-only writes to byte-addressed
   timelines.
6. Stack depth recovered from append-only per-step deltas via cumulative sums.
7. A minimal C-to-WASM frontend for the subset that the current parser and
   executor support.
8. A tiny transformer-style verifier with static code heads and dynamic state
   heads over append-only traces.
9. A stable sidecar protocol shared by open-source and closed-source adapter
   prototypes.
10. A Qwen3 plus Transformers integration scaffold over the stable sidecar
    protocol.
11. An online cache that is closer to long-trace decoding than a static lookup
    benchmark.

## Non-goals

This repository does **not** claim to fully reproduce the original article:

- It is not a trained transformer model.
- It is only a restricted WebAssembly subset with `local.*`, control flow,
  `i32` arithmetic, comparisons, `if`, `i32.load` / `i32.store`, and simple
  data segments.
- It does not compile arbitrary C code into weights.
- It does not reproduce the article's published throughput numbers.

## Repository layout

- `src/llm_computer/wasm.py`: WAT compilation, WASM parsing, and reference
  execution, plus a minimal `clang -> wasm32` compilation path.
- `src/llm_computer/hull.py`: static and online 2D hull caches.
- `src/llm_computer/examples.py`: small WAT programs compiled to WASM modules.
- `src/llm_computer/executor.py`: append-only WASM executor, stack/local/memory
  timelines, and benchmarks.
- `src/llm_computer/protocol.py`: stable request/response schema for sidecar use.
- `src/llm_computer/gemini_integration.py`: Gemini closed-source integration
  over the tool-style sidecar protocol.
- `src/llm_computer/qwen_transformers.py`: Qwen3 plus Transformers integration
  scaffold over the service protocol.
- `src/llm_computer/gemini_cli.py`: `uv run` entry point for Gemini validation.
- `src/llm_computer/qwen_cli.py`: `uv run` entry point for Qwen3 validation.
- `src/llm_computer/service.py`: execution service boundary over the available
  backends.
- `src/llm_computer/transformer.py`: tiny transformer-style verification for the
  restricted control-flow subset.
- `src/llm_computer/integration.py`: open-source and closed-source adapter
  prototypes over the service API.
- `src/llm_computer/__main__.py`: command-line entry point.
- `tests/test_executor.py`: regression tests for timeline retrieval and
  append-only execution.
- `tests/test_service.py`: protocol and service routing tests.
- `tests/test_gemini_integration.py`: regression tests for the Gemini closed-source
  integration.
- `tests/test_integration.py`: adapter tests for open-source and closed-source
  prototypes.
- `tests/test_qwen_transformers.py`: regression tests for the Qwen3
  Transformers orchestration scaffold.
- `tests/test_transformer.py`: regression tests for the transformer subset.
- `docs/benchmark-results.md`: measured results and article-alignment notes.
- `docs/open-source-selection.md`: chosen open-source model and runtime
  baseline.
- `docs/gemini-integration.md`: current Gemini integration status and usage.
- `docs/qwen-transformers-integration.md`: current Qwen3 plus Transformers
  integration status and next steps.
- `docs/runtime-validation.md`: `uv` environment and validated runtime commands.
- `docs/service-protocol.md`: stable execution contract for sidecars and tools.
- `docs/transformer-alignment.md`: current transformer-alignment status and next
  steps.
- `docs/model-integration-plan.md`: open-source and closed-source integration
  plans.

## Quick start

```bash
# Requires WABT tools such as `wat2wasm` in PATH.
# Optional: `clang` in PATH for the C-to-WASM example.
uv sync --python 3.12 --extra transformers --extra gemini
uv run llm-computer
uv run python -m unittest discover -s tests -v
```

## Current status

The implementation is intentionally explicit about what it does and does not
cover. The benchmark output separates:

- static support-point query speed,
- online append-only query+insert speed,
- append-only WASM execution driven by trace retrieval,
- transformer-style verification over the restricted subset.

The current example set includes:

- WAT modules that exercise locals, loops, and memory,
- a memory-backed program,
- a compiled C example that goes through `clang -> wasm32 -> parser -> append-only executor`,
- a transformer-style verification path that now covers locals, control flow,
  memory, and one compiled-C example,
- a sidecar service plus adapter prototypes that keep the execution contract
  stable across open-source and closed-source integration paths,
- a Qwen3 plus Transformers scaffold that turns the stable sidecar contract
  into a real open-source model integration loop,
- a Gemini closed-source integration that exercises the same sidecar contract
  through explicit tool calls.

Current live-validation status:

- Gemini has been validated end-to-end through a real tool call
- Qwen local runtime validation is implemented but the actual checkpoint fetch
  did not complete within the validation session
