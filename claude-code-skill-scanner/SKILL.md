---
name: claude-code-skill-scanner
description: Security scanning and threat triage for local Agent Skills (Claude Code, Codex, Cursor) using a self-contained offline bundle with embedded scanner source and vendor dependencies. Use when asked to audit a SKILL.md package, detect prompt injection/data exfiltration/tool abuse, compare quick vs deep scans, or produce JSON/SARIF reports for CI and remediation in network-restricted environments.
---

# Claude Code Skill Scanner

Use this skill to run security scans against Agent Skill packages.

The skill is self-contained: copy the `claude-code-skill-scanner/` directory into your Claude Code `skills/` directory. It includes:

- embedded scanner source: `embedded/skill_scanner/`
- vendor runtime modules: `vendor/python/`
- optional wheelhouse path: `vendor/wheels/`

Note: default embedded mode uses a compatibility `yara` shim for offline execution, so native YARA matching is not enabled unless you run with wheelhouse + native dependencies.

## Workflow

1. Resolve scan scope.
- Scan one skill: use `scan` mode.
- Scan a folder of skills: use `scan-all` mode.

2. Choose a profile.
- `quick`: static + trigger checks, fast feedback.
- `balanced`: add behavioral analysis for dataflow risks.
- `deep`: add LLM + meta analyzer for semantic validation.
- `ci`: SARIF output + fail-on-findings for pipelines.

3. Run the bundled wrapper.

```bash
./scripts/run-scan.sh <scan|scan-all> <target_path> [quick|balanced|deep|ci] [extra skill-scanner args...]
```

Examples:

```bash
./scripts/run-scan.sh scan ./my-skill quick
./scripts/run-scan.sh scan ./my-skill balanced --yara-mode strict
./scripts/run-scan.sh scan ./my-skill deep
./scripts/run-scan.sh scan-all ./skills ci --recursive --output results.sarif
```

4. Report results with actionability.
- Always include severity counts.
- Highlight `CRITICAL` and `HIGH` findings first.
- Add concrete remediation steps per finding category.

## Runtime Notes

Default runtime mode is `embedded` (no network installs required).

- `SKILL_SCANNER_RUNTIME=embedded|venv` controls runtime strategy.
- `SKILL_SCANNER_PYTHON=python3` sets interpreter.
- `SKILL_SCANNER_INSTALL_WHEELS=1` makes `venv` mode install from `vendor/wheels/` only.

Analyzer key env vars (when corresponding analyzers are enabled):

- `SKILL_SCANNER_LLM_API_KEY` / `SKILL_SCANNER_LLM_MODEL`
- `VIRUSTOTAL_API_KEY`
- `AI_DEFENSE_API_KEY`

## Resources

- Scan presets and tuning: `references/scan-profiles.md`
- Triage and fix playbook: `references/remediation-playbook.md`
- Offline vendor notes: `vendor/README.md`
- Runtime setup helper: `scripts/install-scanner.sh`
- Optional wheelhouse builder: `scripts/build-vendor-wheelhouse.sh`
- Command wrapper: `scripts/run-scan.sh`
