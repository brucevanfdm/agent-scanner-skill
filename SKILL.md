---
name: claude-code-skill-scanner
description: Security scanning and threat triage for local Agent Skills (Claude Code, Codex, Cursor) using a self-contained offline bundle with embedded scanner source and vendor dependencies. Use when asked to audit a SKILL.md package, detect prompt injection/data exfiltration/tool abuse, compare quick vs deep scans, or produce JSON/SARIF reports for CI and remediation in network-restricted environments.
---

# Claude Code Skill Scanner

Use this skill to run security scans against Agent Skill packages.

The skill is self-contained: copy this skill directory into your Claude Code `skills/` directory. It includes:

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
- `deep`: add LLM + meta analyzer for semantic validation (API/provider key path).
- `deep-agent`: no standalone scanner LLM API call; produce JSON and hand off semantic review to Claude Code/Codex host agent.
- `ci`: SARIF output + fail-on-findings for pipelines.

3. Run the bundled wrapper.

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

5. Autonomous host-agent semantic review (`deep-agent`).
- Run `deep-agent` to generate:
  - JSON findings (default: `.runtime/host-agent-review.json`)
  - host-agent task prompt (default: `.runtime/host-agent-review-prompt.md`)
- Then instruct Claude Code/Codex to execute the generated prompt file and complete review + remediation autonomously.

Example:

```bash
./scripts/run-scan.sh scan ./my-skill deep-agent
```

Suggested instruction to Claude Code/Codex:

```text
请执行 .runtime/host-agent-review-prompt.md 中的任务，并直接完成代码修复与验证。
```

Autonomous execution template (copy/paste):

```text
1) 运行：
   ./scripts/run-scan.sh scan <目标skill目录> deep-agent
2) 读取：
   .runtime/host-agent-review-prompt.md
3) 严格按该提示完成：证据化复核 -> 高危优先修复 -> 命令验证 -> 输出变更摘要。
```

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
