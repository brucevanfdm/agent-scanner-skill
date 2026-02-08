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

Cascade behavior (quick|balanced|deep-agent):
  - Always starts from quick stage
  - Auto-escalates to next stage if findings are detected
  - Prints final conclusion + reasons to stdout (no report file by default)

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

declare -a EXTRA_ARGS=()
EXTRA_ARGS_COUNT=$#
if [[ "$EXTRA_ARGS_COUNT" -gt 0 ]]; then
  EXTRA_ARGS=("$@")
fi

PROFILE_ARGS=()
if [[ "$PROFILE" == "ci" ]]; then
  PROFILE_ARGS+=(--use-behavioral --use-trigger --format sarif --fail-on-findings)
fi

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

profile_rank() {
  case "$1" in
    quick) echo 1 ;;
    balanced) echo 2 ;;
    deep-agent) echo 3 ;;
    *) echo 0 ;;
  esac
}

next_profile() {
  case "$1" in
    quick) echo "balanced" ;;
    balanced) echo "deep-agent" ;;
    *) echo "" ;;
  esac
}

build_stage_args() {
  local stage="$1"
  case "$stage" in
    quick)
      echo "--use-trigger"
      ;;
    balanced)
      echo "--use-behavioral --use-trigger"
      ;;
    deep-agent)
      echo "--use-behavioral --use-trigger --use-deep-agent"
      ;;
    *)
      echo ""
      ;;
  esac
}

filter_cascade_args() {
  CASCADE_ARGS=()
  CASCADE_ARGS_COUNT=0
  if [[ "$EXTRA_ARGS_COUNT" -eq 0 ]]; then
    return
  fi
  local skip_next=0
  for arg in "${EXTRA_ARGS[@]}"; do
    if [[ "$skip_next" -eq 1 ]]; then
      skip_next=0
      continue
    fi
    case "$arg" in
      --output|-o|--format)
        skip_next=1
        ;;
      --output=*|--format=*|--compact|--detailed|--fail-on-findings)
        ;;
      *)
        CASCADE_ARGS+=("$arg")
        CASCADE_ARGS_COUNT=$((CASCADE_ARGS_COUNT + 1))
        ;;
    esac
  done
}

extract_metrics() {
  local json_input="$1"
  "${PYTHON_CMD[@]}" - "$MODE" "$json_input" <<'PY'
import json
import sys

mode = sys.argv[1]
data = json.loads(sys.argv[2])

if mode == "scan":
    findings = data.get("findings", [])
    total = len(findings)
    by = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
    for finding in findings:
        sev = str(finding.get("severity", "")).upper()
        if sev in by:
            by[sev] += 1
else:
    summary = data.get("summary", {})
    sev = summary.get("findings_by_severity", {}) or {}
    total = int(summary.get("total_findings", 0) or 0)
    by = {
        "CRITICAL": int(sev.get("critical", 0) or 0),
        "HIGH": int(sev.get("high", 0) or 0),
        "MEDIUM": int(sev.get("medium", 0) or 0),
        "LOW": int(sev.get("low", 0) or 0),
        "INFO": int(sev.get("info", 0) or 0),
    }

high_risk = 1 if (by["CRITICAL"] + by["HIGH"]) > 0 else 0
print(
    "\t".join(
        str(v)
        for v in (
            total,
            high_risk,
            by["CRITICAL"],
            by["HIGH"],
            by["MEDIUM"],
            by["LOW"],
            by["INFO"],
        )
    )
)
PY
}

extract_json_payload() {
  local raw_output="$1"
  "${PYTHON_CMD[@]}" - "$raw_output" <<'PY'
import json
import sys

text = sys.argv[1].strip()
start = text.find("{")
end = text.rfind("}")

if start == -1 or end == -1 or end < start:
    print("Error: scanner did not emit JSON payload.", file=sys.stderr)
    sys.exit(1)

payload = text[start : end + 1]
json.loads(payload)
print(payload)
PY
}

print_conclusion() {
  local final_stage="$1"
  local json_input="$2"
  "${PYTHON_CMD[@]}" - "$MODE" "$final_stage" "$json_input" <<'PY'
import json
import sys

mode = sys.argv[1]
final_stage = sys.argv[2]
data = json.loads(sys.argv[3])

severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}

def normalize_sev(value):
    sev = str(value or "").upper()
    return sev if sev in severity_order else "INFO"

if mode == "scan":
    findings = data.get("findings", [])
    by = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
    for finding in findings:
        by[normalize_sev(finding.get("severity"))] += 1

    high_risk = by["CRITICAL"] + by["HIGH"]
    total = len(findings)

    if high_risk > 0:
        conclusion = "Conclusion: RISK CONFIRMED"
    elif total > 0:
        conclusion = "Conclusion: NO HIGH-CONFIDENCE RISK"
    else:
        conclusion = "Conclusion: NO RISK FOUND"

    print(conclusion)
    print(f"Reason: Final stage={final_stage}, findings={total}, critical={by['CRITICAL']}, high={by['HIGH']}, medium={by['MEDIUM']}, low={by['LOW']}, info={by['INFO']}.")

    if findings:
        top = sorted(
            findings,
            key=lambda item: (
                severity_order.get(normalize_sev(item.get("severity")), 9),
                item.get("rule_id", ""),
                item.get("file_path") or "",
                int(item.get("line_number") or 0),
            ),
        )[:5]
        print("Key findings:")
        for finding in top:
            sev = normalize_sev(finding.get("severity"))
            rule_id = finding.get("rule_id", "UNKNOWN_RULE")
            title = finding.get("title", "").strip()
            file_path = finding.get("file_path") or "unknown"
            line = finding.get("line_number")
            location = f"{file_path}:{line}" if line else file_path
            if title:
                print(f"- [{sev}] {rule_id} at {location}: {title}")
            else:
                print(f"- [{sev}] {rule_id} at {location}")
else:
    summary = data.get("summary", {})
    sev = summary.get("findings_by_severity", {}) or {}
    crit = int(sev.get("critical", 0) or 0)
    high = int(sev.get("high", 0) or 0)
    medium = int(sev.get("medium", 0) or 0)
    low = int(sev.get("low", 0) or 0)
    info = int(sev.get("info", 0) or 0)
    total = int(summary.get("total_findings", 0) or 0)
    skills = int(summary.get("total_skills_scanned", 0) or 0)

    if crit + high > 0:
        conclusion = "Conclusion: RISK CONFIRMED"
    elif total > 0:
        conclusion = "Conclusion: NO HIGH-CONFIDENCE RISK"
    else:
        conclusion = "Conclusion: NO RISK FOUND"

    print(conclusion)
    print(f"Reason: Final stage={final_stage}, skills={skills}, findings={total}, critical={crit}, high={high}, medium={medium}, low={low}, info={info}.")

    risky = []
    for result in data.get("scan_results", []):
        findings = result.get("findings", [])
        c = 0
        h = 0
        for finding in findings:
            sev_name = normalize_sev(finding.get("severity"))
            if sev_name == "CRITICAL":
                c += 1
            elif sev_name == "HIGH":
                h += 1
        if c + h > 0:
            risky.append((-(c + h), result.get("skill_name", "unknown"), c, h))

    if risky:
        print("Risky skills:")
        for _, name, c, h in sorted(risky)[:5]:
            print(f"- {name}: critical={c}, high={h}")
PY
}

if [[ "$PROFILE" == "ci" ]]; then
  CMD=("${PYTHON_CMD[@]}" -m skill_scanner.cli.cli "$MODE" "$TARGET_ABS" "${PROFILE_ARGS[@]}")
  if [[ "$EXTRA_ARGS_COUNT" -gt 0 ]]; then
    CMD+=("${EXTRA_ARGS[@]}")
  fi
  "${CMD[@]}"
  exit 0
fi

filter_cascade_args

MIN_RANK="$(profile_rank "$PROFILE")"
CURRENT_STAGE="quick"
FINAL_STAGE=""
FINAL_JSON=""

while [[ -n "$CURRENT_STAGE" ]]; do
  STAGE_ARGS_STR="$(build_stage_args "$CURRENT_STAGE")"
  read -r -a STAGE_ARGS <<< "$STAGE_ARGS_STR"

  CMD=("${PYTHON_CMD[@]}" -m skill_scanner.cli.cli "$MODE" "$TARGET_ABS" "${STAGE_ARGS[@]}")
  if [[ "$CASCADE_ARGS_COUNT" -gt 0 ]]; then
    CMD+=("${CASCADE_ARGS[@]}")
  fi
  CMD+=(--format json --compact)

  echo "[workflow] Running stage: $CURRENT_STAGE"
  if ! STAGE_RAW="$("${CMD[@]}" 2>&1)"; then
    echo "$STAGE_RAW" >&2
    exit 1
  fi
  STAGE_JSON="$(extract_json_payload "$STAGE_RAW")"

  FINAL_STAGE="$CURRENT_STAGE"
  FINAL_JSON="$STAGE_JSON"

  IFS=$'\t' read -r TOTAL_FINDINGS HIGH_RISK CRITICAL_COUNT HIGH_COUNT MEDIUM_COUNT LOW_COUNT INFO_COUNT <<< "$(extract_metrics "$STAGE_JSON")"

  echo "[workflow] Stage $CURRENT_STAGE findings: total=$TOTAL_FINDINGS critical=$CRITICAL_COUNT high=$HIGH_COUNT medium=$MEDIUM_COUNT low=$LOW_COUNT info=$INFO_COUNT"

  CURRENT_RANK="$(profile_rank "$CURRENT_STAGE")"
  NEXT_STAGE="$(next_profile "$CURRENT_STAGE")"

  if [[ -z "$NEXT_STAGE" ]]; then
    break
  fi

  if [[ "$TOTAL_FINDINGS" -gt 0 || "$CURRENT_RANK" -lt "$MIN_RANK" ]]; then
    echo "[workflow] Escalating to: $NEXT_STAGE"
    CURRENT_STAGE="$NEXT_STAGE"
  else
    break
  fi
done

echo ""
print_conclusion "$FINAL_STAGE" "$FINAL_JSON"
