#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "Stage 2 baseline selections"
echo
rg -n "Qwen3-8B|Transformers|SGLang|vLLM|TensorRT-LLM" \
  docs/open-source-selection.md \
  docs/model-integration-plan.md
