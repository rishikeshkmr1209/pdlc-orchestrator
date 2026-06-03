#!/usr/bin/env python3
"""Unit tests for hooks/eslint-on-save.py"""

import io
import json
import sys
import unittest
import unittest.mock
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "hooks"))

import importlib.util

spec = importlib.util.spec_from_file_location(
    "eslint_on_save",
    REPO_ROOT / "hooks" / "eslint-on-save.py",
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


class TestToolFiltering(_HookTestBase):
    """Only Write and Edit tools should be handled."""

    def test_non_write_tool_ignored(self):
        self.assertEqual(
            self._run_hook({"tool_name": "Read", "tool_input": {"file_path": "/app/index.ts"}}),
            0,
        )

    def test_bash_tool_ignored(self):
        self.assertEqual(
            self._run_hook({"tool_name": "Bash", "tool_input": {"command": "echo hi"}}),
            0,
        )

    def test_write_tool_accepted(self):
        """Write tool should be processed (not immediately rejected)."""
        # Will exit 0 because file doesn't exist, but it enters the handler
        self.assertEqual(
            self._run_hook({
                "tool_name": "Write",
                "tool_input": {"file_path": "/nonexistent/path/file.ts"},
            }),
            0,
        )

    def test_edit_tool_accepted(self):
        self.assertEqual(
            self._run_hook({
                "tool_name": "Edit",
                "tool_input": {"file_path": "/nonexistent/path/file.ts"},
            }),
            0,
        )


class TestExtensionFiltering(_HookTestBase):
    """Only JS/TS extensions should trigger linting."""

    def test_python_file_ignored(self):
        self.assertEqual(
            self._run_hook({
                "tool_name": "Write",
                "tool_input": {"file_path": "/app/script.py"},
            }),
            0,
        )

    def test_md_file_ignored(self):
        self.assertEqual(
            self._run_hook({
                "tool_name": "Write",
                "tool_input": {"file_path": "/app/README.md"},
            }),
            0,
        )

    def test_json_file_ignored(self):
        self.assertEqual(
            self._run_hook({
                "tool_name": "Write",
                "tool_input": {"file_path": "/app/config.json"},
            }),
            0,
        )


class TestLintableExtensions(unittest.TestCase):
    """Verify all expected extensions are in the LINTABLE_EXTENSIONS set."""

    def test_js_extensions(self):
        for ext in (".js", ".jsx", ".mjs", ".cjs"):
            self.assertIn(ext, mod.LINTABLE_EXTENSIONS, f"{ext} should be lintable")

    def test_ts_extensions(self):
        for ext in (".ts", ".tsx", ".mts", ".cts"):
            self.assertIn(ext, mod.LINTABLE_EXTENSIONS, f"{ext} should be lintable")


class TestFindEslint(unittest.TestCase):
    """Tests for ESLint discovery logic."""

    def test_returns_none_for_nonexistent_dir(self):
        result = mod.find_eslint(Path("/nonexistent/dir/file.ts"))
        # Should return None since no eslint is installed at that path
        # (may find system eslint though, so we just check it returns list or None)
        self.assertIn(type(result), (list, type(None)))


class TestRunEslint(unittest.TestCase):
    """Tests for ESLint runner with mocked subprocess."""

    @unittest.mock.patch("subprocess.run")
    def test_clean_file_returns_no_errors(self, mock_run):
        mock_run.return_value = unittest.mock.Mock(
            returncode=0, stdout="", stderr=""
        )
        has_errors, output = mod.run_eslint(["eslint"], Path("/app/file.ts"))
        self.assertFalse(has_errors)
        self.assertEqual(output, "")

    @unittest.mock.patch("subprocess.run")
    def test_error_file_returns_errors(self, mock_run):
        # First call (--fix): succeeds
        fix_result = unittest.mock.Mock(returncode=0, stdout="", stderr="")
        # Second call (check): fails with errors
        check_result = unittest.mock.Mock(
            returncode=1,
            stdout="/app/file.ts: line 5, col 1, Error - no-unused-vars",
            stderr="",
        )
        mock_run.side_effect = [fix_result, check_result]
        has_errors, output = mod.run_eslint(["eslint"], Path("/app/file.ts"))
        self.assertTrue(has_errors)
        self.assertIn("no-unused-vars", output)

    @unittest.mock.patch("subprocess.run", side_effect=FileNotFoundError)
    def test_eslint_not_found_fails_open(self, _):
        has_errors, output = mod.run_eslint(["eslint"], Path("/app/file.ts"))
        self.assertFalse(has_errors)

    @unittest.mock.patch(
        "subprocess.run", side_effect=unittest.mock.Mock(side_effect=Exception("timeout"))
    )
    def test_timeout_fails_open(self, mock_run):
        mock_run.side_effect = __import__("subprocess").TimeoutExpired("eslint", 60)
        has_errors, output = mod.run_eslint(["eslint"], Path("/app/file.ts"))
        self.assertFalse(has_errors)


class TestEdgeCases(_HookTestBase):
    """Edge cases: invalid JSON, empty input."""

    def test_invalid_json(self):
        with unittest.mock.patch(
            "sys.stdin", io.StringIO("not json")
        ), unittest.mock.patch("sys.stdout", new_callable=io.StringIO):
            try:
                mod.main()
                code = 0
            except SystemExit as e:
                code = e.code
        self.assertEqual(code, 0)

    def test_empty_input(self):
        self.assertEqual(self._run_hook({}), 0)

    def test_empty_file_path(self):
        self.assertEqual(
            self._run_hook({"tool_name": "Write", "tool_input": {"file_path": ""}}),
            0,
        )


if __name__ == "__main__":
    unittest.main()
