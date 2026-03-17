#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

MODEL_ID="${QWEN_MODEL_ID:-Qwen/Qwen2.5-0.5B-Instruct}"
DEVICE="${QWEN_DEVICE:-mps}"

uv run python -m unittest discover -s tests -v
python3 -m compileall src tests
uv run llm-computer-qwen \
  --model-id "$MODEL_ID" \
  --device "$DEVICE" \
  --integration-mode execution_block \
  --execution-prompt-mode structured \
  --intercept-request-boundary \
  --prefill-request-prefix \
  --max-round-trips 3 \
  --max-new-tokens 128 \
  --system 'Protocol requirement: do not answer directly. The runtime has already emitted the opening { of the JSON object. Continue with the remaining keys only, without restarting the object. Set source_kind to "wat", mode to "auto", export_name to "main", and source to exactly this WAT module string: (module (func (export \"main\") (result i32) i32.const 6 i32.const 7 i32.mul)). After runtime feedback, reply with only the final integer.' \
  --prompt 'Compute 6 * 7 exactly.'
