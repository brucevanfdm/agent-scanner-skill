---
name: agent-scanner-skill
description: Security scanning and triage for local Agent Skills. Use when the user wants to audit/scan SKILL packages for security risks, detect prompt-injection/data-exfiltration/tool-abuse/code-execution vulnerabilities, review skill safety before installation or deployment, or run security checks on skill code. Detects AITech-1.1 (prompt injection), AITech-8.2 (data exfiltration), AITech-9.1 (command injection), AITech-4.3/12.1 (tool abuse).
---

# Agent Skill Scanner

Use this skill to scan Agent Skill packages for security risks.

## CRITICAL: When DEEP_AGENT Findings Appear

When the scanner outputs `DEEP_AGENT_REVIEW_GUIDE` or `DEEP_AGENT_FILE_REVIEW` findings, you MUST:

1. Read each flagged file using the Read tool
2. Analyze whether the code behavior matches its claimed purpose
3. Check if risky operations are properly guarded
4. **Distinguish real risks from false positives**

This is REQUIRED for deep-agent profile scans — the scanner identifies suspicious patterns but cannot determine intent. Your job is to verify which findings represent actual security concerns.

**Final report format**: After manual review, tell the user clearly:
- ✅ "This skill is safe to use" (if no real risks found)
- ⚠️ "This skill has [X] security issue(s) that should be fixed" (with specific issues)

Do NOT report potential/uncertain findings as confirmed risks.

---

## Quick Start

Scan a single skill with default `balanced` profile:

```bash
bash /path/to/skill/scripts/run-scan.sh scan /path/to/target-skill
```

This skill is self-contained with:
- Scanner source: `skill_scanner/`
- Vendor runtime modules: `vendor/python/`
- Optional wheelhouse: `vendor/wheels/`

Default `embedded` mode uses a compatibility `yara` shim for offline execution.

## Workflow

### 1. Choose scan scope

- Single skill: use `scan`
- Skill directory: use `scan-all`

### 2. Choose profile

| Profile | Behavior | Use when |
|---------|----------|----------|
| `quick` | Pattern-based trigger analysis only | Fast initial check |
| `balanced` | Adds behavioral dataflow analysis | Default manual review |
| `deep-agent` | Adds semantic review guide generation | Maximum confidence, requires reading flagged files |

### 3. Run scan

```bash
./scripts/run-scan.sh <scan|scan-all> <target_path> [profile] [extra args...]
```

Examples:

```bash
# Quick scan for rapid feedback
bash /path/to/skill/scripts/run-scan.sh scan /path/to/target-skill quick

# Balanced with strict YARA rules
bash /path/to/skill/scripts/run-scan.sh scan /path/to/target-skill balanced --yara-mode strict

# Deep scan for critical skills
bash /path/to/skill/scripts/run-scan.sh scan /path/to/target-skill deep-agent

# Scan all skills in a directory
bash /path/to/skill/scripts/run-scan.sh scan-all /path/to/skills-directory deep-agent
```

### 4. Interpret results

The wrapper prints a user-friendly conclusion:

- `Conclusion: RISK CONFIRMED` - The skill has confirmed security issues that should be fixed before use
- `Conclusion: NO HIGH-CONFIDENCE RISK` - No critical risks found, but some minor issues were detected
- `Conclusion: NO RISK FOUND` - No security issues detected

**Important**: The scanner may produce false positives. When `DEEP_AGENT_REVIEW_GUIDE` or `DEEP_AGENT_FILE_REVIEW` findings appear, you MUST read the flagged files to verify whether they represent real risks or benign patterns.

Your final report to the user should:
1. State clearly whether the skill is safe to use
2. List only **confirmed** security issues (not potential/uncertain findings)
3. Explain any false positives you identified during manual review

For detailed deep-agent review workflow, see [references/deep-agent-guide.md](references/deep-agent-guide.md).

## Runtime Configuration

Default mode is `embedded` (no network installs required).

| Variable | Values | Description |
|----------|--------|-------------|
| `SKILL_SCANNER_RUNTIME` | `embedded` (default), `venv` | Runtime strategy |
| `SKILL_SCANNER_PYTHON` | `python3` | Python interpreter |
| `SKILL_SCANNER_INSTALL_WHEELS` | `0` (default), `1` | Install from `vendor/wheels/` only |

Security note: Scanner operates entirely offline. External API analyzers have been removed to ensure no network calls during scanning.

## Resources

Read these references when needed:

- **Scan profiles and tuning**: [references/scan-profiles.md](references/scan-profiles.md) — Read when user needs custom profiles, YARA tuning, or output format options
- **Remediation guidance**: [references/remediation-playbook.md](references/remediation-playbook.md) — Read when findings exist and user asks how to fix them
- **Deep agent review**: [references/deep-agent-guide.md](references/deep-agent-guide.md) — Read when `deep-agent` profile flags files for semantic review
- **Offline setup**: `vendor/README.md` — Read when user needs offline/air-gapped installation
- **Scripts**:
  - `scripts/run-scan.sh` — Main entry point (use `bash /path/to/skill/scripts/run-scan.sh ...`)
  - `scripts/install-scanner.sh` — Runtime setup helper
  - `scripts/build-vendor-wheelhouse.sh` — Build offline wheelhouse
