# Remediation Playbook

## Prioritize by Severity

1. `CRITICAL`: Fix immediately; block release.
2. `HIGH`: Fix before merge whenever possible.
3. `MEDIUM`: Address in current hardening cycle.
4. `LOW`/`INFO`: Track and resolve in backlog.

## Typical Finding Categories and Actions

- Prompt injection (`AITech-1.1`)
  - Remove instruction override/jailbreak text from `SKILL.md`.
  - Keep role instructions narrow and task-specific.

- Data exfiltration (`AITech-8.2`)
  - Remove secret reads (`os.environ`, credential files) unless strictly needed.
  - Do not send local data to untrusted endpoints.

- Command/code injection (`AITech-9.1`)
  - Replace `eval`/`exec` and dynamic shell composition with safe parsers.
  - Validate and constrain all user-controlled inputs.

- Tool abuse/capability inflation (`AITech-4.3` / `AITech-12.1`)
  - Narrow `description` and capability claims in frontmatter.
  - Ensure implementation behavior matches claimed scope.

## Verification Loop

1. Apply smallest safe patch.
2. Re-run `balanced` scan.
3. Re-run `deep` scan if used previously.
4. Confirm no new `CRITICAL`/`HIGH` findings were introduced.
