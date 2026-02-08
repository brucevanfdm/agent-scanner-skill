---
name: agent-scanner-skill
description: Security scanning and triage for local Agent Skills. Use when the user wants to (1) audit/scan SKILL packages for security risks, (2) detect prompt-injection, data-exfiltration, tool-abuse, or code-execution vulnerabilities, (3) review skill safety before installation or deployment, (4) run security checks on skill code. Detects risks like AITech-1.1 (prompt injection), AITech-8.2 (data exfiltration), AITech-9.1 (command injection), AITech-4.3/12.1 (tool abuse).
---

# Agent Skill Scanner

Use this skill to scan Agent Skill packages for security risks.

This skill is self-contained and includes:

- scanner source: `skill_scanner/`
- vendor runtime modules: `vendor/python/`
- optional wheelhouse path: `vendor/wheels/`

Default `embedded` mode uses a compatibility `yara` shim for offline execution. Native YARA requires wheelhouse + native dependencies.

## Quick Start

Scan a single skill with default `balanced` profile:

```bash
./scripts/run-scan.sh scan ./my-skill
```

## Workflow

### 1. Choose scan scope

- Single skill: use `scan`
- Skill directory: use `scan-all`

### 2. Choose profile

| Profile | Behavior | Use when |
|---------|----------|----------|
| `quick` | Starts with quick checks, auto-escalates if findings detected | Fast initial check |
| `balanced` | Guarantees behavioral verification, escalates on findings | Default manual review |
| `deep-agent` | Full three-stage cascade (quick → balanced → deep-agent) | Maximum confidence |

### 3. Run scan

```bash
./scripts/run-scan.sh <scan|scan-all> <target_path> [profile] [extra args...]
```

Examples:

```bash
# Quick scan for rapid feedback
./scripts/run-scan.sh scan ./my-skill quick

# Balanced with strict YARA rules
./scripts/run-scan.sh scan ./my-skill balanced --yara-mode strict

# Deep scan for critical skills
./scripts/run-scan.sh scan ./my-skill deep-agent
```

### 4. Interpret results

The wrapper prints a concise conclusion:

- `Conclusion: RISK CONFIRMED` - Critical/High severity findings detected
- `Conclusion: NO HIGH-CONFIDENCE RISK` - Only Medium/Low/Info findings
- `Conclusion: NO RISK FOUND` - No findings detected

Output is printed to stdout by default. To write results to a file, use `--output results.json` or `--output results.md`.

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
- **Offline setup**: `vendor/README.md` — Read when user needs offline/air-gapped installation
- **Scripts**:
  - `scripts/run-scan.sh` — Main entry point (shown in Quick Start)
  - `scripts/install-scanner.sh` — Runtime setup helper
  - `scripts/build-vendor-wheelhouse.sh` — Build offline wheelhouse
