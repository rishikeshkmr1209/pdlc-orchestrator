#!/usr/bin/env python3
"""Claude Master Plugin — Skill Validator

Validates all SKILL.md files for structural correctness,
frontmatter integrity, and cross-reference consistency.

Usage:
    python scripts/validate-skills.py              # Human-readable output
    python scripts/validate-skills.py --json       # JSON report
    python scripts/validate-skills.py --verbose    # Debug frontmatter parsing

Exit codes:
    0 — All files pass validation
    1 — One or more validation errors found
"""

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Minimum Python version required
MIN_PYTHON = (3, 9)

# Known Claude Code tool names (last updated: 2026-02-25)
VALID_TOOLS = frozenset({
    "Read", "Write", "Edit", "Bash", "Grep", "Glob", "Task", "Skill",
    "WebFetch", "WebSearch", "NotebookEdit", "TodoWrite",
    "AskUserQuestion", "ToolSearch",
})

# Required frontmatter fields
REQUIRED_FRONTMATTER_FIELDS = {"name", "description"}

# Recommended Markdown sections (warning if missing)
RECOMMENDED_SECTIONS = {"Evaluation"}

# ANSI color codes
_RED = "\033[31m"
_YELLOW = "\033[33m"
_GREEN = "\033[32m"
_BOLD = "\033[1m"
_RESET = "\033[0m"


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class ValidationFinding:
    file_path: str
    severity: str  # "error" or "warning"
    message: str
    category: str  # "frontmatter", "structure", "cross-reference", "schema"


@dataclass
class SkillInfo:
    dir_name: str
    file_path: str
    frontmatter: dict | None
    body: str
    status: str = "ok"  # "ok", "missing_file", "empty", "read_error", "no_frontmatter"


@dataclass
class ValidationReport:
    findings: dict = field(default_factory=dict)  # file_path -> list[Finding]
    total_errors: int = 0
    total_warnings: int = 0
    files_checked: int = 0

    def add(self, finding: ValidationFinding) -> None:
        self.findings.setdefault(finding.file_path, []).append(finding)
        if finding.severity == "error":
            self.total_errors += 1
        else:
            self.total_warnings += 1


# ---------------------------------------------------------------------------
# COMP-002: Frontmatter Parser
# ---------------------------------------------------------------------------

def parse_frontmatter(content: str) -> tuple[dict | None, str]:
    """Extract and parse YAML frontmatter from SKILL.md content.

    Handles simple scalars (key: value), list items (- item), and
    folded block scalars (key: >) with indented continuation lines.

    Returns (parsed_dict, body_after_frontmatter).
    Returns (None, content) if no valid frontmatter delimiters found.
    """
    stripped = content.lstrip("\ufeff")  # strip UTF-8 BOM if present
    # Normalize CRLF to LF for Windows-created files
    stripped = stripped.replace("\r\n", "\n")

    # Extract frontmatter between --- delimiters (handles EOF after closing ---)
    fm_match = re.match(r"^---[ \t]*\n(.*?)\n---[ \t]*(?:\n|$)", stripped, re.DOTALL)
    if not fm_match:
        return None, content

    fm_text = fm_match.group(1)
    body = stripped[fm_match.end():]

    result: dict = {}
    current_key: str | None = None
    current_value_lines: list[str] = []
    is_block_scalar = False
    is_list = False

    def _flush() -> None:
        nonlocal current_key, current_value_lines, is_block_scalar, is_list
        if current_key is None:
            return
        if is_list:
            items = []
            for line in current_value_lines:
                item = line.strip()
                if item.startswith("- "):
                    items.append(item[2:].strip())
                elif item.startswith("-"):
                    items.append(item[1:].strip())
            result[current_key] = items
        elif is_block_scalar:
            result[current_key] = " ".join(
                line.strip() for line in current_value_lines if line.strip()
            )
        else:
            result[current_key] = " ".join(
                line.strip() for line in current_value_lines if line.strip()
            )
        current_key = None
        current_value_lines = []
        is_block_scalar = False
        is_list = False

    for line in fm_text.split("\n"):
        # Non-indented line with colon = new key
        key_match = re.match(r"^([a-zA-Z_][a-zA-Z0-9_-]*)\s*:\s*(.*)", line)
        if key_match and not line.startswith((" ", "\t")):
            _flush()
            current_key = key_match.group(1)
            value = key_match.group(2).strip()

            if value == ">":
                is_block_scalar = True
            elif value == "|":
                is_block_scalar = True
            elif value == "":
                # Could be block scalar or list — determine from next lines
                is_block_scalar = False
            else:
                current_value_lines = [value]
        elif current_key and line.startswith((" ", "\t")):
            # Indented continuation line
            stripped_line = line.strip()
            if stripped_line.startswith("- "):
                is_list = True
            current_value_lines.append(line)
        # Ignore blank lines or comments

    _flush()

    return result, body


# ---------------------------------------------------------------------------
# COMP-003: Frontmatter Validator
# ---------------------------------------------------------------------------

def validate_frontmatter(
    frontmatter: dict | None, file_path: str
) -> list[ValidationFinding]:
    """Validate frontmatter has required fields and valid tool names."""
    findings: list[ValidationFinding] = []

    if frontmatter is None:
        findings.append(ValidationFinding(
            file_path=file_path,
            severity="error",
            message="No valid YAML frontmatter found (expected --- delimiters).",
            category="frontmatter",
        ))
        return findings

    # Check required fields
    for req_field in REQUIRED_FRONTMATTER_FIELDS:
        if req_field not in frontmatter or not frontmatter[req_field]:
            findings.append(ValidationFinding(
                file_path=file_path,
                severity="error",
                message=f"Missing required frontmatter field: '{req_field}'.",
                category="frontmatter",
            ))

    # Validate allowed-tools (optional field, but if present must be valid)
    tools = frontmatter.get("allowed-tools")
    if tools is not None:
        if not isinstance(tools, list):
            findings.append(ValidationFinding(
                file_path=file_path,
                severity="error",
                message="'allowed-tools' must be a list of tool names.",
                category="frontmatter",
            ))
        else:
            for tool in tools:
                if tool not in VALID_TOOLS:
                    findings.append(ValidationFinding(
                        file_path=file_path,
                        severity="warning",
                        message=f"Unrecognized tool name in allowed-tools: '{tool}'. "
                                f"Valid tools: {', '.join(sorted(VALID_TOOLS))}.",
                        category="frontmatter",
                    ))

    return findings


# ---------------------------------------------------------------------------
# COMP-004: Markdown Structure Validator
# ---------------------------------------------------------------------------

def validate_markdown_structure(
    body: str, file_path: str
) -> list[ValidationFinding]:
    """Check Markdown body for required heading structure."""
    findings: list[ValidationFinding] = []

    if not body.strip():
        findings.append(ValidationFinding(
            file_path=file_path,
            severity="error",
            message="Markdown body is empty (no content after frontmatter).",
            category="structure",
        ))
        return findings

    # Check for H1 title
    h1_matches = re.findall(r"^# .+", body, re.MULTILINE)
    if not h1_matches:
        findings.append(ValidationFinding(
            file_path=file_path,
            severity="error",
            message="Missing H1 title (expected '# Title' as first heading).",
            category="structure",
        ))

    # Check for recommended sections
    h2_matches = re.findall(r"^## (.+)", body, re.MULTILINE)
    h2_names = {h.strip() for h in h2_matches}

    for section in RECOMMENDED_SECTIONS:
        if section not in h2_names:
            findings.append(ValidationFinding(
                file_path=file_path,
                severity="warning",
                message=f"Missing recommended section: '## {section}'.",
                category="structure",
            ))

    return findings


# ---------------------------------------------------------------------------
# COMP-005: Cross-Reference Validator
# ---------------------------------------------------------------------------

def extract_skill_refs_from_claude_md(claude_md_content: str) -> set[str]:
    """Extract skill names referenced in CLAUDE.md.

    Only matches explicit path references to .claude/skills/<name>/ to avoid
    false positives from backtick-quoted subagent names, naming conventions,
    and other hyphenated terms.
    """
    refs: set[str] = set()

    # Match skills/<name>/ or skills/<name>/SKILL.md
    for m in re.finditer(r"skills/([a-zA-Z0-9_-]+)/", claude_md_content):
        refs.add(m.group(1))

    return refs


def validate_cross_references(
    plugin_root: Path,
    skill_dirs: set[str],
    skill_bodies: dict[str, str],
) -> list[ValidationFinding]:
    """Verify CLAUDE.md skill refs and schema file refs in skill bodies."""
    findings: list[ValidationFinding] = []

    # Read CLAUDE.md
    claude_md_path = plugin_root / "CLAUDE.md"
    if not claude_md_path.exists():
        findings.append(ValidationFinding(
            file_path="CLAUDE.md",
            severity="warning",
            message="CLAUDE.md not found at plugin root. Skipping cross-reference checks.",
            category="cross-reference",
        ))
        return findings

    try:
        claude_md_content = claude_md_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        findings.append(ValidationFinding(
            file_path="CLAUDE.md",
            severity="error",
            message=f"Failed to read CLAUDE.md: {e}",
            category="cross-reference",
        ))
        return findings

    # Check that skill dirs referenced in CLAUDE.md actually exist
    refs = extract_skill_refs_from_claude_md(claude_md_content)
    for ref in sorted(refs):
        if ref not in skill_dirs:
            findings.append(ValidationFinding(
                file_path="CLAUDE.md",
                severity="error",
                message=f"CLAUDE.md references skill '{ref}' but no directory "
                        f"skills/{ref}/ exists.",
                category="cross-reference",
            ))

    # Note: JSON schema file references removed — artifacts now use Markdown
    # with Required Sections validation (no .schema.json files exist).

    return findings


# ---------------------------------------------------------------------------
# COMP-007: Result Formatter
# ---------------------------------------------------------------------------

def format_human(report: ValidationReport) -> str:
    """Format validation results as colored, human-readable terminal output."""
    lines: list[str] = []
    lines.append(f"\n{_BOLD}Skill Validator Report{_RESET}")
    lines.append(f"Files checked: {report.files_checked}")
    lines.append("")

    if not report.findings:
        lines.append(f"{_GREEN}All files passed validation.{_RESET}")
        return "\n".join(lines)

    for file_path in sorted(report.findings):
        file_findings = report.findings[file_path]
        lines.append(f"{_BOLD}{file_path}{_RESET}")
        for f in file_findings:
            if f.severity == "error":
                icon = f"{_RED}ERROR{_RESET}"
            else:
                icon = f"{_YELLOW}WARN {_RESET}"
            lines.append(f"  {icon} [{f.category}] {f.message}")
        lines.append("")

    # Summary
    errors = report.total_errors
    warnings = report.total_warnings
    if errors > 0:
        lines.append(f"{_RED}{_BOLD}{errors} error(s){_RESET}, {warnings} warning(s)")
    else:
        lines.append(f"{_GREEN}0 errors{_RESET}, {_YELLOW}{warnings} warning(s){_RESET}")

    return "\n".join(lines)


def format_json(report: ValidationReport) -> str:
    """Format validation results as a JSON report."""
    output = {
        "files_checked": report.files_checked,
        "total_errors": report.total_errors,
        "total_warnings": report.total_warnings,
        "results": {},
    }

    for file_path in sorted(report.findings):
        output["results"][file_path] = [
            asdict(f) for f in report.findings[file_path]
        ]

    return json.dumps(output, indent=2)


# ---------------------------------------------------------------------------
# COMP-001: Main Orchestrator
# ---------------------------------------------------------------------------

def discover_skills(plugin_root: Path) -> list[SkillInfo]:
    """Discover all skill directories and parse their SKILL.md files."""
    skills_dir = plugin_root / "skills"
    skills: list[SkillInfo] = []

    if not skills_dir.exists():
        return skills

    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue

        skill_md = skill_dir / "SKILL.md"
        dir_name = skill_dir.name

        rel_path = str(skill_md.relative_to(plugin_root))

        if not skill_md.exists():
            # Edge case EC-002: directory exists but no SKILL.md
            skills.append(SkillInfo(
                dir_name=dir_name, file_path=rel_path,
                frontmatter=None, body="", status="missing_file",
            ))
            continue

        try:
            content = skill_md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            skills.append(SkillInfo(
                dir_name=dir_name, file_path=rel_path,
                frontmatter=None, body="", status="read_error",
            ))
            continue

        # Edge case EC-001: empty file
        if not content.strip():
            skills.append(SkillInfo(
                dir_name=dir_name, file_path=rel_path,
                frontmatter=None, body="", status="empty",
            ))
            continue

        frontmatter, body = parse_frontmatter(content)
        status = "ok" if frontmatter is not None else "no_frontmatter"
        skills.append(SkillInfo(
            dir_name=dir_name, file_path=rel_path,
            frontmatter=frontmatter, body=body, status=status,
        ))

    return skills




def main() -> None:
    # Version check
    if sys.version_info < MIN_PYTHON:
        print(
            f"Error: Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ required, "
            f"found {sys.version_info.major}.{sys.version_info.minor}.",
            file=sys.stderr,
        )
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description="Validate SKILL.md files in the Claude plugin."
    )
    parser.add_argument(
        "--json", action="store_true", dest="json_output",
        help="Output results as JSON instead of human-readable text.",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Print parsed frontmatter and detected headings for debugging.",
    )
    args = parser.parse_args()

    # Resolve plugin root (parent of scripts/)
    plugin_root = Path(__file__).resolve().parent.parent

    report = ValidationReport()

    # --- Discover and validate skills ---
    skills = discover_skills(plugin_root)
    skill_dirs: set[str] = set()
    skill_bodies: dict[str, str] = {}

    for skill in skills:
        report.files_checked += 1
        skill_dirs.add(skill.dir_name)

        # Handle non-ok statuses from discovery
        if skill.status == "missing_file":
            report.add(ValidationFinding(
                file_path=skill.file_path, severity="error",
                message="Skill directory missing SKILL.md file.",
                category="frontmatter",
            ))
            continue
        if skill.status == "read_error":
            report.add(ValidationFinding(
                file_path=skill.file_path, severity="error",
                message="Failed to read SKILL.md file (permission denied or encoding error).",
                category="frontmatter",
            ))
            continue
        if skill.status == "empty":
            report.add(ValidationFinding(
                file_path=skill.file_path, severity="error",
                message="Empty file — no frontmatter or content found.",
                category="frontmatter",
            ))
            continue
        if skill.status == "no_frontmatter":
            report.add(ValidationFinding(
                file_path=skill.file_path, severity="error",
                message="No valid YAML frontmatter found (expected --- delimiters).",
                category="frontmatter",
            ))
            continue

        # Verbose: show parsed frontmatter
        if args.verbose:
            print(f"\n{_BOLD}[VERBOSE] {skill.file_path}{_RESET}")
            print(f"  Frontmatter: {json.dumps(skill.frontmatter, indent=4, default=str)}")
            headings = re.findall(r"^(#{1,3}) (.+)", skill.body, re.MULTILINE)
            print(f"  Headings: {[(h[0], h[1].strip()) for h in headings]}")

        # Validate frontmatter
        for finding in validate_frontmatter(skill.frontmatter, skill.file_path):
            report.add(finding)

        # Validate Markdown structure
        for finding in validate_markdown_structure(skill.body, skill.file_path):
            report.add(finding)

        # Collect body for cross-reference checking
        skill_bodies[skill.file_path] = skill.body

    # --- Cross-reference validation ---
    for finding in validate_cross_references(plugin_root, skill_dirs, skill_bodies):
        report.add(finding)

    # --- Output ---
    if args.json_output:
        print(format_json(report))
    else:
        print(format_human(report))

    sys.exit(1 if report.total_errors > 0 else 0)


if __name__ == "__main__":
    main()
