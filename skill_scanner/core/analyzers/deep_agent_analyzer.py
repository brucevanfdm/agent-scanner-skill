# Copyright 2026 Cisco Systems, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

"""
Deep Agent analyzer for semantic security review.

This analyzer performs preparatory analysis to guide Claude Code through
a manual semantic review of skill files. It identifies:
1. High-risk files requiring careful review
2. Suspicious patterns that need semantic context
3. Cross-file relationships that may indicate complex threats

The output is a "Review Guide" that Claude Code uses to systematically
review each flagged file.
"""

import hashlib
import re
from pathlib import Path
from typing import Any

from ...core.models import Finding, Severity, Skill, ThreatCategory
from .base import BaseAnalyzer


class DeepAgentAnalyzer(BaseAnalyzer):
    """
    Deep semantic analyzer that prepares a review guide for Claude Code.

    Unlike static pattern matching, this analyzer identifies files and patterns
    that require semantic understanding to properly assess risk. The output
    guides Claude through a systematic manual review.
    """

    # Risk indicators that flag a file for manual review
    HIGH_RISK_PATTERNS = {
        "network": [
            r"requests\.(get|post|put|delete|patch)",
            r"urllib\.(request|urlopen)",
            r"http\.client",
            r"httpx\.",
            r"aiohttp",
            r"socket\.connect",
            r"websocket",
            r"curl\s+",
            r"wget\s+",
        ],
        "code_execution": [
            r"eval\s*\(",
            r"exec\s*\(",
            r"compile\s*\(",
            r"__import__\s*\(",
            r"importlib",
            r"subprocess\.\w+",
            r"os\.system",
            r"os\.popen",
        ],
        "data_access": [
            r"os\.environ",
            r"os\.getenv",
            r"open\s*\([^)]*['\"]r",
            r"pathlib.*read_text",
            r"json\.load",
            r"yaml\.safe_load|yaml\.load",
        ],
        "dynamic_behavior": [
            r"getattr\s*\(",
            r"setattr\s*\(",
            r"hasattr\s*\(",
            r"globals\s*\(\s*\)",
            r"locals\s*\(\s*\)",
            r"@\w+\.(before|after|hook)",
        ],
        "encoding_obfuscation": [
            r"base64\.(b64encode|b64decode|encode|decode)",
            r"binascii",
            r"zlib\.(compress|decompress)",
            r"\.encode\s*\(\s*['\"]rot13",
            r"codecs\.decode",
        ],
    }

    # Context patterns that increase suspicion
    SUSPICIOUS_COMBINATIONS = [
        ("network", "data_access"),
        ("network", "encoding_obfuscation"),
        ("code_execution", "data_access"),
        ("code_execution", "network"),
        ("dynamic_behavior", "network"),
    ]

    def __init__(self):
        """Initialize deep agent analyzer."""
        super().__init__("deep_agent_analyzer")
        self._compiled_patterns = self._compile_patterns()

    def _compile_patterns(self) -> dict[str, list[re.Pattern]]:
        """Compile regex patterns for efficiency."""
        compiled = {}
        for category, patterns in self.HIGH_RISK_PATTERNS.items():
            compiled[category] = [re.compile(p, re.IGNORECASE) for p in patterns]
        return compiled

    def analyze(self, skill: Skill) -> list[Finding]:
        """
        Analyze skill and generate review guide findings.

        This doesn't perform semantic analysis itself - it identifies files
        that need semantic review and creates a guide for Claude Code.

        Args:
            skill: Skill to analyze

        Returns:
            List of findings containing review guide information
        """
        findings = []

        # Analyze each file for risk indicators
        file_risks = self._analyze_files(skill)

        # Generate review guide findings
        findings.extend(self._generate_review_guide(skill, file_risks))

        # Identify cross-file concerns
        findings.extend(self._analyze_cross_file_concerns(skill, file_risks))

        return findings

    def _analyze_files(self, skill: Skill) -> dict[str, dict[str, Any]]:
        """
        Analyze each file for risk indicators.

        Returns:
            Dict mapping file_path -> risk assessment
        """
        file_risks = {}

        for skill_file in skill.files:
            if skill_file.file_type not in ("python", "bash", "markdown"):
                continue

            content = skill_file.read_content()
            if not content:
                continue

            risks = self._assess_file_risks(skill_file.relative_path, content)
            if risks["risk_score"] > 0:
                file_risks[skill_file.relative_path] = risks

        return file_risks

    def _assess_file_risks(self, file_path: str, content: str) -> dict[str, Any]:
        """
        Assess risk level of a single file.

        Returns:
            Risk assessment dict with categories, score, and review notes
        """
        risks = {
            "file_path": file_path,
            "categories": {},
            "risk_score": 0,
            "line_count": len(content.splitlines()),
            "review_notes": [],
        }

        # Check each risk category
        for category, patterns in self._compiled_patterns.items():
            matches = []
            for pattern in patterns:
                for match in pattern.finditer(content):
                    line_num = content[: match.start()].count("\n") + 1
                    line_content = content.split("\n")[line_num - 1] if content else ""
                    matches.append({
                        "line": line_num,
                        "pattern": pattern.pattern,
                        "context": line_content.strip()[:100],
                    })

            if matches:
                risks["categories"][category] = matches
                # Score based on category severity
                category_scores = {
                    "code_execution": 3,
                    "network": 2,
                    "data_access": 1,
                    "dynamic_behavior": 2,
                    "encoding_obfuscation": 2,
                }
                risks["risk_score"] += len(matches) * category_scores.get(category, 1)

        # Check for suspicious combinations
        found_categories = set(risks["categories"].keys())
        for combo in self.SUSPICIOUS_COMBINATIONS:
            if combo[0] in found_categories and combo[1] in found_categories:
                risks["risk_score"] += 5
                risks["review_notes"].append(
                    f"Suspicious combination: {combo[0]} + {combo[1]}"
                )

        # Special checks for SKILL.md
        if file_path == "SKILL.md" or file_path.endswith("SKILL.md"):
            risks["review_notes"].extend(self._check_skill_md_concerns(content))

        return risks

    def _check_skill_md_concerns(self, content: str) -> list[str]:
        """Check SKILL.md for concerns requiring semantic review."""
        notes = []

        # Check for instruction override patterns
        instruction_patterns = [
            r"ignore\s+(all\s+)?previous\s+instructions",
            r"disregard\s+(all\s+)?prior",
            r"you\s+are\s+now\s+a\s+\w+",
            r"your\s+new\s+role\s+is",
            r"act\s+as\s+(if\s+)?you\s+are",
            r"pretend\s+to\s+be",
        ]

        for pattern in instruction_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                notes.append(f"Potential instruction override pattern: {pattern}")

        # Check for excessive capability claims
        capability_words = ["all", "any", "everything", "anything", "unlimited", "infinite"]
        capability_count = sum(
            1 for word in capability_words
            if re.search(rf"\b{word}\b", content, re.IGNORECASE)
        )
        if capability_count >= 3:
            notes.append(f"Excessive capability claims ({capability_count} vague terms)")

        # Check for hidden/obfuscated content
        if "<!--" in content and "-->" in content:
            notes.append("Contains HTML comments - verify no hidden instructions")

        # Check for excessive backticks (potential code injection)
        backtick_count = content.count("```")
        if backtick_count > 10:
            notes.append(f"Many code blocks ({backtick_count//2}) - review for injection")

        return notes

    def _generate_review_guide(self, skill: Skill, file_risks: dict) -> list[Finding]:
        """Generate review guide findings for Claude Code."""
        findings = []

        if not file_risks:
            return findings

        # Sort files by risk score
        sorted_files = sorted(
            file_risks.items(),
            key=lambda x: x[1]["risk_score"],
            reverse=True
        )

        # Generate overall review guide
        high_risk_files = [
            (path, info) for path, info in sorted_files
            if info["risk_score"] >= 5
        ]
        medium_risk_files = [
            (path, info) for path, info in sorted_files
            if 2 <= info["risk_score"] < 5
        ]

        if high_risk_files:
            review_list = "\n".join([
                f"  {i+1}. [{info['risk_score']} pts] {path}"
                f"  ({', '.join(info['categories'].keys())})"
                for i, (path, info) in enumerate(high_risk_files[:5])
            ])

            findings.append(
                Finding(
                    id=self._generate_id("DEEP_REVIEW_GUIDE", skill.name),
                    rule_id="DEEP_AGENT_REVIEW_GUIDE",
                    category=ThreatCategory.POLICY_VIOLATION,
                    severity=Severity.INFO,
                    title=f"Deep Agent Review: {len(high_risk_files)} high-risk files need semantic review",
                    description=(
                        f"This skill requires manual semantic review. "
                        f"{len(high_risk_files)} files flagged with high-risk patterns.\n\n"
                        f"Priority review order:\n{review_list}\n\n"
                        f"Review each file for:\n"
                        f"- Intent: Does the code do what it claims?\n"
                        f"- Safety: Are risky operations properly guarded?\n"
                        f"- Context: Do patterns combine to create vulnerabilities?"
                    ),
                    file_path="REVIEW_GUIDE",
                    remediation="Follow the deep-agent review workflow in references/deep-agent-guide.md",
                    analyzer="deep_agent",
                    metadata={
                        "high_risk_count": len(high_risk_files),
                        "medium_risk_count": len(medium_risk_files),
                        "files": [path for path, _ in sorted_files],
                    },
                )
            )

        # Generate per-file review findings
        for file_path, info in high_risk_files[:3]:  # Top 3 for detailed review
            category_details = "\n".join([
                f"    - {cat}: {len(matches)} matches"
                for cat, matches in info["categories"].items()
            ])

            notes = "\n".join([
                f"  - {note}"
                for note in info["review_notes"]
            ]) if info["review_notes"] else "  None"

            findings.append(
                Finding(
                    id=self._generate_id("DEEP_FILE_REVIEW", file_path),
                    rule_id="DEEP_AGENT_FILE_REVIEW",
                    category=ThreatCategory.POLICY_VIOLATION,
                    severity=Severity.INFO,
                    title=f"Review required: {file_path}",
                    description=(
                        f"File: {file_path}\n"
                        f"Risk score: {info['risk_score']}\n"
                        f"Lines: {info['line_count']}\n\n"
                        f"Risk categories:\n{category_details}\n\n"
                        f"Review notes:\n{notes}\n\n"
                        f"Action: Read this file and analyze its intent and safety."
                    ),
                    file_path=file_path,
                    remediation="Read file content and verify behavior matches description",
                    analyzer="deep_agent",
                    metadata={
                        "risk_score": info["risk_score"],
                        "categories": list(info["categories"].keys()),
                        "review_notes": info["review_notes"],
                    },
                )
            )

        return findings

    def _analyze_cross_file_concerns(
        self, skill: Skill, file_risks: dict
    ) -> list[Finding]:
        """Identify concerns that span multiple files."""
        findings = []

        if len(file_risks) < 2:
            return findings

        # Check for data flow patterns
        has_data_source = any(
            "data_access" in info["categories"]
            for info in file_risks.values()
        )
        has_network_sink = any(
            "network" in info["categories"]
            for info in file_risks.values()
        )

        if has_data_source and has_network_sink:
            data_files = [
                path for path, info in file_risks.items()
                if "data_access" in info["categories"]
            ]
            network_files = [
                path for path, info in file_risks.items()
                if "network" in info["categories"]
            ]

            findings.append(
                Finding(
                    id=self._generate_id("CROSS_FILE_DATA_FLOW", skill.name),
                    rule_id="DEEP_AGENT_CROSS_FILE_FLOW",
                    category=ThreatCategory.DATA_EXFILTRATION,
                    severity=Severity.HIGH,
                    title="Cross-file data flow: Data access + Network in different files",
                    description=(
                        f"Files reading data: {', '.join(data_files[:3])}\n"
                        f"Files with network: {', '.join(network_files[:3])}\n\n"
                        f"Risk: Data may flow from source files to network sinks.\n"
                        f"Review: Check if data from {data_files[0] if data_files else 'N/A'} "
                        f"is sent via {network_files[0] if network_files else 'N/A'}"
                    ),
                    file_path=None,
                    remediation="Verify data flow between these files is legitimate",
                    analyzer="deep_agent",
                    metadata={
                        "data_files": data_files,
                        "network_files": network_files,
                    },
                )
            )

        return findings

    def _generate_id(self, prefix: str, context: str) -> str:
        """Generate unique finding ID."""
        combined = f"{prefix}:{context}"
        hash_obj = hashlib.sha256(combined.encode())
        return f"{prefix}_{hash_obj.hexdigest()[:10]}"
