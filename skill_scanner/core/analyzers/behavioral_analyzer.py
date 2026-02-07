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
Behavioral analyzer for agent skills using static dataflow analysis.

Analyzes skill scripts using AST parsing, dataflow tracking, and description-behavior
correlation checks. Detects threats through code analysis without execution.

Features:
- Static dataflow analysis for code behavior tracking
- Cross-file correlation analysis
"""

import hashlib
import logging

from ...core.models import Finding, Severity, Skill, ThreatCategory
from ...core.static_analysis.context_extractor import (
    ContextExtractor,
    SkillScriptContext,
)
from ...core.static_analysis.interprocedural.call_graph_analyzer import CallGraphAnalyzer
from ...core.static_analysis.interprocedural.cross_file_analyzer import CrossFileAnalyzer, CrossFileCorrelation
from .base import BaseAnalyzer

logger = logging.getLogger(__name__)


class BehavioralAnalyzer(BaseAnalyzer):
    """
    Behavioral analyzer using static dataflow analysis.

    Analyzes skill scripts through:
    1. AST parsing and function extraction
    2. Dataflow tracking (sources → sinks)
    3. Threat pattern detection
    4. Cross-file correlation analysis

    Does NOT execute code - uses static analysis for safety.
    """

    def __init__(self, use_static_analysis: bool = True):
        """
        Initialize behavioral analyzer.

        Args:
            use_static_analysis: Deprecated parameter, kept for backward compatibility.
                Static analysis is always enabled as it's required for the analyzer to function.
        """
        super().__init__("behavioral_analyzer")

        # Static analysis is always required - the parameter is kept for backward compatibility
        if not use_static_analysis:
            logger.warning(
                "use_static_analysis=False is deprecated and ignored. "
                "Static analysis is required for the behavioral analyzer to function."
            )
        self.use_static_analysis = True  # Always enabled
        self.context_extractor = ContextExtractor()  # Always initialized

    def analyze(self, skill: Skill) -> list[Finding]:
        """
        Analyze skill using static dataflow analysis.

        Args:
            skill: Skill to analyze

        Returns:
            List of behavioral findings
        """
        return self._analyze_static(skill)

    def _analyze_static(self, skill: Skill) -> list[Finding]:
        """Analyze skill using static dataflow analysis with cross-file correlation."""
        findings = []
        cross_file = CrossFileAnalyzer()
        call_graph_analyzer = CallGraphAnalyzer()

        # First pass: Extract context from each Python script
        for script_file in skill.get_scripts():
            if script_file.file_type != "python":
                continue

            content = script_file.read_content()
            if not content:
                continue

            # Add to call graph analyzer
            call_graph_analyzer.add_file(script_file.path, content)

            # Extract security context
            try:
                context = self.context_extractor.extract_context(script_file.path, content)

                # Add to cross-file analyzer
                cross_file.add_file_context(script_file.relative_path, context)

                # Generate findings from individual file context
                script_findings = self._generate_findings_from_context(context, skill)
                findings.extend(script_findings)

            except Exception as e:
                logger.warning("Failed to analyze %s: %s", script_file.relative_path, e)

        # Build call graph for cross-file analysis
        call_graph_analyzer.build_call_graph()

        # Second pass: Analyze cross-file correlations
        correlations = cross_file.analyze_correlations()
        correlation_findings = self._generate_findings_from_correlations(correlations, skill)
        findings.extend(correlation_findings)

        return findings

    def _generate_findings_from_context(self, context: SkillScriptContext, skill: Skill) -> list[Finding]:
        """Generate security findings from extracted context."""
        findings = []

        # Check for exfiltration patterns
        if context.has_network and context.has_env_var_access:
            findings.append(
                Finding(
                    id=self._generate_id("ENV_VAR_EXFILTRATION", context.file_path),
                    rule_id="BEHAVIOR_ENV_VAR_EXFILTRATION",
                    category=ThreatCategory.DATA_EXFILTRATION,
                    severity=Severity.CRITICAL,
                    title="Environment variable access with network calls detected",
                    description=f"Script accesses environment variables and makes network calls in {context.file_path}",
                    file_path=context.file_path,
                    remediation="Remove environment variable harvesting or network transmission",
                    analyzer="behavioral",
                    metadata={
                        "has_network": context.has_network,
                        "has_env_access": context.has_env_var_access,
                        "suspicious_urls": context.suspicious_urls,
                    },
                )
            )

        # Check for credential file access
        if context.has_credential_access:
            findings.append(
                Finding(
                    id=self._generate_id("CREDENTIAL_FILE_ACCESS", context.file_path),
                    rule_id="BEHAVIOR_CREDENTIAL_FILE_ACCESS",
                    category=ThreatCategory.DATA_EXFILTRATION,
                    severity=Severity.HIGH,
                    title="Credential file access detected",
                    description=f"Script accesses credential files in {context.file_path}",
                    file_path=context.file_path,
                    remediation="Remove access to ~/.aws, ~/.ssh, or other credential files",
                    analyzer="behavioral",
                )
            )

        # Check for environment variable harvesting (even without immediate network)
        if context.has_env_var_access:
            findings.append(
                Finding(
                    id=self._generate_id("ENV_VAR_HARVESTING", context.file_path),
                    rule_id="BEHAVIOR_ENV_VAR_HARVESTING",
                    category=ThreatCategory.DATA_EXFILTRATION,
                    severity=Severity.MEDIUM,
                    title="Environment variable harvesting detected",
                    description=f"Script iterates through environment variables in {context.file_path}",
                    file_path=context.file_path,
                    remediation="Remove environment variable collection unless explicitly required and documented",
                    analyzer="behavioral",
                )
            )

        # Check for suspicious URLs
        if context.suspicious_urls:
            for url in context.suspicious_urls:
                findings.append(
                    Finding(
                        id=self._generate_id("SUSPICIOUS_URL", url),
                        rule_id="BEHAVIOR_SUSPICIOUS_URL",
                        category=ThreatCategory.DATA_EXFILTRATION,
                        severity=Severity.HIGH,
                        title=f"Suspicious URL detected: {url}",
                        description="Script contains suspicious URL that may be used for data exfiltration",
                        file_path=context.file_path,
                        remediation="Review URL and ensure it's legitimate and documented",
                        analyzer="behavioral",
                        metadata={"url": url},
                    )
                )

        # Check for eval/exec with subprocess
        if context.has_eval_exec and context.has_subprocess:
            findings.append(
                Finding(
                    id=self._generate_id("EVAL_SUBPROCESS", context.file_path),
                    rule_id="BEHAVIOR_EVAL_SUBPROCESS",
                    category=ThreatCategory.COMMAND_INJECTION,
                    severity=Severity.CRITICAL,
                    title="eval/exec combined with subprocess detected",
                    description=f"Dangerous combination of code execution and system commands in {context.file_path}",
                    file_path=context.file_path,
                    remediation="Remove eval/exec or use safer alternatives",
                    analyzer="behavioral",
                )
            )

        return findings

    def _generate_id(self, prefix: str, context: str) -> str:
        """Generate unique finding ID."""
        combined = f"{prefix}:{context}"
        hash_obj = hashlib.sha256(combined.encode())
        return f"{prefix}_{hash_obj.hexdigest()[:10]}"

    def _generate_findings_from_correlations(
        self, correlations: list[CrossFileCorrelation], skill: Skill
    ) -> list[Finding]:
        """Generate findings from cross-file correlations."""
        findings = []

        for correlation in correlations:
            # Map correlation type to severity
            severity_map = {
                "CRITICAL": Severity.CRITICAL,
                "HIGH": Severity.HIGH,
                "MEDIUM": Severity.MEDIUM,
            }
            severity = severity_map.get(correlation.severity, Severity.MEDIUM)

            # Map threat type to category
            category_map = {
                "exfiltration_chain": ThreatCategory.DATA_EXFILTRATION,
                "credential_network_separation": ThreatCategory.DATA_EXFILTRATION,
                "env_var_exfiltration": ThreatCategory.DATA_EXFILTRATION,
            }
            category = category_map.get(correlation.threat_type, ThreatCategory.POLICY_VIOLATION)

            # Create finding
            finding = Finding(
                id=self._generate_id(
                    f"CROSSFILE_{correlation.threat_type.upper()}", "_".join(correlation.files_involved)
                ),
                rule_id=f"BEHAVIOR_CROSSFILE_{correlation.threat_type.upper()}",
                category=category,
                severity=severity,
                title=f"Cross-file {correlation.threat_type.replace('_', ' ')}: {len(correlation.files_involved)} files",
                description=correlation.description,
                file_path=None,  # Multiple files involved
                remediation=f"Review data flow across files: {', '.join(correlation.files_involved)}",
                analyzer="behavioral",
                metadata={
                    "files_involved": correlation.files_involved,
                    "threat_type": correlation.threat_type,
                    "evidence": correlation.evidence,
                },
            )
            findings.append(finding)

        return findings
