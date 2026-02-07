---
name: agent-scanner-skill
description: Security scanning and triage for local Agent Skills. Use this skill to audit SKILL packages, detect prompt-injection/data-exfiltration/tool-abuse risks, and produce concise risk conclusions with reasons.
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
- `quick`: starts quick stage, auto-escalates to `balanced` then `deep-agent` only if findings are detected.
- `balanced`: run at least through `balanced` (still starts with `quick`), escalates further on findings.
- `deep-agent`: run all three stages (`quick` -> `balanced` -> `deep-agent`) for maximum confidence.
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

4. Read final output.
- The wrapper prints a concise final decision:
  - `Conclusion`: `RISK CONFIRMED` / `NO HIGH-CONFIDENCE RISK` / `NO RISK FOUND`
  - `Reason`: final stage + severity counts + top evidence lines
- Default behavior does not write report files for manual review flows (`quick|balanced|deep-agent`).

5. Use `ci` when you need machine-readable artifacts.
- `ci` keeps SARIF + fail-on-findings behavior for pipelines.

## Runtime Notes

Default runtime mode is `embedded` (no network installs required).

- `SKILL_SCANNER_RUNTIME=embedded|venv` controls runtime strategy.
- `SKILL_SCANNER_PYTHON=python3` sets interpreter.
- `SKILL_SCANNER_INSTALL_WHEELS=1` makes `venv` mode install from `vendor/wheels/` only.

Security guardrail:
- Scanner-side external API analyzers have been removed from the codebase.
- Cascading review stays local without scanner external API network calls.

## Resources

- Scan presets and tuning: `references/scan-profiles.md`
- Triage and fix playbook: `references/remediation-playbook.md`
- Offline vendor notes: `vendor/README.md`
- Runtime setup helper: `scripts/install-scanner.sh`
- Optional wheelhouse builder: `scripts/build-vendor-wheelhouse.sh`
- Command wrapper: `scripts/run-scan.sh`
