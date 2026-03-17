#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

MARKDOWN_OUTPUT="${ARTICLE_EXAMPLES_MARKDOWN_OUTPUT:-docs/article-example-validation.md}"
JSON_OUTPUT="${ARTICLE_EXAMPLES_JSON_OUTPUT:-docs/article-example-validation.json}"
SUDOKU_MAX_STEPS="${ARTICLE_SUDOKU_MAX_STEPS:-50000000}"

uv run python -m unittest discover -s tests -v
python3 -m compileall src tests
uv run llm-computer-article-examples \
  --sudoku-max-steps "$SUDOKU_MAX_STEPS" \
  --markdown-output "$MARKDOWN_OUTPUT" \
  --json-output "$JSON_OUTPUT"
