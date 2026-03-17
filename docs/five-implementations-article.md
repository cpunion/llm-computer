# Five Ways We Tried to Execute Programs with LLMs

![Animated overview](assets/five-implementation-overview.gif)

## Original Reference

This project article is a validation and implementation report inspired by Percepta's original post: [Can LLMs Be Computers?](https://www.percepta.ai/blog/can-llms-be-computers).

- Original title: *Can LLMs Be Computers?*
- Original subtitle: Executing programs inside transformers with exponentially faster inference
- Published by: Christos Tzamos together with others at Percepta
- Published on: Mar 11, 2026
- Original link: https://www.percepta.ai/blog/can-llms-be-computers

## TL;DR

We now have five working execution paths in one repository, ordered from the shallowest semantic baseline to the deepest current open-weight integration. The point of the ladder is not that every deeper layer is already faster. The point is that each layer moves the execution boundary closer to the model while preserving a single underlying execution contract.

The live comparison was recorded on `Qwen/Qwen2.5-0.5B-Instruct` for the open-source path, `gemini-3-flash-preview` for the closed-source path, and `mps` as the device. All five methods returned the same final value `42` on the canonical WASM scenario.

![Implementation ladder](assets/five-implementation-ladder.png)

## Why This Ladder Matters

Most discussions about tool use versus in-model execution collapse too many design choices into one question. In practice there are several distinct integration layers:

1. A semantic baseline that defines correct execution.
2. A mechanism baseline that already uses append-only state recovery.
3. A hosted-model path that can only call out to a sidecar.
4. An open-weight wrapper that intercepts structured requests inside the local runtime.
5. A native open-source execution block that removes the text round-trip and starts to resemble an embedded executor.

The important result is that the repository now exercises all five layers with the same service contract and the same published article examples.

![Execution boundaries](assets/five-implementation-paths.png)

## The Five Implementations

### 1. Reference Direct

This is the cleanest semantic baseline: parse WASM, execute it with ordinary mutable state, and return the result without any model orchestration.

**Execution boundary.** The service calls the reference WASM executor directly.

**Canonical 6 × 7 run.** `30.85 ms` end-to-end, final value `42`.

**Implementation notes**

- Uses `ReferenceWasmExecutor` as the canonical semantics oracle.
- Bypasses prompt protocols, wrappers, and tool calls entirely.
- Defines the trace shape that every deeper implementation must preserve.

**Testing status**

- Passed the five-way comparison scenario with final value `42`.
- Validated Hungarian end-to-end with result `206`.
- Validated the full article Sudoku checksum `1276684605` in `22,370,167` steps.

### 2. Append-Only Naive Direct

This is the first mechanism-faithful executor: state is reconstructed from append-only writes, but retrieval still scans the whole history instead of using a hull-backed fast path.

**Execution boundary.** The service calls the append-only executor with a naive timeline scan.

**Canonical 6 × 7 run.** `17.52 ms` end-to-end, final value `42`.

**Implementation notes**

- Replaces mutable locals and stack with append-only state timelines.
- Uses the same request/response boundary as other direct backends.
- Serves as the control for whether the hull trick actually matters.

**Testing status**

- Passed the five-way comparison scenario with final value `42`.
- Validated Hungarian end-to-end with result `206`.
- Matched the reference Sudoku prefix state through `10,000` steps.

### 3. Closed-Source Sidecar

This is the best available path for closed-weight APIs: the model remains a planner, while the execution contract is enforced through a strict tool schema and the shared sidecar service.

**Execution boundary.** Gemini plans; the sidecar executes; Gemini narrates the final answer.

**Canonical 6 × 7 run.** `4.115 s` end-to-end, final value `42`.

**Implementation notes**

- Uses `gemini-3-flash-preview` with forced tool use.
- Keeps the execution backend identical to the open-source path.
- Cannot move execution inside model weights because runtime internals are unavailable.

**Testing status**

- Passed the five-way comparison scenario with final value `42`.
- Recorded `tool_calls=1` in live validation.
- Backed by dedicated Gemini integration tests plus the stage-3 and stage-10 validations.

### 4. Open-Source Wrapper

This path keeps execution outside the model block graph, but it moves orchestration inside the open runtime: request extraction, structured capture, and response injection are all handled locally.

**Execution boundary.** Qwen emits a structured execution request; the runtime resolves it and feeds back a response span.

**Canonical 6 × 7 run.** `1.178 s` end-to-end, final value `42`.

**Implementation notes**

- Validated with `Qwen/Qwen2.5-0.5B-Instruct` through `Transformers`.
- Supports tagged requests, structured capture, and prefilled structured prompt mode.
- Still round-trips through runtime feedback rather than a native execution block.

**Testing status**

- Passed the five-way comparison scenario with final value `42`.
- Recorded `intercepted_requests=1` and `structured_captures=1`.
- Covered by stages 4 through 8 plus the comparison harness.

### 5. Open-Source Execution Block

This is the deepest current integration: open-weight generation stays in the loop, yet the execution round-trip is resolved through a native execution-block path instead of a wrapper-only text protocol.

**Execution boundary.** Qwen still emits the request, but the runtime resolves it natively and returns compact execution feedback instead of an `exec_response` text block.

**Canonical 6 × 7 run.** `857.05 ms` end-to-end, final value `42`.

**Implementation notes**

- Pins the backend to `transformer_hull` for the native execution round.
- Removes the `exec_response` text loop from the hot path.
- Acts as the bridge between today's wrapper integration and tomorrow's true in-model execution heads.

**Testing status**

- Passed the five-way comparison scenario with final value `42`.
- Recorded `native_execution_rounds=1` with no runtime answer fallback.
- Covered by stage 9, the comparison harness, and the transformer regression suite.

## Comparison Snapshot

![Latency chart](assets/five-implementation-latency.png)

| Depth | Method | Category | End-to-end | Used execution | Key runtime signal |
| ---: | --- | --- | ---: | --- | --- |
| 1 | Reference Direct | direct | 30.85 ms | yes | - |
| 2 | Append-Only Naive Direct | direct | 17.52 ms | yes | - |
| 3 | Closed-Source Sidecar | closed source | 4.115 s | yes | tool_calls=1 |
| 4 | Open-Source Wrapper | open source | 1.178 s | yes | structured_captures=1 |
| 5 | Open-Source Execution Block | open source | 857.05 ms | yes | native_execution_rounds=1 |

## What the Article Examples Added

The original repository already handled toy arithmetic and small compiled-C examples. The next requirement was stronger: validate the examples that the Percepta article actually shows to readers. That changed the quality bar for the project.

![Article examples](assets/article-example-results.png)

The published Hungarian example now succeeds across four local backends with the same result `206`. The published Sudoku puzzle now succeeds end-to-end under the reference WASM executor with checksum `1276684605`.

The Sudoku story is especially important because it separates two claims that are often blurred together:

- full-result correctness under the semantic reference executor,
- prefix-state equivalence under the append-only and transformer-style paths.

That distinction keeps the article honest: the long puzzle is fully solved in the repository, but only the reference path currently completes the entire `22M+` step run as part of the preserved validation artifacts.

![Sudoku prefix validation](assets/sudoku-prefix-validation.png)

## What Each Layer Taught Us

- The reference path is still indispensable. It is the only clean oracle for semantic correctness.
- The append-only naive path proves that the article mechanism is not just an optimization trick. State really can be reconstructed from append-only writes.
- The closed-source sidecar path proves that hosted APIs can participate, but only through a hard tool boundary.
- The open-source wrapper path proves that runtime interception can turn a plain local model into an execution-aware system without changing model weights.
- The open-source execution-block path is the most promising bridge to the article’s end state because it removes the text response loop and starts to behave like a native execution lane.

## Validation Matrix

![Validation matrix](assets/five-implementation-validation-matrix.png)

## Final Summary

The repository now has five distinct implementations that all return the same canonical answer but represent very different architectural commitments. The deeper the implementation, the closer execution moves to the model boundary. The harder the article example, the more important it becomes to preserve separate validation artifacts instead of folding everything into a single headline claim.

Today’s strongest supported statement is therefore narrower and more useful than marketing language:

> We can now compare five concrete execution layers inside one codebase, validate them against the same semantic oracle, and demonstrate that the article’s Hungarian and Sudoku examples survive that ladder instead of only toy arithmetic.

The remaining gap is also clear: a true execution-head path inside a real open-weight model still has to replace the last deterministic Python transition layer.

## Source Files

- Original article: https://www.percepta.ai/blog/can-llms-be-computers
- `docs/five-way-comparison.json`
- `docs/article-example-validation.json`
- `docs/sudoku-result-validation.json`
- `docs/stage-validation-log.md`
