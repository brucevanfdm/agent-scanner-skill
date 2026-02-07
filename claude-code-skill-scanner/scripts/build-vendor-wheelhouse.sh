#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
WHEEL_DIR="$SKILL_DIR/vendor/wheels"
REQ_FILE="$SKILL_DIR/vendor/requirements-offline.txt"
PYTHON_BIN="${SKILL_SCANNER_PYTHON:-python3}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Error: Python interpreter not found: $PYTHON_BIN" >&2
  exit 1
fi

mkdir -p "$WHEEL_DIR"

"$PYTHON_BIN" -m pip download --dest "$WHEEL_DIR" -r "$REQ_FILE"

echo "Wheelhouse ready: $WHEEL_DIR"
