# Agent Skill Scanner

[English](README.md) | [中文](README_CN.md)

A security scanner for Agent Skills packages that detects prompt injection, data exfiltration, tool abuse, and other AI-specific threats.

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

## Overview

Agent Skill Scanner is a specialized security tool designed to audit AI Agent Skill packages (OpenAI Codex, Cursor Agent Skills, and compatible formats). It performs static analysis to identify security risks before skills are deployed to production environments.

### Key Features

- **Offline-First Design** - Runs completely locally with no network dependencies
- **Cascade Scanning** - Progressive analysis (quick → balanced → deep) that escalates based on findings
- **80+ Security Patterns** - Detects threats across 12+ categories aligned with AITech Taxonomy
- **Multiple Output Formats** - Summary, JSON, Markdown, Table, and SARIF for CI/CD integration
- **Cross-Skill Analysis** - Detects trigger hijacking and description overlap between skills
- **Extensible Architecture** - Plugin-based analyzers with YARA rule support

## Threat Categories

| Category | AITech Code | Description |
|----------|-------------|-------------|
| Prompt Injection | AITech-1.1 | Direct attempts to override system instructions |
| Indirect Injection | AITech-1.2 | Malicious instructions from external sources |
| Command Injection | AITech-9.1.4 | SQL injection, command execution, XSS |
| Data Exfiltration | AITech-8.2 | Unauthorized data exposure via tooling |
| Tool Chaining Abuse | AITech-8.2.3 | Suspicious multi-step data extraction |
| Hardcoded Secrets | AITech-8.2.1 | API keys, credentials in code |
| Obfuscation | AITech-9.1.3 | Code obfuscation techniques |
| Resource Abuse | AITech-13.1 | Fork bombs, infinite loops, DoS |
| Social Engineering | AITech-15.1 | Misleading metadata, brand impersonation |
| Trigger Hijacking | AITech-4.3.5 | Overly broad skill descriptions |

## Installation

### Option 1: Run as a Skill (Embedded Mode)

The scanner includes its own Python runtime and requires no installation:

```bash
# Clone the repository
git clone https://github.com/yourusername/agent-scanner-skill.git
cd agent-scanner-skill

# Run directly using the wrapper script
./scripts/run-scan.sh scan /path/to/skill quick
```

### Option 2: Install as Python Package

```bash
# Install from source
pip install -e .

# Or install from PyPI (when published)
pip install agent-scanner-skill
```

## Quick Start

### Scan a Single Skill

```bash
skill-scanner scan /path/to/skill
```

### Scan Multiple Skills

```bash
skill-scanner scan-all /path/to/skills --recursive
```

### Scan with Cascade Profiles

```bash
# Quick scan (auto-escalates on findings)
./scripts/run-scan.sh scan ./my-skill quick

# Balanced scan (includes quick + deeper analysis)
./scripts/run-scan.sh scan ./my-skill balanced

# Deep scan (maximum coverage)
./scripts/run-scan.sh scan ./my-skill deep-agent

# CI profile (SARIF + fail-on-findings)
./scripts/run-scan.sh scan-all ./skills ci --output results.sarif
```

## Usage Examples

### Basic Security Scan

```bash
skill-scanner scan ./my-skill --format summary
```

### JSON Output for Automation

```bash
skill-scanner scan ./my-skill --format json --output report.json
```

### SARIF for GitHub Code Scanning

```bash
skill-scanner scan-all ./skills --format sarif --output results.sarif
```

### Enable Behavioral Analysis

```bash
skill-scanner scan ./my-skill --use-behavioral
```

### Scan with Custom YARA Rules

```bash
skill-scanner scan ./my-skill --custom-rules ./my-rules/
```

### CI/CD Integration

```bash
# Exit with error code if critical/high findings found
skill-scanner scan ./my-skill --fail-on-findings
```

## CLI Reference

### Commands

| Command | Description |
|---------|-------------|
| `scan <dir>` | Scan a single skill package |
| `scan-all <dir>` | Scan all skills in a directory |
| `list-analyzers` | List available analyzers |
| `validate-rules` | Validate rule signatures |

### Options

| Option | Description |
|--------|-------------|
| `--format` | Output format: summary, json, markdown, table, sarif |
| `--output, -o` | Write report to file |
| `--detailed` | Include detailed findings |
| `--recursive, -r` | Recursively search for skills |
| `--use-behavioral` | Enable behavioral dataflow analysis |
| `--use-trigger` | Enable trigger specificity analysis |
| `--yara-mode` | YARA mode: strict, balanced, permissive |
| `--custom-rules` | Path to custom YARA rules |
| `--disable-rule` | Disable specific rule (can be repeated) |
| `--fail-on-findings` | Exit with error if critical/high findings |
| `--check-overlap` | Check for description overlap between skills |

## Output Formats

### Summary

```
============================================================
Skill: my-skill
============================================================
Status: [FAIL] ISSUES FOUND
Max Severity: HIGH
Total Findings: 3
Scan Duration: 1.23s

Findings Summary:
  Critical: 1
  High:     1
  Medium:   1
  Low:      0
  Info:     0
```

### JSON

```json
{
  "skill_name": "my-skill",
  "is_safe": false,
  "max_severity": "HIGH",
  "findings": [...]
}
```

### SARIF

Compatible with GitHub Advanced Security, Azure DevOps, and other SARIF-consuming tools.

## Architecture

### Analyzers

1. **StaticAnalyzer** (default)
   - Pattern-based detection using YAML rules
   - YARA-compatible rule engine
   - 80+ security signatures

2. **BehavioralAnalyzer**
   - Static dataflow analysis
   - AST-based taint tracking
   - Multi-file correlation

3. **TriggerAnalyzer**
   - Description specificity analysis
   - Keyword baiting detection
   - Trigger hijacking risks

### Project Structure

```
agent-scanner-skill/
├── skill_scanner/           # Core scanner code
│   ├── core/
│   │   ├── analyzers/       # Analysis engines
│   │   ├── models.py        # Data models
│   │   ├── scanner.py       # Main scanner
│   │   └── reporters/       # Output formatters
│   ├── data/
│   │   └── rules/           # Security signatures
│   ├── threats/             # Threat taxonomy
│   └── cli/                 # Command-line interface
├── scripts/                 # Utility scripts
├── vendor/                  # Python runtime
├── references/              # Documentation
└── agents/                  # Agent configurations
```

## Contributing

Contributions are welcome! Please see our contributing guidelines for details.

### Adding Custom Rules

Create YARA rule files in your custom rules directory:

```yaml
# custom-rules/my-rule.yaml
- id: MY_CUSTOM_RULE
  category: command_injection
  severity: HIGH
  patterns:
    - "dangerous_pattern"
  file_types: [python, bash]
  description: "My custom security check"
  remediation: "How to fix this issue"
```

### Development Setup

```bash
# Clone repository
git clone https://github.com/yourusername/agent-scanner-skill.git
cd agent-scanner-skill

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e .

# Run tests
pytest
```

## Documentation

- [Scan Profiles](references/scan-profiles.md) - Pre-configured scanning profiles
- [Remediation Playbook](references/remediation-playbook.md) - How to fix findings
- [Threat Taxonomy](skill_scanner/threats/threats.py) - AITech classification reference
- [Vendor Runtime](vendor/README.md) - Offline runtime setup

## License

Copyright 2026 Cisco Systems, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

SPDX-License-Identifier: Apache-2.0

## Security

For security vulnerabilities, please follow our [security policy](SECURITY.md).

## Acknowledgments

Built with AITech Taxonomy for standardized threat classification.
Compatible with OpenAI Codex and Cursor Agent Skills formats.
