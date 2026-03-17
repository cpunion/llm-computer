#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

MODEL="${GEMINI_MODEL:-gemini-3-flash-preview}"

uv run python -m unittest discover -s tests -v
uv run llm-computer-gemini \
  --model "$MODEL" \
  --force-tool-use \
  --prompt 'Execute this WAT module with the execution tool and return only the final integer: (module (func (export "main") (result i32) i32.const 6 i32.const 7 i32.mul))'
