#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

RUNTIME_DIR="${SKILL_SCANNER_RUNTIME_DIR:-$SKILL_DIR/.runtime}"
VENV_DIR="$RUNTIME_DIR/venv"
PYTHON_BIN="${SKILL_SCANNER_PYTHON:-python3}"
WHEEL_DIR="$SKILL_DIR/vendor/wheels"
REQ_FILE="$SKILL_DIR/vendor/requirements-offline.txt"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Error: Python interpreter not found: $PYTHON_BIN" >&2
  exit 1
fi

mkdir -p "$RUNTIME_DIR"

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

VENV_PY="$VENV_DIR/bin/python"

if [[ "${SKILL_SCANNER_INSTALL_WHEELS:-0}" == "1" ]]; then
  if [[ ! -d "$WHEEL_DIR" ]]; then
    echo "Error: wheel directory not found: $WHEEL_DIR" >&2
    exit 1
  fi
  if [[ ! -f "$REQ_FILE" ]]; then
    echo "Error: requirements file not found: $REQ_FILE" >&2
    exit 1
  fi
  if ! ls "$WHEEL_DIR"/*.whl >/dev/null 2>&1; then
    echo "Error: no wheels found in $WHEEL_DIR" >&2
    exit 1
  fi

  "$VENV_PY" -m pip install --no-index --find-links "$WHEEL_DIR" -r "$REQ_FILE"
fi

echo "$VENV_PY"
