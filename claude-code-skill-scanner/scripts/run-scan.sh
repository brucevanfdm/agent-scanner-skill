#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  ./scripts/run-scan.sh <scan|scan-all> <target_path> [quick|balanced|deep|ci] [extra args...]

Examples:
  ./scripts/run-scan.sh scan ./my-skill quick
  ./scripts/run-scan.sh scan ./my-skill balanced --yara-mode strict
  ./scripts/run-scan.sh scan-all ./skills ci --recursive --output results.sarif

Environment:
  SKILL_SCANNER_PYTHON=python3         Python executable
  SKILL_SCANNER_RUNTIME=embedded|venv  Runtime mode (default: embedded)
USAGE
}

if [[ $# -lt 2 ]]; then
  usage
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
EMBEDDED_DIR="$SKILL_DIR/embedded"
VENDOR_PY_DIR="$SKILL_DIR/vendor/python"
INSTALL_SCRIPT="$SCRIPT_DIR/install-scanner.sh"

MODE="$1"
TARGET="$2"
PROFILE="${3:-balanced}"
TARGET_ABS="$TARGET"

if [[ -e "$TARGET" ]]; then
  TARGET_DIR="$(cd "$(dirname "$TARGET")" && pwd)"
  TARGET_BASE="$(basename "$TARGET")"
  TARGET_ABS="$TARGET_DIR/$TARGET_BASE"
fi

if [[ "$MODE" != "scan" && "$MODE" != "scan-all" ]]; then
  echo "Error: mode must be 'scan' or 'scan-all'" >&2
  exit 1
fi

if [[ $# -ge 3 ]]; then
  shift 3
else
  shift 2
fi

EXTRA_ARGS=()
if [[ $# -gt 0 ]]; then
  EXTRA_ARGS=("$@")
fi

PROFILE_ARGS=()
case "$PROFILE" in
  quick)
    PROFILE_ARGS+=(--use-trigger --format summary)
    ;;
  balanced)
    PROFILE_ARGS+=(--use-behavioral --use-trigger --format summary)
    ;;
  deep)
    PROFILE_ARGS+=(--use-behavioral --use-trigger --use-llm --enable-meta --format summary)
    ;;
  ci)
    PROFILE_ARGS+=(--use-behavioral --use-trigger --format sarif --fail-on-findings)
    ;;
  *)
    echo "Error: profile must be one of quick|balanced|deep|ci" >&2
    exit 1
    ;;
esac

if [[ ! -d "$EMBEDDED_DIR/skill_scanner" ]]; then
  echo "Error: embedded source not found: $EMBEDDED_DIR/skill_scanner" >&2
  exit 1
fi

if [[ ! -f "$VENDOR_PY_DIR/yaml.py" ]]; then
  echo "Error: vendor runtime modules missing in $VENDOR_PY_DIR" >&2
  exit 1
fi

RUNTIME_MODE="${SKILL_SCANNER_RUNTIME:-embedded}"
if [[ "$RUNTIME_MODE" != "embedded" && "$RUNTIME_MODE" != "venv" ]]; then
  echo "Error: SKILL_SCANNER_RUNTIME must be embedded or venv" >&2
  exit 1
fi

PYTHON_CMD=()
if [[ "$RUNTIME_MODE" == "venv" ]]; then
  if [[ ! -x "$INSTALL_SCRIPT" ]]; then
    echo "Error: install script not found: $INSTALL_SCRIPT" >&2
    exit 1
  fi
  VENV_PY="$($INSTALL_SCRIPT)"
  PYTHON_CMD=("$VENV_PY")
else
  SYS_PY="${SKILL_SCANNER_PYTHON:-python3}"
  if ! command -v "$SYS_PY" >/dev/null 2>&1; then
    echo "Error: Python interpreter not found: $SYS_PY" >&2
    exit 1
  fi
  PYTHON_CMD=("$SYS_PY")
fi

if [[ -n "${PYTHONPATH:-}" ]]; then
  export PYTHONPATH="$VENDOR_PY_DIR:$EMBEDDED_DIR:$PYTHONPATH"
else
  export PYTHONPATH="$VENDOR_PY_DIR:$EMBEDDED_DIR"
fi

cd "$SKILL_DIR"

CMD=("${PYTHON_CMD[@]}" -m skill_scanner.cli.cli "$MODE" "$TARGET_ABS" "${PROFILE_ARGS[@]}")
if [[ ${#EXTRA_ARGS[@]} -gt 0 ]]; then
  CMD+=("${EXTRA_ARGS[@]}")
fi

"${CMD[@]}"
