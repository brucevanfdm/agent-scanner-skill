---
name: agent-scanner-skill
description: Security scanning and triage for local Agent Skills. Use this skill to audit SKILL packages, detect prompt-injection/data-exfiltration/tool-abuse risks, and generate JSON/SARIF outputs for CI.
---

# Agent Skill Scanner

Use this skill to scan Agent Skill packages for security risks.

This skill is self-contained and includes:

- scanner source: `skill_scanner/`
- vendor runtime modules: `vendor/python/`
- optional wheelhouse path: `vendor/wheels/`

Default `embedded` mode uses a compatibility `yara` shim for offline execution. Native YARA requires wheelhouse + native dependencies.

## Workflow

1. Resolve scan scope.
- Single skill: `scan`
- Skill directory: `scan-all`

2. Choose a profile.
- `quick`: static + trigger checks, fast feedback.
- `balanced`: add behavioral analysis for dataflow risks.
- `deep-agent`: no standalone scanner external API call; output JSON and hand off semantic review to host agent.
- `ci`: SARIF output + fail-on-findings for pipelines.

3. Run the wrapper.

```bash
./scripts/run-scan.sh <scan|scan-all> <target_path> [quick|balanced|deep-agent|ci] [extra skill-scanner args...]
```

Examples:

```bash
./scripts/run-scan.sh scan ./my-skill quick
./scripts/run-scan.sh scan ./my-skill balanced --yara-mode strict
./scripts/run-scan.sh scan ./my-skill deep-agent
./scripts/run-scan.sh scan-all ./skills ci --recursive --output results.sarif
```

4. Report results with actionability.
- Always include severity counts.
- Highlight `CRITICAL` and `HIGH` findings first.
- Add concrete remediation steps per finding category.

5. Host-agent semantic review (`deep-agent`).
- `deep-agent` generates:
  - JSON findings: `.runtime/host-agent-review.json` (default)
  - task prompt: `.runtime/host-agent-review-prompt.md` (default)
- Execute the generated prompt with your host agent for evidence-based remediation.

## Runtime Notes

Default runtime mode is `embedded` (no network installs required).

- `SKILL_SCANNER_RUNTIME=embedded|venv` controls runtime strategy.
- `SKILL_SCANNER_PYTHON=python3` sets interpreter.
- `SKILL_SCANNER_INSTALL_WHEELS=1` makes `venv` mode install from `vendor/wheels/` only.

Security guardrail:
- Scanner-side external API analyzers have been removed from the codebase.
- Use `deep-agent` for semantic review without scanner external API network calls.

## Resources

- Scan presets and tuning: `references/scan-profiles.md`
- Triage and fix playbook: `references/remediation-playbook.md`
- Offline vendor notes: `vendor/README.md`
- Runtime setup helper: `scripts/install-scanner.sh`
- Optional wheelhouse builder: `scripts/build-vendor-wheelhouse.sh`
- Command wrapper: `scripts/run-scan.sh`
