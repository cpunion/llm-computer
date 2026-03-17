#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

uv run python -m unittest discover -s tests -v
python3 -m compileall src tests
uv run llm-computer-sudoku-validate \
  --prefix-budgets 1000 10000 100000 \
  --naive-max-budget 10000 \
  --hull-max-budget 100000 \
  --transformer-max-budget 100000 \
  --full-reference-max-steps "${SUDOKU_FULL_REFERENCE_MAX_STEPS:-50000000}" \
  --markdown-output docs/sudoku-result-validation.md \
  --json-output docs/sudoku-result-validation.json
