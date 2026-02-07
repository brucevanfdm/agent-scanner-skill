# Scan Profiles

## Runtime Modes

- `embedded` (default): runs bundled `skill_scanner` with `vendor/python` compatibility modules.
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
| `quick` | Starts with `--use-trigger`; auto-escalates on findings | Fast local checks with automatic re-check | Low -> Medium |
| `balanced` | Starts from `quick`, guarantees `--use-behavioral --use-trigger` stage | Default manual review with better confidence | Medium |
| `deep-agent` | Runs full cascade (`quick` -> `balanced` -> `deep-agent`) | Maximum confidence local review | Medium |
| `ci` | `--use-behavioral --use-trigger --format sarif --fail-on-findings` | CI gate with machine-readable output | Medium |

### Manual Flow Output (`quick|balanced|deep-agent`)

- Wrapper prints final:
  - `Conclusion`: whether risk is confirmed
  - `Reason`: final stage + severity counts + key findings
- By default no report file is written for manual flow.

If you pass `--output`/`--format` in manual flow, wrapper ignores them and still prints the final conclusion.

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
2. Use `balanced` when you want at least one behavioral verification pass.
3. Use `deep-agent` when you want full three-stage verification.
4. Use `ci` in pipelines with SARIF ingestion.

## Optional Analyzer Flags

- Rule tuning:
  - `--yara-mode strict|balanced|permissive`
  - `--custom-rules <dir>`
  - `--disable-rule <RULE_ID>` (repeatable)

Note: scanner-side external API analyzers were removed from codebase for security.

## Output Strategy

- Manual review (wrapper): use `quick|balanced|deep-agent` and read final `Conclusion` + `Reason`.
- Automation and post-processing: use `ci` with `--output results.sarif`, or call `skill_scanner.cli.cli` directly for custom JSON/table output.
