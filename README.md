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
9. An online cache that is closer to long-trace decoding than a static lookup
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
- `src/llm_computer/transformer.py`: tiny transformer-style verification for the
  restricted control-flow subset.
- `src/llm_computer/__main__.py`: command-line entry point.
- `tests/test_executor.py`: regression tests for timeline retrieval and
  append-only execution.
- `tests/test_transformer.py`: regression tests for the transformer subset.
- `docs/benchmark-results.md`: measured results and article-alignment notes.
- `docs/transformer-alignment.md`: current transformer-alignment status and next
  steps.
- `docs/model-integration-plan.md`: open-source and closed-source integration
  plans.

## Quick start

```bash
# Requires WABT tools such as `wat2wasm` in PATH.
# Optional: `clang` in PATH for the C-to-WASM example.
PYTHONPATH=src python3 -m llm_computer
PYTHONPATH=src python3 -m unittest discover -s tests -v
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
  memory, and one compiled-C example.
