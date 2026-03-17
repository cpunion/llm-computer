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
- live checkpoint downloads for `Qwen/Qwen3-8B` and `Qwen/Qwen3-0.6B` were
  attempted but did not finish in the available session
- the resulting conclusion is that the open-source runtime code is ready, but
  live open-weight validation in this session remained blocked by checkpoint
  fetch throughput
