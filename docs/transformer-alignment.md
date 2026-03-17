# Transformer Alignment

Date: 2026-03-17

## Purpose

This document explains what the repository currently aligns with from the
Percepta article, what remains outside the current scope, and how the new tiny
transformer-style verifier should be interpreted.

## Current transformer-aligned components

The repository now has two execution paths:

1. A general append-only executor in `src/llm_computer/executor.py`.
2. A restricted tiny transformer-style verifier in
   `src/llm_computer/transformer.py`.

The tiny transformer verifier is intentionally narrower, but structurally closer
to the article:

- static code heads retrieve instruction fields by instruction pointer,
- dynamic state heads retrieve the latest writes for `ip`, locals, and stack
  slots from append-only traces,
- stack depth is reconstructed from append-only deltas,
- an explicit tiny execution block now splits execution into:
  - feature extraction from recovered state
  - a transition layer that maps features onto the next-state signal
  - an append-only writeback layer that emits the next writes

This verifier currently supports:

- `block`
- `loop`
- `end`
- `i32.const`
- `local.get`
- `local.set`
- `local.tee`
- `i32.load`
- `i32.store`
- `i32.lt_s`
- `i32.gt_s`
- `i32.le_s`
- `i32.add`
- `i32.sub`
- `i32.mul`
- `i32.eqz`
- `if`
- `else`
- `br`
- `br_if`

## What this verifies

The verifier demonstrates that a restricted execution subset can be expressed as
an attention-style state recovery system rather than as ordinary mutable machine
state.

More concretely, it verifies:

- the instruction stream can be read through static heads,
- the machine state can be reconstructed from append-only writes,
- the control-flow subset used by the factorial and triangular-sum programs can
  be executed without falling back to the general executor,
- byte-addressed linear memory can be recovered inside the transformer-style
  path,
- a real `clang -> wasm32` compiled example can be executed inside the
  transformer-style path,
- hull-backed dynamic retrieval improves longer traces in this transformer-like
  path as well.

## What it does not yet verify

This is still not the full article system.

The current verifier does not yet cover:

- arbitrary WASM subsets,
- weight compilation into a real transformer runtime,
- learned or compiled `Q/K/V` weights,
- integration with an actual LLM forward pass.

## Why the restricted subset is still useful

The restricted subset is enough to make the core architectural point:

- the repository is no longer only a Python dispatcher over append-only state,
- there is now a separate execution path that is explicitly organized as
  instruction heads plus state heads plus an execution block,
- correctness can be checked against the same reference WASM executor.

The repository now also exposes this transformer-aligned path through a stable
service boundary, so the same subset can be exercised by open-source and
closed-source adapter prototypes without changing the backend contract.

The latest alignment step is important because it moves the repository away
from a single Python opcode dispatcher and closer to the article's intended
shape:

- the transition logic is still deterministic Python, but it is no longer mixed
  with state retrieval and writeback plumbing,
- the execution path now has explicit stage boundaries that can later be mapped
  onto learned or compiled transformer components,
- unit tests can validate the execution stages independently of the end-to-end
  trace replay.

## Next alignment milestones

The next milestones, in order, are:

1. Separate static-code retrieval from dynamic-state retrieval at the runtime
   level so that open-source model integration can target them independently.
2. Expand the transformer subset toward a broader class of compiled C examples.
3. Replace the static-code linear scan heads with a more faithful geometric or
   compiled retrieval mechanism.
4. Move from the current service boundary into one real open-weight runtime.
5. Replace the fixed execution block with compiled transformer weights or a
   closer attention-only construction.
