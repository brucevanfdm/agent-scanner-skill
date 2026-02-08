# Scan Profiles Reference

Detailed configuration options for the scanner.

## Runtime Modes

| Mode | Description | Use case |
|------|-------------|----------|
| `embedded` (default) | Uses bundled `skill_scanner` with `vendor/python` compatibility shims | Default, no setup needed |
| `venv` | Runs in `.runtime/venv` with optional wheelhouse | Need native packages like `yara-python` |

## Profile Details

### quick
- **Flags**: `--use-trigger`
- **Behavior**: Fast pattern matching, auto-escalates on findings
- **Best for**: Initial rapid screening during development

### balanced
- **Flags**: `--use-behavioral --use-trigger`
- **Behavior**: Adds behavioral analysis, escalates on findings
- **Best for**: Pre-commit review, default manual checks

### deep-agent
- **Flags**: `--use-behavioral --use-trigger --use-deep-agent`
- **Behavior**: Runs all analyzers and generates semantic review guide
- **Best for**: Critical skills, pre-release validation
- **Output**: Lists high-risk files that Claude Code should manually review

The deep-agent profile adds **semantic analysis guidance**:
- Identifies files with suspicious pattern combinations
- Generates prioritized review list with risk scores
- Flags cross-file data flow concerns
- Guides Claude to read and analyze specific files

See [deep-agent-guide.md](deep-agent-guide.md) for the review workflow.

## Optional Flags

```bash
# Rule strictness
--yara-mode strict|balanced|permissive

# Custom rules
--custom-rules <directory>

# Disable specific rules
--disable-rule <RULE_ID>
```

## Offline Wheelhouse Setup

For air-gapped environments:

```bash
# On connected machine
./scripts/build-vendor-wheelhouse.sh

# On offline machine
export SKILL_SCANNER_RUNTIME=venv
export SKILL_SCANNER_INSTALL_WHEELS=1
./scripts/run-scan.sh scan ./my-skill balanced
```

## Output Options

| Use case | Command |
|----------|---------|
| Human review | `quick|balanced|deep-agent` (prints conclusion to stdout) |
| File output | Add `--output results.json` or `--output results.md` |
| Custom processing | Call `python -m skill_scanner.cli.cli` directly with `--format json` |
