#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

uv run python -m unittest discover -s tests -v \
  -p 'test_service.py'
uv run python -m unittest discover -s tests -v \
  -p 'test_integration.py'
