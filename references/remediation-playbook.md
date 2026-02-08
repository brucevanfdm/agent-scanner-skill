# Remediation Playbook

**Read this when**: The scanner reports findings and you need guidance on how to fix them.

## Severity Priority

| Severity | Action |
|----------|--------|
| `CRITICAL` | Fix immediately; block release |
| `HIGH` | Fix before merge whenever possible |
| `MEDIUM` | Address in current hardening cycle |
| `LOW`/`INFO` | Track and resolve in backlog |

## Finding Categories

### Prompt Injection (AITech-1.1)
- Remove instruction override/jailbreak text from `SKILL.md`
- Keep role instructions narrow and task-specific
- Avoid phrases like "ignore previous instructions" or "DAN mode"

### Data Exfiltration (AITech-8.2)
- Remove secret reads (`os.environ`, credential files) unless strictly needed
- Do not send local data to untrusted endpoints
- Validate any network calls are to expected destinations

### Command/Code Injection (AITech-9.1)
- Replace `eval`/`exec` with safe parsers (ast.literal_eval, json.loads)
- Avoid dynamic shell composition with user input
- Validate and constrain all user-controlled inputs

### Tool Abuse / Capability Inflation (AITech-4.3 / AITech-12.1)
- Narrow `description` in SKILL.md frontmatter to match actual capabilities
- Remove overbroad triggering conditions
- Ensure implementation behavior matches claimed scope

## Verification Loop

After applying fixes:

1. Apply smallest safe patch
2. Re-run `balanced` scan: `./scripts/run-scan.sh scan ./my-skill balanced`
3. Re-run `deep-agent` if semantic changes were made
4. Confirm no new `CRITICAL`/`HIGH` findings
