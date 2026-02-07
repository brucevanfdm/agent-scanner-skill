#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  ./scripts/run-scan.sh <scan|scan-all> <target_path> [quick|balanced|deep-agent|ci] [extra args...]

Examples:
  ./scripts/run-scan.sh scan ./my-skill quick
  ./scripts/run-scan.sh scan ./my-skill balanced --yara-mode strict
  ./scripts/run-scan.sh scan ./my-skill deep-agent
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
SCANNER_PKG_DIR="$SKILL_DIR/skill_scanner"
VENDOR_PY_DIR="$SKILL_DIR/vendor/python"
INSTALL_SCRIPT="$SCRIPT_DIR/install-scanner.sh"

MODE="$1"
TARGET="$2"
PROFILE="balanced"
SHIFT_COUNT=2
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
  case "$3" in
    quick|balanced|deep-agent|ci)
      PROFILE="$3"
      SHIFT_COUNT=3
      ;;
    -*)
      # No profile provided; treat remaining args as passthrough CLI flags.
      ;;
    *)
      echo "Error: profile must be one of quick|balanced|deep-agent|ci" >&2
      exit 1
      ;;
  esac
fi

shift "$SHIFT_COUNT"

EXTRA_ARGS=("$@")

PROFILE_ARGS=()
HOST_AGENT_MODE=0
DEFAULT_REVIEW_JSON_PATH="${SKILL_DIR}/.runtime/host-agent-review.json"
HOST_AGENT_PROMPT_PATH="${SKILL_DIR}/.runtime/host-agent-review-prompt.md"
REVIEW_JSON_PATH="$DEFAULT_REVIEW_JSON_PATH"
case "$PROFILE" in
  quick)
    PROFILE_ARGS+=(--use-trigger --format summary)
    ;;
  balanced)
    PROFILE_ARGS+=(--use-behavioral --use-trigger --format summary)
    ;;
  deep-agent)
    # Host-agent mode: do not call external model APIs from scanner.
    PROFILE_ARGS+=(--use-behavioral --use-trigger --format json)
    HOST_AGENT_MODE=1
    ;;
  ci)
    PROFILE_ARGS+=(--use-behavioral --use-trigger --format sarif --fail-on-findings)
    ;;
  *)
    echo "Error: profile must be one of quick|balanced|deep-agent|ci" >&2
    exit 1
    ;;
esac

if [[ ! -d "$SCANNER_PKG_DIR" ]]; then
  echo "Error: scanner source not found: $SCANNER_PKG_DIR" >&2
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
  export PYTHONPATH="$VENDOR_PY_DIR:$SKILL_DIR:$PYTHONPATH"
else
  export PYTHONPATH="$VENDOR_PY_DIR:$SKILL_DIR"
fi

cd "$SKILL_DIR"

CMD=("${PYTHON_CMD[@]}" -m skill_scanner.cli.cli "$MODE" "$TARGET_ABS" "${PROFILE_ARGS[@]}")

# deep-agent mode needs a JSON output file for host-agent semantic review.
if [[ "$HOST_AGENT_MODE" -eq 1 ]]; then
  HAS_OUTPUT_ARG=0
  for (( i=0; i<${#EXTRA_ARGS[@]}; i++ )); do
    arg="${EXTRA_ARGS[$i]}"
    if [[ "$arg" == "--output" || "$arg" == "-o" || "$arg" == --output=* ]]; then
      HAS_OUTPUT_ARG=1
      if [[ "$arg" == --output=* ]]; then
        REVIEW_JSON_PATH="${arg#--output=}"
      elif [[ $((i + 1)) -lt ${#EXTRA_ARGS[@]} ]]; then
        REVIEW_JSON_PATH="${EXTRA_ARGS[$((i + 1))]}"
      fi
      break
    fi
  done
  if [[ "$HAS_OUTPUT_ARG" -eq 0 ]]; then
    mkdir -p "$(dirname "$DEFAULT_REVIEW_JSON_PATH")"
    EXTRA_ARGS+=(--output "$DEFAULT_REVIEW_JSON_PATH")
    REVIEW_JSON_PATH="$DEFAULT_REVIEW_JSON_PATH"
  fi
fi

if [[ ${#EXTRA_ARGS[@]} -gt 0 ]]; then
  CMD+=("${EXTRA_ARGS[@]}")
fi

"${CMD[@]}"

if [[ "$HOST_AGENT_MODE" -eq 1 ]]; then
  mkdir -p "$(dirname "$HOST_AGENT_PROMPT_PATH")"

  # Normalize JSON path for prompt readability.
  if [[ "$REVIEW_JSON_PATH" = /* ]]; then
    REVIEW_JSON_ABS="$REVIEW_JSON_PATH"
  else
    REVIEW_JSON_ABS="$SKILL_DIR/$REVIEW_JSON_PATH"
  fi

  cat > "$HOST_AGENT_PROMPT_PATH" <<EOF
# Host-Agent Semantic Security Review Task (deep-agent)

You are running in the same repository and should complete this task end-to-end without calling external model APIs.

## Inputs
- Scan JSON report: \`$REVIEW_JSON_ABS\`
- Target path: \`$TARGET_ABS\`
- Mode: \`$MODE\`
- Profile: \`$PROFILE\`

## Required Actions
1. Load and summarize findings by severity and analyzer from the JSON report.
2. Re-verify every \`CRITICAL\` and \`HIGH\` finding against source files (include \`file:line\` evidence).
3. Review \`MEDIUM\` findings and mark likely false positives with rationale.
4. Detect any obvious missed high-impact risks not captured by static/behavioral checks.
5. Propose concrete remediations, then apply patches for highest-risk issues first.
6. Run relevant verification commands/tests and report outcomes.

## Output Format
1. Findings first (ordered by severity), each with:
   - severity, rule_id, affected file reference, exploitability rationale
2. Open questions/assumptions (if any)
3. Patch summary (files changed and why)
4. Verification commands and results

## Constraints
- Do not use external model APIs from scanner codepaths for this task.
- Ground all conclusions in repository evidence and scanner output.
EOF

  echo ""
  echo "[deep-agent] Semantic handoff (no separate external API key required):"
  echo "1) Scan JSON: $REVIEW_JSON_ABS"
  echo "2) Host-agent prompt: $HOST_AGENT_PROMPT_PATH"
  echo "3) Execute that prompt with your host agent for autonomous review + remediation."
fi
