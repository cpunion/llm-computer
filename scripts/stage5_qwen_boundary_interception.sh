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
  --few-shot-example \
  --intercept-request-boundary \
  --max-round-trips 3 \
  --max-new-tokens 128 \
  --system 'Protocol requirement: your first reply must be exactly one <exec_request>...</exec_request> block and nothing else. Inside the tags output one valid JSON object only. Use source_kind="wat", mode="auto", and source containing a complete WAT module. Do not answer directly. Do not use Python. After runtime feedback, reply with only the final integer.' \
  --prompt 'Compute 6 * 7 exactly.'
