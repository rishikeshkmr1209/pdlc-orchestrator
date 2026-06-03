#!/usr/bin/env python3
"""Unit tests for skills/autorefine/runner.py

Uses mocked subprocess calls since we can't run real `claude` in tests.
"""

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Dynamic imports
# ---------------------------------------------------------------------------

_BASE = Path(__file__).resolve().parent.parent / "skills" / "autorefine"

_spec_s = importlib.util.spec_from_file_location("scorer", _BASE / "scorer.py")
scorer = importlib.util.module_from_spec(_spec_s)
sys.modules["scorer"] = scorer
_spec_s.loader.exec_module(scorer)

_spec_a = importlib.util.spec_from_file_location("analyzer", _BASE / "analyzer.py")
analyzer_mod = importlib.util.module_from_spec(_spec_a)
sys.modules["analyzer"] = analyzer_mod
_spec_a.loader.exec_module(analyzer_mod)

_spec_r = importlib.util.spec_from_file_location("runner", _BASE / "runner.py")
runner = importlib.util.module_from_spec(_spec_r)
sys.modules["runner"] = runner
_spec_r.loader.exec_module(runner)

_spec_tb = importlib.util.spec_from_file_location("task_bank", _BASE / "task_bank.py")
task_bank_mod = importlib.util.module_from_spec(_spec_tb)
sys.modules["task_bank"] = task_bank_mod
_spec_tb.loader.exec_module(task_bank_mod)

Task = task_bank_mod.Task
run_experiment = runner.run_experiment
_parse_stream_json_metrics = runner._parse_stream_json_metrics


class TestParseStreamJson(unittest.TestCase):
    """Test stream-json output parsing."""

    def test_empty_output(self):
        metrics = _parse_stream_json_metrics("")
        self.assertEqual(metrics["tokens_used"], 0)
        self.assertEqual(metrics["turn_count"], 1)  # min 1

    def test_usage_events(self):
        events = [
            json.dumps({"type": "assistant", "role": "assistant", "usage": {"input_tokens": 100, "output_tokens": 50}}),
            json.dumps({"type": "assistant", "role": "assistant", "usage": {"input_tokens": 80, "output_tokens": 30}}),
        ]
        output = "\n".join(events)
        metrics = _parse_stream_json_metrics(output)
        self.assertEqual(metrics["tokens_used"], 260)  # 100+50+80+30
        self.assertEqual(metrics["turn_count"], 2)

    def test_tool_errors(self):
        events = [
            json.dumps({"type": "tool_result", "is_error": True}),
            json.dumps({"type": "tool_result", "is_error": False}),
            json.dumps({"type": "tool_result", "is_error": True}),
        ]
        output = "\n".join(events)
        metrics = _parse_stream_json_metrics(output)
        self.assertEqual(metrics["error_count"], 2)

    def test_skill_invocations(self):
        events = [
            json.dumps({"type": "tool_use", "name": "Skill", "input": {"skill": "requirements"}}),
            json.dumps({"type": "tool_use", "name": "Skill", "input": {"skill": "generate-tests"}}),
            json.dumps({"type": "tool_use", "name": "Read", "input": {"file_path": "/foo"}}),
        ]
        output = "\n".join(events)
        metrics = _parse_stream_json_metrics(output)
        self.assertEqual(sorted(metrics["skills_invoked"]), ["generate-tests", "requirements"])

    def test_invalid_json_lines_skipped(self):
        output = "not json\n{\"type\": \"assistant\", \"role\": \"assistant\"}\ngarbage"
        metrics = _parse_stream_json_metrics(output)
        self.assertEqual(metrics["turn_count"], 1)


class TestRunExperiment(unittest.TestCase):
    """Test experiment execution with mocked subprocess."""

    def _make_task(self) -> Task:
        return Task(
            id="t1-test",
            tier=1,
            description="Write a test function",
            success_criteria=["Function exists", "Tests pass"],
            token_budget=500,
            expected_turns=3,
            setup_commands=[],
        )

    @patch("runner.subprocess.run")
    def test_completed_experiment(self, mock_run):
        """Headless experiment should complete with mocked claude."""
        mock_result = MagicMock()
        mock_result.stdout = json.dumps({"type": "assistant", "role": "assistant", "usage": {"input_tokens": 100, "output_tokens": 50}})
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        task = self._make_task()
        result = run_experiment(task, mode="headless")

        self.assertEqual(result.status, "completed")
        self.assertIsNotNone(result.scored)
        self.assertEqual(result.task_id, "t1-test")
        # /tmp dir should be cleaned up
        self.assertFalse(os.path.isdir(result.tmp_dir) if result.tmp_dir else True)

    @patch("runner.subprocess.run")
    def test_failed_experiment(self, mock_run):
        """Experiment should handle claude failures gracefully."""
        mock_run.side_effect = Exception("claude crashed")

        task = self._make_task()
        result = run_experiment(task, mode="headless")

        self.assertEqual(result.status, "failed")
        self.assertIn("crashed", result.failure_reason)

    def test_interactive_mode_placeholder(self):
        """Interactive mode should return a placeholder result."""
        task = self._make_task()
        result = run_experiment(task, mode="interactive")
        self.assertEqual(result.status, "completed")

    def test_invalid_mode_fails(self):
        """Unknown mode should fail."""
        task = self._make_task()
        result = run_experiment(task, mode="invalid")
        self.assertEqual(result.status, "failed")
        self.assertIn("Unknown mode", result.failure_reason)


class TestTmpCleanup(unittest.TestCase):
    """Test that /tmp directories are cleaned up."""

    @patch("runner.subprocess.run")
    def test_cleanup_on_success(self, mock_run):
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        task = Task(
            id="t1-test", tier=1, description="test",
            success_criteria=["pass"], token_budget=500, expected_turns=3,
            setup_commands=[],
        )
        result = run_experiment(task, mode="headless")
        if result.tmp_dir:
            self.assertFalse(os.path.isdir(result.tmp_dir))


if __name__ == "__main__":
    unittest.main()
