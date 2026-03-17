#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

MODEL_ID="${QWEN_MODEL_ID:-Qwen/Qwen2.5-0.5B-Instruct}"
DEVICE="${QWEN_DEVICE:-mps}"
GEMINI_MODEL="${GEMINI_MODEL:-gemini-3-flash-preview}"
MARKDOWN_OUTPUT="${COMPARISON_MARKDOWN_OUTPUT:-docs/five-way-comparison.md}"
JSON_OUTPUT="${COMPARISON_JSON_OUTPUT:-docs/five-way-comparison.json}"

uv run python -m unittest discover -s tests -v
python3 -m compileall src tests
uv run llm-computer-compare \
  --model-id "$MODEL_ID" \
  --device "$DEVICE" \
  --gemini-model "$GEMINI_MODEL" \
  --markdown-output "$MARKDOWN_OUTPUT" \
  --json-output "$JSON_OUTPUT"
