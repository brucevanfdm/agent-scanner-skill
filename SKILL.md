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
- `deep`: add LLM + meta analyzer for semantic validation (API/provider key path).
- `deep-agent`: no standalone scanner LLM API call; output JSON and hand off semantic review to host agent.
- `ci`: SARIF output + fail-on-findings for pipelines.

3. Run the wrapper.

```bash
./scripts/run-scan.sh <scan|scan-all> <target_path> [quick|balanced|deep|deep-agent|ci] [extra skill-scanner args...]
```

Examples:

```bash
./scripts/run-scan.sh scan ./my-skill quick
./scripts/run-scan.sh scan ./my-skill balanced --yara-mode strict
./scripts/run-scan.sh scan ./my-skill deep
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

Analyzer key env vars (when corresponding analyzers are enabled):

- `SKILL_SCANNER_LLM_API_KEY` / `SKILL_SCANNER_LLM_MODEL`
  (optional if host/provider env key already exists; scanner also auto-detects
  `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `AZURE_OPENAI_API_KEY`, `OPENROUTER_API_KEY`)
- `VIRUSTOTAL_API_KEY`
- `AI_DEFENSE_API_KEY`

For strict mode (disable provider-env fallback), set:
- `SKILL_SCANNER_ALLOW_PROVIDER_ENV_FALLBACK=0`

## Resources

- Scan presets and tuning: `references/scan-profiles.md`
- Triage and fix playbook: `references/remediation-playbook.md`
- Offline vendor notes: `vendor/README.md`
- Runtime setup helper: `scripts/install-scanner.sh`
- Optional wheelhouse builder: `scripts/build-vendor-wheelhouse.sh`
- Command wrapper: `scripts/run-scan.sh`
