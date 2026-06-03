#!/usr/bin/env python3
"""Unit tests for scripts/validate-skills.py"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

# Add scripts/ to path so we can import the module
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

# Import functions under test
from importlib import import_module

# Import as module (handle hyphen in filename)
import importlib.util

spec = importlib.util.spec_from_file_location(
    "validate_skills", REPO_ROOT / "scripts" / "validate-skills.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

parse_frontmatter = mod.parse_frontmatter
validate_frontmatter = mod.validate_frontmatter
validate_markdown_structure = mod.validate_markdown_structure
format_human = mod.format_human
format_json = mod.format_json
ValidationReport = mod.ValidationReport
ValidationFinding = mod.ValidationFinding

FIXTURES = REPO_ROOT / "tests" / "fixtures"


class TestParseFrontmatter(unittest.TestCase):
    """Tests for COMP-002: FrontmatterParser"""

    def test_valid_simple_frontmatter(self):
        content = "---\nname: test\ndescription: A test skill\n---\n# Body"
        fm, body = parse_frontmatter(content)
        self.assertIsNotNone(fm)
        self.assertEqual(fm["name"], "test")
        self.assertEqual(fm["description"], "A test skill")
        self.assertIn("# Body", body)

    def test_folded_block_scalar(self):
        content = "---\nname: test\ndescription: >\n  A multiline\n  description here.\nallowed-tools:\n  - Read\n  - Write\n---\n# Body"
        fm, body = parse_frontmatter(content)
        self.assertIsNotNone(fm)
        self.assertEqual(fm["name"], "test")
        self.assertIn("multiline", fm["description"])
        self.assertIn("description here.", fm["description"])
        self.assertEqual(fm["allowed-tools"], ["Read", "Write"])

    def test_missing_delimiters(self):
        content = "# No frontmatter here\nJust markdown."
        fm, body = parse_frontmatter(content)
        self.assertIsNone(fm)

    def test_empty_content(self):
        fm, body = parse_frontmatter("")
        self.assertIsNone(fm)

    def test_utf8_bom(self):
        content = "\ufeff---\nname: test\ndescription: BOM test\n---\n# Body"
        fm, body = parse_frontmatter(content)
        self.assertIsNotNone(fm)
        self.assertEqual(fm["name"], "test")

    def test_list_parsing(self):
        content = "---\nname: test\ndescription: test\nallowed-tools:\n  - Read\n  - Grep\n  - Glob\n---\n# Body"
        fm, body = parse_frontmatter(content)
        self.assertEqual(fm["allowed-tools"], ["Read", "Grep", "Glob"])

    def test_real_skill_file(self):
        """Parse an actual SKILL.md from the repo."""
        skill_path = REPO_ROOT / ".claude" / "skills" / "code-review" / "SKILL.md"
        if not skill_path.exists():
            self.skipTest("code-review skill not found")
        content = skill_path.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(content)
        self.assertIsNotNone(fm)
        self.assertEqual(fm["name"], "code-review")
        self.assertIn("Read", fm["allowed-tools"])


class TestValidateFrontmatter(unittest.TestCase):
    """Tests for COMP-003: FrontmatterValidator"""

    def test_valid_frontmatter(self):
        fm = {"name": "test", "description": "A test", "allowed-tools": ["Read"]}
        findings = validate_frontmatter(fm, "test.md")
        errors = [f for f in findings if f.severity == "error"]
        self.assertEqual(len(errors), 0)

    def test_missing_name(self):
        fm = {"description": "A test"}
        findings = validate_frontmatter(fm, "test.md")
        errors = [f for f in findings if f.severity == "error"]
        self.assertEqual(len(errors), 1)
        self.assertIn("name", errors[0].message)

    def test_missing_description(self):
        fm = {"name": "test"}
        findings = validate_frontmatter(fm, "test.md")
        errors = [f for f in findings if f.severity == "error"]
        self.assertEqual(len(errors), 1)
        self.assertIn("description", errors[0].message)

    def test_none_frontmatter(self):
        findings = validate_frontmatter(None, "test.md")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].severity, "error")

    def test_invalid_tool_name(self):
        fm = {"name": "test", "description": "test", "allowed-tools": ["Read", "FooBar"]}
        findings = validate_frontmatter(fm, "test.md")
        warnings = [f for f in findings if f.severity == "warning"]
        self.assertEqual(len(warnings), 1)
        self.assertIn("FooBar", warnings[0].message)

    def test_all_valid_tools(self):
        fm = {"name": "test", "description": "test", "allowed-tools": ["Read", "Write", "Grep"]}
        findings = validate_frontmatter(fm, "test.md")
        self.assertEqual(len(findings), 0)

    def test_empty_tools_list(self):
        fm = {"name": "test", "description": "test", "allowed-tools": []}
        findings = validate_frontmatter(fm, "test.md")
        self.assertEqual(len(findings), 0)


class TestValidateMarkdownStructure(unittest.TestCase):
    """Tests for COMP-004: MarkdownStructureValidator"""

    def test_valid_structure(self):
        body = "# Title\n\n## Process\n\nContent.\n\n## Evaluation\n\n| Col |\n"
        findings = validate_markdown_structure(body, "test.md")
        errors = [f for f in findings if f.severity == "error"]
        self.assertEqual(len(errors), 0)

    def test_missing_h1(self):
        body = "## Process\n\nContent.\n\n## Evaluation\n\n| Col |\n"
        findings = validate_markdown_structure(body, "test.md")
        errors = [f for f in findings if f.severity == "error"]
        self.assertEqual(len(errors), 1)
        self.assertIn("H1", errors[0].message)

    def test_missing_evaluation(self):
        body = "# Title\n\n## Process\n\nContent.\n"
        findings = validate_markdown_structure(body, "test.md")
        warnings = [f for f in findings if f.severity == "warning"]
        self.assertEqual(len(warnings), 1)
        self.assertIn("Evaluation", warnings[0].message)

    def test_empty_body(self):
        findings = validate_markdown_structure("", "test.md")
        errors = [f for f in findings if f.severity == "error"]
        self.assertEqual(len(errors), 1)
        self.assertIn("empty", errors[0].message.lower())


class TestResultFormatter(unittest.TestCase):
    """Tests for COMP-007: ResultFormatter"""

    def test_clean_pass_human(self):
        report = ValidationReport(files_checked=5)
        output = format_human(report)
        self.assertIn("passed", output.lower())

    def test_error_human(self):
        report = ValidationReport(files_checked=1)
        report.add(ValidationFinding("test.md", "error", "Something broke", "frontmatter"))
        output = format_human(report)
        self.assertIn("ERROR", output)
        self.assertIn("1 error(s)", output)

    def test_clean_pass_json(self):
        report = ValidationReport(files_checked=5)
        output = format_json(report)
        data = json.loads(output)
        self.assertEqual(data["total_errors"], 0)
        self.assertEqual(data["files_checked"], 5)

    def test_error_json(self):
        report = ValidationReport(files_checked=1)
        report.add(ValidationFinding("test.md", "error", "Broke", "frontmatter"))
        output = format_json(report)
        data = json.loads(output)
        self.assertEqual(data["total_errors"], 1)
        self.assertIn("test.md", data["results"])


class TestIntegration(unittest.TestCase):
    """Integration tests running the full script."""

    def test_full_run_passes(self):
        """The real codebase should pass validation."""
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "validate-skills.py"), "--json"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        self.assertEqual(result.returncode, 0, f"Validator failed:\n{result.stdout}\n{result.stderr}")
        data = json.loads(result.stdout)
        self.assertEqual(data["total_errors"], 0)
        self.assertGreaterEqual(data["files_checked"], 18)

    def test_json_output_valid(self):
        """JSON output is parseable."""
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "validate-skills.py"), "--json"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        data = json.loads(result.stdout)
        self.assertIn("files_checked", data)
        self.assertIn("total_errors", data)
        self.assertIn("total_warnings", data)
        self.assertIn("results", data)


if __name__ == "__main__":
    unittest.main()
