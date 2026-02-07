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
Command-line interface for the Skill Scanner.
"""

import argparse
import sys
from pathlib import Path

from ..core.analyzers.behavioral_analyzer import BehavioralAnalyzer
from ..core.analyzers.static import StaticAnalyzer
from ..core.reporters.json_reporter import JSONReporter
from ..core.reporters.sarif_reporter import SARIFReporter
from ..core.scanner import SkillScanner

from ..core.loader import SkillLoadError
from ..core.reporters.markdown_reporter import MarkdownReporter
from ..core.reporters.table_reporter import TableReporter


def _build_status_printer(output_format: str):
    """Create a status printer that keeps JSON output parseable."""
    is_json_output = output_format == "json"

    def status_print(msg: str) -> None:
        if is_json_output:
            print(msg, file=sys.stderr)
        else:
            print(msg)

    return status_print


def _initialize_analyzers(args, status_print):
    """Build analyzer list from CLI args."""
    analyzers = [
        StaticAnalyzer(
            yara_mode=args.yara_mode,
            custom_yara_rules_path=args.custom_rules,
            disabled_rules=set(args.disabled_rules or []),
        )
    ]

    if args.use_behavioral:
        try:
            behavioral_analyzer = BehavioralAnalyzer(use_static_analysis=True)
            analyzers.append(behavioral_analyzer)
            status_print("Using behavioral analyzer (static dataflow analysis)")
        except Exception as e:
            print(f"Warning: Could not initialize behavioral analyzer: {e}", file=sys.stderr)

    if args.use_trigger:
        try:
            from ..core.analyzers.trigger_analyzer import TriggerAnalyzer

            trigger_analyzer = TriggerAnalyzer()
            analyzers.append(trigger_analyzer)
            status_print("Using Trigger analyzer (description specificity analysis)")
        except Exception as e:
            print(f"Warning: Could not initialize Trigger analyzer: {e}", file=sys.stderr)

    return analyzers


def _generate_and_output_report(result_or_report, args, is_multi_skill=False):
    """Generate report in requested format and output to file or stdout.

    Args:
        result_or_report: ScanResult or Report object
        args: CLI arguments with format, output, detailed, compact attributes
        is_multi_skill: If True, use multi-skill summary for summary format

    Returns:
        Generated report string
    """
    # Generate report based on format
    if args.format == "json":
        reporter = JSONReporter(pretty=not args.compact)
        output = reporter.generate_report(result_or_report)
    elif args.format == "markdown":
        reporter = MarkdownReporter(detailed=args.detailed)
        output = reporter.generate_report(result_or_report)
    elif args.format == "table":
        reporter = TableReporter()
        output = reporter.generate_report(result_or_report)
    elif args.format == "sarif":
        reporter = SARIFReporter()
        output = reporter.generate_report(result_or_report)
    else:  # summary
        if is_multi_skill:
            output = generate_multi_skill_summary(result_or_report)
        else:
            output = generate_summary(result_or_report)

    # Output
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Report saved to: {args.output}")
    else:
        print(output)

    return output


def scan_command(args):
    """Handle the scan command for a single skill."""
    skill_dir = Path(args.skill_directory)

    if not skill_dir.exists():
        print(f"Error: Directory does not exist: {skill_dir}", file=sys.stderr)
        return 1

    status_print = _build_status_printer(args.format)
    analyzers = _initialize_analyzers(args, status_print)

    scanner = SkillScanner(analyzers=analyzers)

    try:
        # Scan the skill
        result = scanner.scan_skill(skill_dir)

        # Generate and output report
        _generate_and_output_report(result, args, is_multi_skill=False)

        # Exit with error code if critical/high issues found
        if not result.is_safe and args.fail_on_findings:
            return 1

        return 0

    except SkillLoadError as e:
        print(f"Error loading skill: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def scan_all_command(args):
    """Handle the scan-all command for multiple skills."""
    skills_dir = Path(args.skills_directory)

    if not skills_dir.exists():
        print(f"Error: Directory does not exist: {skills_dir}", file=sys.stderr)
        return 1

    status_print = _build_status_printer(args.format)
    analyzers = _initialize_analyzers(args, status_print)

    scanner = SkillScanner(analyzers=analyzers)

    try:
        # Scan all skills
        check_overlap = args.check_overlap
        report = scanner.scan_directory(skills_dir, recursive=args.recursive, check_overlap=check_overlap)

        if report.total_skills_scanned == 0:
            print("No skills found to scan.", file=sys.stderr)
            return 1

        # Generate and output report
        _generate_and_output_report(report, args, is_multi_skill=True)

        # Exit with error code if any skills have issues
        if args.fail_on_findings and (report.critical_count > 0 or report.high_count > 0):
            return 1

        return 0

    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def list_analyzers_command(args):
    """Handle the list-analyzers command."""
    print("Available Analyzers:")
    print("")
    print("1. static_analyzer (Default)")
    print("   - Pattern-based detection using YAML + YARA rules")
    print("   - Scans SKILL.md instructions and scripts")
    print("   - Detects 80+ security patterns across 12+ threat categories")
    print("")

    print("2. behavioral_analyzer [OK] Available")
    print("   - Static dataflow analysis (AST + taint tracking)")
    print("   - Tracks data from sources to sinks without execution")
    print("   - Detects multi-file exfiltration chains")
    print("   - Cross-file correlation analysis")
    print("   - Usage: --use-behavioral")
    print("")

    print("3. trigger_analyzer [OK] Available")
    print("   - Detects overly generic skill descriptions")
    print("   - Identifies trigger hijacking risks")
    print("   - Checks description specificity and keyword baiting")
    print("   - Usage: --use-trigger")
    print("")

    return 0


def validate_rules_command(args):
    """Handle the validate-rules command."""
    from ..core.rules.patterns import RuleLoader

    try:
        if args.rules_file:
            loader = RuleLoader(Path(args.rules_file))
        else:
            loader = RuleLoader()

        rules = loader.load_rules()

        print(f"[OK] Successfully loaded {len(rules)} rules")
        print("")
        print("Rules by category:")

        for category, category_rules in loader.rules_by_category.items():
            print(f"  - {category.value}: {len(category_rules)} rules")

        return 0

    except Exception as e:
        print(f"[FAIL] Error validating rules: {e}", file=sys.stderr)
        return 1


def generate_summary(result) -> str:
    """Generate a simple summary output."""
    lines = []
    lines.append("=" * 60)
    lines.append(f"Skill: {result.skill_name}")
    lines.append("=" * 60)
    lines.append(f"Status: {'[OK] SAFE' if result.is_safe else '[FAIL] ISSUES FOUND'}")
    lines.append(f"Max Severity: {result.max_severity.value}")
    lines.append(f"Total Findings: {len(result.findings)}")
    lines.append(f"Scan Duration: {result.scan_duration_seconds:.2f}s")
    lines.append("")

    if result.findings:
        from ..core.models import Severity

        lines.append("Findings Summary:")
        lines.append(f"  Critical: {len(result.get_findings_by_severity(Severity.CRITICAL))}")
        lines.append(f"  High:     {len(result.get_findings_by_severity(Severity.HIGH))}")
        lines.append(f"  Medium:   {len(result.get_findings_by_severity(Severity.MEDIUM))}")
        lines.append(f"  Low:      {len(result.get_findings_by_severity(Severity.LOW))}")
        lines.append(f"  Info:     {len(result.get_findings_by_severity(Severity.INFO))}")

    return "\n".join(lines)


def generate_multi_skill_summary(report) -> str:
    """Generate a simple summary for multiple skills."""
    lines = []
    lines.append("=" * 60)
    lines.append("Agent Skills Security Scan Report")
    lines.append("=" * 60)
    lines.append(f"Skills Scanned: {report.total_skills_scanned}")
    lines.append(f"Safe Skills: {report.safe_count}")
    lines.append(f"Total Findings: {report.total_findings}")
    lines.append("")
    lines.append("Findings by Severity:")
    lines.append(f"  Critical: {report.critical_count}")
    lines.append(f"  High:     {report.high_count}")
    lines.append(f"  Medium:   {report.medium_count}")
    lines.append(f"  Low:      {report.low_count}")
    lines.append(f"  Info:     {report.info_count}")
    lines.append("")

    lines.append("Individual Skills:")
    for result in report.scan_results:
        status = "[OK]" if result.is_safe else "[FAIL]"
        lines.append(f"  {status} {result.skill_name} - {len(result.findings)} findings ({result.max_severity.value})")

    return "\n".join(lines)


def _add_common_scan_arguments(parser):
    """Add common arguments shared by scan and scan-all commands.

    Args:
        parser: ArgumentParser to add arguments to
    """
    parser.add_argument(
        "--format",
        choices=["summary", "json", "markdown", "table", "sarif"],
        default="summary",
        help="Output format (default: summary). Use 'sarif' for GitHub Code Scanning integration.",
    )
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--detailed", action="store_true", help="Include detailed findings")
    parser.add_argument("--compact", action="store_true", help="Compact JSON output")
    parser.add_argument(
        "--fail-on-findings", action="store_true", help="Exit with error code if critical/high findings exist"
    )
    parser.add_argument("--use-behavioral", action="store_true", help="Enable behavioral dataflow analysis")
    parser.add_argument(
        "--use-trigger",
        action="store_true",
        help="Enable trigger specificity analysis (detects overly generic descriptions)",
    )
    parser.add_argument(
        "--yara-mode",
        choices=["strict", "balanced", "permissive"],
        default="balanced",
        help="YARA detection mode: strict (max security, more FPs), balanced (default), permissive (fewer FPs, may miss threats)",
    )
    parser.add_argument(
        "--custom-rules",
        metavar="PATH",
        help="Path to directory containing custom YARA rules (.yara files) to use instead of built-in rules",
    )
    parser.add_argument(
        "--disable-rule",
        action="append",
        metavar="RULE_NAME",
        dest="disabled_rules",
        help="Disable a specific rule by name (can be used multiple times). Example: --disable-rule YARA_script_injection",
    )


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Skill Scanner - Security scanner for agent skills packages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan a single skill
  skill-scanner scan /path/to/skill

  # Scan with behavioral analysis (dataflow tracking)
  skill-scanner scan /path/to/skill --use-behavioral

  # Scan with JSON output
  skill-scanner scan /path/to/skill --format json

  # Scan all skills in a directory
  skill-scanner scan-all /path/to/skills

  # Scan recursively with static + behavioral analyzers
  skill-scanner scan-all /path/to/skills --recursive --use-behavioral

  # List available analyzers
  skill-scanner list-analyzers

  # Validate rule signatures
  skill-scanner validate-rules
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Scan command
    scan_parser = subparsers.add_parser("scan", help="Scan a single skill package")
    scan_parser.add_argument("skill_directory", help="Path to skill directory")
    _add_common_scan_arguments(scan_parser)

    # Scan-all command
    scan_all_parser = subparsers.add_parser("scan-all", help="Scan multiple skill packages")
    scan_all_parser.add_argument("skills_directory", help="Directory containing skills")
    scan_all_parser.add_argument("--recursive", "-r", action="store_true", help="Recursively search for skills")
    scan_all_parser.add_argument(
        "--check-overlap", action="store_true", help="Enable cross-skill description overlap detection"
    )
    _add_common_scan_arguments(scan_all_parser)

    # List analyzers command
    subparsers.add_parser("list-analyzers", help="List available analyzers")

    # Validate rules command
    validate_parser = subparsers.add_parser("validate-rules", help="Validate rule signatures")
    validate_parser.add_argument("--rules-file", help="Path to custom rules file")

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Execute command
    if args.command == "scan":
        return scan_command(args)
    elif args.command == "scan-all":
        return scan_all_command(args)
    elif args.command == "list-analyzers":
        return list_analyzers_command(args)
    elif args.command == "validate-rules":
        return validate_rules_command(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
