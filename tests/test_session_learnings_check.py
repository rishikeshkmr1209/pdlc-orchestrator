#!/usr/bin/env python3
"""Unit tests for hooks/session-learnings-check.py"""

import io
import json
import os
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "hooks"))

import importlib.util

spec = importlib.util.spec_from_file_location(
    "session_learnings_check",
    REPO_ROOT / "hooks" / "session-learnings-check.py",
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class _HookTestBase(unittest.TestCase):
    """Base helper for running hook main() with mocked stdin."""

    def _run_hook(self, input_data: dict) -> int:
        with unittest.mock.patch(
            "sys.stdin", io.StringIO(json.dumps(input_data))
        ), unittest.mock.patch("sys.stdout", new_callable=io.StringIO):
            try:
                mod.main()
                return 0
            except SystemExit as e:
                return e.code


class TestAlwaysExitZero(_HookTestBase):
    """Stop hooks must ALWAYS exit 0, never block."""

    def test_empty_input_exits_zero(self):
        self.assertEqual(self._run_hook({}), 0)

    def test_invalid_json_exits_zero(self):
        with unittest.mock.patch(
            "sys.stdin", io.StringIO("not json")
        ), unittest.mock.patch("sys.stdout", new_callable=io.StringIO):
            try:
                mod.main()
                code = 0
            except SystemExit as e:
                code = e.code
        self.assertEqual(code, 0)

    def test_stop_hook_active_exits_zero(self):
        """When stop_hook_active is True, should exit immediately."""
        self.assertEqual(
            self._run_hook({"stop_hook_active": True, "transcript_path": "/fake"}),
            0,
        )

    def test_no_transcript_exits_zero(self):
        self.assertEqual(
            self._run_hook({"transcript_path": ""}),
            0,
        )

    def test_missing_transcript_file_exits_zero(self):
        self.assertEqual(
            self._run_hook({"transcript_path": "/nonexistent/path/session.jsonl"}),
            0,
        )


class TestScanForSignals(unittest.TestCase):
    """Direct unit tests on scan_for_signals function."""

    def test_no_signals_in_clean_text(self):
        counts = mod.scan_for_signals("How do I write a for loop?")
        self.assertEqual(sum(counts.values()), 0)

    def test_repeated_instruction_detected(self):
        counts = mod.scan_for_signals("I already told you to use TypeScript")
        self.assertIn("repeated_instruction", counts)
        self.assertGreater(counts["repeated_instruction"], 0)

    def test_escalation_detected(self):
        counts = mod.scan_for_signals("Think harder about this problem")
        self.assertIn("escalation", counts)

    def test_tool_correction_detected(self):
        counts = mod.scan_for_signals("Use osgrep instead of grep")
        self.assertIn("tool_correction", counts)

    def test_workflow_detected(self):
        counts = mod.scan_for_signals("Did you run the tests?")
        self.assertIn("workflow", counts)

    def test_multiple_signals(self):
        text = "I already told you to think harder and use osgrep. Did you run the tests?"
        counts = mod.scan_for_signals(text)
        self.assertGreaterEqual(len(counts), 3)

    def test_case_insensitive(self):
        counts = mod.scan_for_signals("I ALREADY TOLD YOU")
        self.assertIn("repeated_instruction", counts)


class TestBuildNudge(unittest.TestCase):
    """Tests for nudge message generation."""

    def test_empty_counts_returns_none(self):
        self.assertIsNone(mod.build_nudge({}))

    def test_zero_counts_returns_none(self):
        self.assertIsNone(mod.build_nudge({"repeated_instruction": 0}))

    def test_repeated_instruction_nudge(self):
        nudge = mod.build_nudge({"repeated_instruction": 2})
        self.assertIsNotNone(nudge)
        self.assertIn("repeated corrections", nudge)
        self.assertIn("/learnings", nudge)

    def test_escalation_nudge(self):
        nudge = mod.build_nudge({"escalation": 1})
        self.assertIsNotNone(nudge)
        self.assertIn("thoroughness", nudge)

    def test_tool_correction_nudge(self):
        nudge = mod.build_nudge({"tool_correction": 1})
        self.assertIsNotNone(nudge)
        self.assertIn("tool/approach", nudge)

    def test_workflow_nudge(self):
        nudge = mod.build_nudge({"workflow": 1})
        self.assertIsNotNone(nudge)
        self.assertIn("workflow", nudge)

    def test_multiple_signals_all_mentioned(self):
        nudge = mod.build_nudge({
            "repeated_instruction": 1,
            "escalation": 2,
            "tool_correction": 1,
        })
        self.assertIn("repeated corrections", nudge)
        self.assertIn("thoroughness", nudge)
        self.assertIn("tool/approach", nudge)
        self.assertIn("4 total", nudge)


class TestExtractUserMessages(unittest.TestCase):
    """Tests for JSONL transcript parsing."""

    def test_extracts_user_messages(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write(json.dumps({"role": "user", "content": "Hello world"}) + "\n")
            f.write(json.dumps({"role": "assistant", "content": "Hi there"}) + "\n")
            f.write(json.dumps({"role": "user", "content": "Think harder"}) + "\n")
            f.flush()
            result = mod._extract_user_messages(f.name)
        os.unlink(f.name)
        self.assertIn("Hello world", result)
        self.assertIn("Think harder", result)
        self.assertNotIn("Hi there", result)

    def test_handles_content_list(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write(json.dumps({
                "role": "user",
                "content": [{"type": "text", "text": "I already told you"}],
            }) + "\n")
            f.flush()
            result = mod._extract_user_messages(f.name)
        os.unlink(f.name)
        self.assertIn("I already told you", result)

    def test_handles_malformed_lines(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write("not valid json\n")
            f.write(json.dumps({"role": "user", "content": "valid"}) + "\n")
            f.flush()
            result = mod._extract_user_messages(f.name)
        os.unlink(f.name)
        self.assertIn("valid", result)

    def test_nonexistent_file_returns_empty(self):
        result = mod._extract_user_messages("/nonexistent/path/session.jsonl")
        self.assertEqual(result, "")

    def test_empty_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.flush()
            result = mod._extract_user_messages(f.name)
        os.unlink(f.name)
        self.assertEqual(result, "")


class TestWithTranscript(_HookTestBase):
    """Integration: hook with a real transcript file."""

    def test_signals_produce_output(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write(json.dumps({"role": "user", "content": "I already told you to think harder"}) + "\n")
            f.flush()
            with unittest.mock.patch(
                "sys.stdin",
                io.StringIO(json.dumps({"transcript_path": f.name})),
            ):
                captured = io.StringIO()
                with unittest.mock.patch("sys.stdout", captured):
                    try:
                        mod.main()
                        code = 0
                    except SystemExit as e:
                        code = e.code
        os.unlink(f.name)
        self.assertEqual(code, 0)
        # Should have printed a nudge
        self.assertIn("/learnings", captured.getvalue())


if __name__ == "__main__":
    unittest.main()
