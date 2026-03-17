# Stage Validation Log

Date: 2026-03-17

This document records the repository's staged implementation progress together
with the validation commands and observed outcomes used at each stage.

Reusable scripts for these stages are kept under `scripts/`.

## Stage 0: Semantic Core

Goal:

- reproduce the article's execution semantics over a restricted WASM subset
- validate append-only execution and transformer-style verification against a
  reference interpreter

Representative commits:

- `e45a180` `Build article-aligned WASM executor and transformer verifier`
- `cc48f24` `Refactor tiny transformer execution into explicit block`

Validation:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m llm_computer
```

Observed outcome:

- append-only executor matched the reference interpreter on the current WAT,
  memory, and compiled-C examples
- transformer-style verifier matched the reference interpreter on the supported
  subset
- long traces showed consistent hull-timeline speedups while short traces
  remained slower

## Stage 1: Shared Sidecar Contract

Goal:

- stabilize a request and response schema that can be shared by open-source and
  closed-source model integrations

Representative commits:

- `eb28a73` `Add execution service and integration adapters`

Validation:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Observed outcome:

- `ExecutionRequest` and `ExecutionResponse` round-tripped correctly
- open-source tagged-span integration and closed-source tool-schema integration
  both resolved through the same `ExecutionService`

## Stage 2: Open-Source Model Baseline

Goal:

- select a concrete open-source baseline and define the runtime migration order

Representative commits:

- `cea95bf` `Document open-source model selection baseline`

Validation:

- document review only

Observed outcome:

- selected baseline: `Qwen3-8B + Transformers`
- follow-up runtime order fixed as `SGLang -> vLLM -> TensorRT-LLM`

## Stage 3: uv Runtime and Hosted Gemini Validation

Goal:

- move runtime management to `uv`
- validate one closed-source hosted integration against the shared tool schema

Representative commits:

- `263d644` `Manage runtime with uv and add Qwen CLI scaffold`
- `e1a13ba` `Add Gemini integration and runtime validation docs`

Validation:

```bash
uv sync --python 3.12 --extra transformers --extra gemini
uv run python -m unittest discover -s tests -v
uv run llm-computer-gemini \
  --model gemini-3-flash-preview \
  --force-tool-use \
  --prompt 'Execute this WAT module with the execution tool and return only the final integer: (module (func (export "main") (result i32) i32.const 6 i32.const 7 i32.mul))'
```

Observed outcome:

- the `uv` environment was created successfully
- Gemini returned the final answer `42`
- the runtime summary reported `tool_calls=1` and `used_execution=true`

## Stage 4: Open-Source Transformers Sidecar Validation

Goal:

- validate the open-source `Transformers + sidecar` path with a real model

Representative commits:

- `1457b57` `Add Qwen3 Transformers integration scaffold`
- `87a3796` `Harden open-source request parsing and validate Qwen family runtime`

Validation:

```bash
uv run python -m unittest discover -s tests -v
uv run llm-computer-qwen \
  --model-id Qwen/Qwen2.5-0.5B-Instruct \
  --device mps \
  --few-shot-example \
  --max-round-trips 3 \
  --max-new-tokens 128 \
  --system 'Protocol requirement: your first reply must be exactly one <exec_request>...</exec_request> block and nothing else. Inside the tags output one valid JSON object only. Use source_kind="wat", mode="auto", and source containing a complete WAT module. Do not answer directly. Do not use Python. After runtime feedback, reply with only the final integer.' \
  --prompt 'Compute 6 * 7 exactly.'
```

Observed outcome:

- a real cached Qwen-family model emitted a valid `exec_request`
- the sidecar returned an `exec_response` with result `[42]`
- the model returned the final answer `42`
- the runtime summary reported `used_execution=true` and `turns=2`

## Stage 5: Request-Boundary Interception Prototype

Goal:

- move the open-source runtime closer to true runtime interception by stopping
  generation as soon as `</exec_request>` appears

Validation:

```bash
uv run python -m unittest discover -s tests -v
python3 -m compileall src tests
uv run llm-computer-qwen \
  --model-id Qwen/Qwen2.5-0.5B-Instruct \
  --device mps \
  --few-shot-example \
  --intercept-request-boundary \
  --max-round-trips 3 \
  --max-new-tokens 128 \
  --system 'Protocol requirement: your first reply must be exactly one <exec_request>...</exec_request> block and nothing else. Inside the tags output one valid JSON object only. Use source_kind="wat", mode="auto", and source containing a complete WAT module. Do not answer directly. Do not use Python. After runtime feedback, reply with only the final integer.' \
  --prompt 'Compute 6 * 7 exactly.'
```

Observed outcome:

- `31` unit tests passed and `2` were skipped because optional dependency
  branches are already installed in the environment
- `python3 -m compileall src tests` completed successfully
- the real open-source live run again returned the final answer `42`
- the runtime summary reported `used_execution=true`, `turns=2`, and
  `intercepted_requests=1`

## Stage 6: Structured Request Capture

Goal:

- reduce dependence on the closing request tag by canonicalizing a complete
  execution JSON object as soon as it becomes valid

Validation:

```bash
uv run python -m unittest discover -s tests -v
python3 -m compileall src tests
uv run llm-computer-qwen \
  --model-id Qwen/Qwen2.5-0.5B-Instruct \
  --device mps \
  --few-shot-example \
  --intercept-request-boundary \
  --max-round-trips 3 \
  --max-new-tokens 128 \
  --system 'Protocol requirement: do not answer directly. Your first reply must begin with <exec_request> and then contain exactly one valid JSON object. Stop immediately after the JSON object and do not emit </exec_request>. Set source_kind to "wat", mode to "auto", export_name to "main", and source to exactly this WAT module string: (module (func (export \"main\") (result i32) i32.const 6 i32.const 7 i32.mul)). After runtime feedback, reply with only the final integer.' \
  --prompt 'Compute 6 * 7 exactly.'
```

Observed outcome:

- `34` unit tests passed and `2` were skipped because optional dependency
  branches are already installed in the environment
- `python3 -m compileall src tests` completed successfully
- the real open-source live run again returned the final answer `42`
- the runtime summary reported `used_execution=true`, `turns=2`,
  `intercepted_requests=1`, and `structured_captures=1`

## Stage 7: Structured Prompt Mode

Goal:

- stop asking the model for tagged request wrappers and make structured JSON
  emission a first-class open-source prompt mode

Validation:

```bash
./scripts/stage7_qwen_structured_prompt_mode.sh
```

Observed outcome:

- `36` unit tests passed and `2` were skipped because optional dependency
  branches are already installed in the environment
- `python3 -m compileall src tests` completed successfully
- the real open-source live run returned the final answer `42`
- the runtime summary reported `used_execution=true`, `turns=2`,
  `intercepted_requests=1`, and `structured_captures=1`

## Stage 8: Prefilled Structured Prompt Mode

Goal:

- let the runtime inject the opening request prefix before generation so the
  model only needs to continue the JSON object

Validation:

```bash
./scripts/stage8_qwen_prefilled_structured_mode.sh
```

Observed outcome:

- `39` unit tests passed and `2` were skipped because optional dependency
  branches are already installed in the environment
- `python3 -m compileall src tests` completed successfully
- the real open-source live run returned the final answer `42`
- the runtime summary reported `used_execution=true`, `turns=2`,
  `intercepted_requests=1`, `structured_captures=1`, and
  `runtime_answer_fallbacks=1`

## Stage 9: Native Execution Block Mode

Goal:

- keep the same request extraction path but resolve execution natively inside
  the open-source orchestrator instead of routing through `<exec_response>` text

Validation:

```bash
./scripts/stage9_qwen_execution_block.sh
```

Observed outcome:

- `41` unit tests passed and `2` were skipped because optional dependency
  branches are already installed in the environment
- `python3 -m compileall src tests` completed successfully
- the real open-source live run returned the final answer `42`
- the runtime summary reported `used_execution=true`, `turns=2`,
  `intercepted_requests=1`, `structured_captures=1`,
  `native_execution_rounds=1`, and `runtime_answer_fallbacks=0`

## Stage 10: Five-Way Comparison Matrix

Goal:

- collapse the repository's final comparison target into one reproducible
  harness with five rows:
  - semantic control
  - naive direct append-only execution
  - open-source wrapper
  - open-source execution block
  - closed-source sidecar

Validation:

```bash
./scripts/stage10_five_way_comparison.sh
```

Observed outcome:

- `47` unit tests passed and `2` were skipped because optional dependency
  branches are already installed in the environment
- `python3 -m compileall src tests` completed successfully
- the comparison harness wrote
  `docs/five-way-comparison.md` and `docs/five-way-comparison.json`
- all five comparison rows returned the final value `42`
- the open-source wrapper used execution successfully with
  `intercepted_requests=1` and `structured_captures=1`
- the open-source execution-block path also used execution successfully with
  `intercepted_requests=1`, `structured_captures=1`, and
  `native_execution_rounds=1`
- the closed-source Gemini path completed successfully with `tool_calls=1`
- in the recorded run, `open_source_execution_block` completed faster than
  `open_source_wrapper`, while the hosted Gemini sidecar remained the slowest
  end-to-end path

## Stage 11: Article Example Validation

Goal:

- validate the article's published Hungarian and Sudoku examples against the
  current WASM executor stack
- preserve a reproducible command and report for later article writing

Validation:

```bash
./scripts/stage11_article_examples.sh
```

Observed outcome:

- `49` unit tests passed and `2` were skipped because optional dependency
  branches are already installed in the environment
- `python3 -m compileall src tests` completed successfully
- the article's Hungarian `10x10` matching example returned the expected cost
  `206` under:
  - the reference interpreter
  - append-only naive execution
  - append-only hull execution
  - transformer-style hull execution
- the article's Sudoku example returned the independently verified checksum
  `1276684605` under the reference interpreter
- the recorded Sudoku reference trace finished in `22,370,167` steps
- the report was written to `docs/article-example-validation.md` and
  `docs/article-example-validation.json`

## Current conclusion

The repository has now validated three progressively stronger integration
claims:

1. the execution backends reproduce the current semantic subset correctly
2. the shared sidecar contract works across open-source and closed-source
   integration styles
3. the open-source path can now be driven through plain sidecar round trips,
   through a request-boundary interception wrapper, and through a deeper
   structured-request capture wrapper
4. the open-source path now also supports a first-class structured prompt mode
   rather than relying exclusively on tagged request wrappers
5. the open-source path now also supports runtime-prefilled request prefixes
   that further reduce how much request scaffolding the model must emit
6. the open-source path now also supports a native execution-block mode that
   removes the `<exec_response>` text round-trip from the execution loop
7. the repository now has one reproducible five-way matrix that compares the
   exact final target set requested for the article draft
8. the repository now validates the article's Hungarian and Sudoku examples
   directly, not only internal toy programs and integration scaffolds

The remaining gap to the article's stronger end state is still the same:

- no true execution heads inside a real model
- no execution-only KV path
- no compilation of WASM semantics into model weights
- no live `Qwen3-8B` checkpoint validation yet
