#!/usr/bin/env python3
"""Unit tests for skills/autorefine/task_bank.py"""

import importlib.util
import sys
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Dynamic import
# ---------------------------------------------------------------------------

_TB_PATH = Path(__file__).resolve().parent.parent / "skills" / "autorefine" / "task_bank.py"
_spec = importlib.util.spec_from_file_location("task_bank", _TB_PATH)
task_bank = importlib.util.module_from_spec(_spec)
sys.modules["task_bank"] = task_bank
_spec.loader.exec_module(task_bank)

Task = task_bank.Task
load_task = task_bank.load_task
list_tasks = task_bank.list_tasks
validate_task = task_bank.validate_task
parse_frontmatter = task_bank.parse_frontmatter

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


class TestParseFrontmatter(unittest.TestCase):
    """Test YAML frontmatter parsing."""

    def test_valid_frontmatter(self):
        content = "---\nid: test\ntier: 1\n---\n# Body"
        fm, body = parse_frontmatter(content)
        self.assertIsNotNone(fm)
        self.assertEqual(fm["id"], "test")
        self.assertEqual(fm["tier"], "1")
        self.assertIn("# Body", body)

    def test_no_frontmatter(self):
        content = "# Just a heading\nSome text."
        fm, body = parse_frontmatter(content)
        self.assertIsNone(fm)
        self.assertEqual(body, content)


class TestLoadTask(unittest.TestCase):
    """Test loading tasks from markdown files."""

    def test_load_valid_task(self):
        task = load_task(str(FIXTURES_DIR / "sample-task-valid.md"))
        self.assertEqual(task.id, "test-valid-task")
        self.assertEqual(task.tier, 1)
        self.assertEqual(task.token_budget, 500)
        self.assertEqual(task.expected_turns, 3)
        self.assertIn("adds two numbers", task.description)
        self.assertTrue(len(task.success_criteria) >= 3)
        self.assertTrue(len(task.setup_commands) >= 1)

    def test_load_invalid_task_raises(self):
        with self.assertRaises(ValueError) as ctx:
            load_task(str(FIXTURES_DIR / "sample-task-invalid.md"))
        self.assertIn("Missing required fields", str(ctx.exception))

    def test_load_nonexistent_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            load_task("/nonexistent/path/task.md")


class TestListTasks(unittest.TestCase):
    """Test listing tasks from a directory."""

    def test_list_from_fixtures(self):
        # Fixtures contain one valid task file; invalid is skipped
        tasks = list_tasks(str(FIXTURES_DIR))
        valid_ids = [t.id for t in tasks]
        self.assertIn("test-valid-task", valid_ids)

    def test_list_from_nonexistent_dir(self):
        tasks = list_tasks("/nonexistent/dir")
        self.assertEqual(tasks, [])

    def test_sorted_by_tier(self):
        tasks = list_tasks(str(FIXTURES_DIR))
        tiers = [t.tier for t in tasks]
        self.assertEqual(tiers, sorted(tiers))


class TestValidateTask(unittest.TestCase):
    """Test task validation logic."""

    def test_valid_task(self):
        task = Task(
            id="t1-test",
            tier=1,
            description="A test task",
            success_criteria=["works"],
            token_budget=500,
            expected_turns=3,
        )
        errors = validate_task(task)
        self.assertEqual(errors, [])

    def test_empty_id(self):
        task = Task(id="", tier=1, description="d", success_criteria=["c"],
                    token_budget=500, expected_turns=3)
        errors = validate_task(task)
        self.assertTrue(any("id" in e.lower() for e in errors))

    def test_invalid_tier(self):
        task = Task(id="t", tier=0, description="d", success_criteria=["c"],
                    token_budget=500, expected_turns=3)
        errors = validate_task(task)
        self.assertTrue(any("tier" in e.lower() for e in errors))

        task2 = Task(id="t", tier=6, description="d", success_criteria=["c"],
                     token_budget=500, expected_turns=3)
        errors2 = validate_task(task2)
        self.assertTrue(any("tier" in e.lower() for e in errors2))

    def test_empty_description(self):
        task = Task(id="t", tier=1, description="", success_criteria=["c"],
                    token_budget=500, expected_turns=3)
        errors = validate_task(task)
        self.assertTrue(any("description" in e.lower() for e in errors))

    def test_no_success_criteria(self):
        task = Task(id="t", tier=1, description="d", success_criteria=[],
                    token_budget=500, expected_turns=3)
        errors = validate_task(task)
        self.assertTrue(any("criteria" in e.lower() for e in errors))

    def test_zero_token_budget(self):
        task = Task(id="t", tier=1, description="d", success_criteria=["c"],
                    token_budget=0, expected_turns=3)
        errors = validate_task(task)
        self.assertTrue(any("budget" in e.lower() for e in errors))

    def test_zero_expected_turns(self):
        task = Task(id="t", tier=1, description="d", success_criteria=["c"],
                    token_budget=500, expected_turns=0)
        errors = validate_task(task)
        self.assertTrue(any("turns" in e.lower() for e in errors))


if __name__ == "__main__":
    unittest.main()
