# Model Integration Plan

Date: 2026-03-17

## Objective

This document describes how the repository's execution architecture can be
integrated with open-source transformer models and with closed-source LLM APIs.

The guiding principle is:

- keep the current WASM frontend and trace representation stable,
- isolate the execution lane from the general language lane,
- minimize model changes at first,
- only move into true in-model execution after the sidecar and runtime paths are
  validated.

## Common architecture

Both open-source and closed-source paths should share the same execution
contract:

1. A program is compiled to WASM or to a restricted execution subset.
2. The program is represented as a static tokenized code trace.
3. Runtime state is represented as append-only execution writes.
4. A planner decides when to enter execution mode.
5. The execution lane returns structured state updates and final values.

This keeps the interface stable even if the backend changes from a sidecar to a
runtime-integrated transformer.

## Open-source model path

### Phase 0: Sidecar execution

Goal:

- keep the base model unchanged,
- use the current repository as an external execution service.

Implementation:

- the model emits an execution request,
- the runtime sends WASM plus inputs to the sidecar,
- the sidecar returns structured trace summaries and final outputs.

Advantages:

- lowest engineering risk,
- works immediately,
- validates the planner/executor protocol before model surgery.

### Phase 1: Runtime-attached execution heads

Goal:

- keep the language model mostly frozen,
- add a narrow execution lane at inference time.

Implementation:

- reserve execution tokens or an execution segment,
- add a small number of dedicated execution heads,
- route execution-mode attention to custom caches,
- keep the rest of the model unchanged.

Expected changes:

- inference engine changes,
- KV-cache specialization for execution heads,
- adapter or LoRA-style modifications if needed.

### Phase 2: Tiny in-model executor block

Goal:

- move from a sidecar protocol to a true embedded execution block.

Implementation:

- add a compact transformer block specialized for execution mode,
- keep it separate from the general language backbone,
- feed it static code tokens and append-only state tokens,
- use the current tiny transformer verifier as the semantic reference.

### Phase 3: Broader WASM coverage

Goal:

- accept realistic compiled programs without manual filtering.

Implementation:

- support more comparisons and control flow,
- support memory in the transformer lane,
- support selected compiled C patterns produced by `clang`.

## Closed-source model path

### Phase 0: Tool-style sidecar

Goal:

- integrate without weight access.

Implementation:

- expose the executor as a tool or service,
- send code, execution mode, and input bindings,
- return final results plus optionally a compressed execution trace.

This is the only realistic starting point for closed-source models because the
runtime internals are not accessible.

### Phase 1: Structured execution protocol

Goal:

- reduce prompt fragility and make execution handoffs deterministic.

Implementation:

- define a strict JSON schema for execution requests,
- define trace summaries and error classes,
- require the model to emit only structured execution commands in execution mode.

### Phase 2: Planner/executor split

Goal:

- use the closed-source model only for planning and language tasks,
- keep exact execution outside the model.

Implementation:

- planner model writes or selects code,
- sidecar runs the execution lane,
- planner model reads back compact state summaries.

This preserves most of the value while avoiding impossible runtime integration
requirements.

## Cost and risk comparison

Open-source path:

- higher engineering cost,
- better fidelity to the article,
- possible runtime and kernel changes,
- best path to true in-model execution.

Closed-source path:

- much lower engineering cost,
- immediate product usefulness,
- cannot become a true internal execution layer,
- remains a planner-plus-sidecar architecture.

## Recommended order

1. Keep improving the repository until the transformer-style path covers memory
   and one compiled-C example.
2. Build the sidecar API and execution protocol.
3. Integrate the sidecar with at least one open-source model and one
   closed-source model.
4. Add runtime-attached execution heads for an open-source model.
5. Only then attempt a true tiny in-model executor block.

## Immediate implementation tasks

The immediate engineering sequence should be:

1. Replace the current hand-coded transition block with a more explicit tiny
   transformer block abstraction.
2. Define a stable execution request/response schema.
3. Wrap the current executor as a service boundary.
4. Prototype one open-source runtime integration against the same schema.
5. Expand the transformer subset toward more compiled-C patterns.
