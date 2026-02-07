# Scan Profiles

## Runtime Modes

- `embedded` (default): runs bundled `embedded/skill_scanner` with `vendor/python` compatibility modules.
- `embedded` mode includes a `yara` compatibility shim (native YARA matching disabled).
- `venv`: runs inside `.runtime/venv`; optionally installs from local wheelhouse only.

Set with:

```bash
export SKILL_SCANNER_RUNTIME=embedded
# or
export SKILL_SCANNER_RUNTIME=venv
```

## Profile Matrix

| Profile | Flags | Best for | Cost |
|---|---|---|---|
| `quick` | `--use-trigger` | Fast local checks during edits | Low |
| `balanced` | `--use-behavioral --use-trigger` | Default manual review | Medium |
| `deep` | `--use-behavioral --use-trigger --use-llm --enable-meta` | High-confidence audit before release | High |
| `deep-agent` | `--use-behavioral --use-trigger --format json` | No standalone scanner LLM API; hand off semantic review to Claude Code/Codex | Medium |
| `ci` | `--use-behavioral --use-trigger --format sarif --fail-on-findings` | CI gate with machine-readable output | Medium |

### deep-agent Outputs

When using `deep-agent`, wrapper emits:

- JSON report (default): `.runtime/host-agent-review.json`
- Host-agent task prompt (default): `.runtime/host-agent-review-prompt.md`

If you pass `--output`, the prompt file automatically points to that JSON path.

## Optional Wheelhouse

If you need native packages (for example `yara-python`), prebuild wheels on a connected machine:

```bash
./scripts/build-vendor-wheelhouse.sh
```

Then in offline environment:

```bash
export SKILL_SCANNER_RUNTIME=venv
export SKILL_SCANNER_INSTALL_WHEELS=1
./scripts/run-scan.sh scan ./my-skill balanced
```

## Recommended Flow

1. Start with `quick` while iterating.
2. Run `balanced` before declaring remediation complete.
3. Use `deep` when scanner-side LLM API access is available and risk is high.
4. Use `deep-agent` when you want Claude Code/Codex host agent to do semantic review without separate scanner LLM key setup.
5. Use `ci` in pipelines with SARIF ingestion.

For `deep-agent`, after scan completion ask your host agent to execute the generated prompt file directly.

## Optional Analyzer Flags

- VirusTotal:
  - `--use-virustotal`
  - Optional: `--vt-api-key <key>`, `--vt-upload-files`
- Cisco AI Defense:
  - `--use-aidefense`
  - Optional: `--aidefense-api-key <key>`, `--aidefense-api-url <url>`
- Rule tuning:
  - `--yara-mode strict|balanced|permissive`
  - `--custom-rules <dir>`
  - `--disable-rule <RULE_ID>` (repeatable)

## Output Strategy

- Human review: `--format summary` or `--format table`
- Automation and post-processing: `--format json`
- GitHub code scanning: `--format sarif --output results.sarif`
