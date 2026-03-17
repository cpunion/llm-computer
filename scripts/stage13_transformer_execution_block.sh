#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

uv run python -m unittest discover -s tests -v
python3 -m compileall src tests
