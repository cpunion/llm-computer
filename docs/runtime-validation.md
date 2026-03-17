# Runtime Validation

Date: 2026-03-17

## Environment

The local runtime validation target is:

- host: Apple Silicon macOS
- Python manager: `uv`
- project Python: `3.12`

The environment is created with:

```bash
uv sync --python 3.12 --extra transformers --extra gemini
```

## Installed runtime packages

Representative validated versions from `uv sync`:

- `torch==2.10.0`
- `transformers==5.3.0`
- `accelerate==1.13.0`
- `google-genai==1.67.0`
- `python-dotenv==1.2.2`

## Validated commands

Base test and benchmark validation:

```bash
uv run python -m unittest discover -s tests -v
uv run llm-computer
```

Observed result after the latest interception-stage changes:

- `34` unit tests passed
- `2` tests skipped because the environment already includes the optional
  dependency branches they would otherwise exercise

Closed-source Gemini validation:

```bash
uv run llm-computer-gemini \
  --model gemini-3-flash-preview \
  --force-tool-use \
  --prompt 'Execute this WAT module with the execution tool and return only the final integer: (module (func (export "main") (result i32) i32.const 6 i32.const 7 i32.mul))'
```

Observed result:

- final answer: `42`
- `tool_calls=1`
- `used_execution=true`

Additional observation:

- without forced tool calling, `gemini-3-flash-preview` often answers simple
  arithmetic directly and may skip the sidecar entirely
- the stable validation path therefore uses forced tool calling plus the manual
  function-response loop documented in `docs/gemini-integration.md`

Open-source Qwen validation is recorded in `docs/qwen-transformers-integration.md`.

Observed status on 2026-03-17:

- the `Transformers` runtime scaffold itself is implemented and test-covered
- a live end-to-end open-source run completed with
  `Qwen/Qwen2.5-0.5B-Instruct` on `mps`
- the same path emitted a valid `exec_request`, consumed a real
  `exec_response`, and returned the final answer `42`
- the request-boundary interception mode also completed a live run with the same
  model and returned the final answer `42`
- the interception summary reported `intercepted_requests=1`
- the structured-request capture mode also completed a live run with the same
  model and returned the final answer `42`
- the structured summary reported `intercepted_requests=1` and
  `structured_captures=1`
- the built-in structured prompt mode also completed a live run with the same
  model and returned the final answer `42`
- the built-in structured prompt summary again reported `intercepted_requests=1`
  and `structured_captures=1`
- the prefilled structured prompt mode also completed a live run with the same
  model and returned the final answer `42`
- the prefilled summary reported `intercepted_requests=1`,
  `structured_captures=1`, and `runtime_answer_fallbacks=1`
- the native execution-block mode also completed a live run with the same model
  and returned the final answer `42`
- the native execution-block summary reported `intercepted_requests=1`,
  `structured_captures=1`, `native_execution_rounds=1`, and
  `runtime_answer_fallbacks=0`
- live checkpoint downloads for `Qwen/Qwen3-8B` and `Qwen/Qwen3-0.6B` were also
  attempted but did not finish in the available session
- the resulting conclusion is that the open-source runtime path is validated in
  principle, while `Qwen3-8B` specifically remains blocked by checkpoint fetch
  throughput

Validated interception command:

```bash
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

Validated structured-capture command:

```bash
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

Validated structured-prompt command:

```bash
./scripts/stage7_qwen_structured_prompt_mode.sh
```

Validated prefilled structured-prompt command:

```bash
./scripts/stage8_qwen_prefilled_structured_mode.sh
```

Validated native execution-block command:

```bash
./scripts/stage9_qwen_execution_block.sh
```

Validated five-way comparison command:

```bash
./scripts/stage10_five_way_comparison.sh
```

Observed result:

- all five comparison rows completed successfully and returned `42`
- `reference_direct` and `append_only_naive_direct` remained the fastest rows
  because they bypass model orchestration entirely
- `open_source_execution_block` completed faster than
  `open_source_wrapper` in the recorded run while keeping
  `intercepted_requests=1` and `structured_captures=1`
- `closed_source_sidecar` completed successfully with `tool_calls=1`
- the full recorded output is preserved in `docs/five-way-comparison.md` and
  `docs/five-way-comparison.json`

Validated article-example command:

```bash
./scripts/stage11_article_examples.sh
```

Observed result:

- all `49` current unit tests passed and `2` were skipped
- the article's Hungarian `10x10` matching example returned the expected cost
  `206` under:
  - the reference interpreter
  - append-only naive execution
  - append-only hull execution
  - transformer-style hull execution
- the article's Sudoku example returned the independently verified checksum
  `1276684605` under the reference interpreter
- the Sudoku reference trace completed in `22,370,167` steps in the recorded
  run
- the full recorded output is preserved in
  `docs/article-example-validation.md` and
  `docs/article-example-validation.json`
