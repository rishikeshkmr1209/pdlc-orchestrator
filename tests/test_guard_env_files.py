#!/usr/bin/env python3
"""Unit tests for hooks/guard-env-files.py"""

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
    "guard_env_files",
    REPO_ROOT / "hooks" / "guard-env-files.py",
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


class TestReadToolBlocked(_HookTestBase):
    """Read tool must be blocked for .env files."""

    def test_read_dot_env(self):
        self.assertEqual(
            self._run_hook({"tool_name": "Read", "tool_input": {"file_path": "/app/.env"}}),
            2,
        )

    def test_read_env_local(self):
        self.assertEqual(
            self._run_hook({"tool_name": "Read", "tool_input": {"file_path": "/app/.env.local"}}),
            2,
        )

    def test_read_env_production(self):
        self.assertEqual(
            self._run_hook({"tool_name": "Read", "tool_input": {"file_path": ".env.production"}}),
            2,
        )


class TestReadToolAllowed(_HookTestBase):
    """Read tool must be allowed for safe patterns."""

    def test_read_env_example(self):
        self.assertEqual(
            self._run_hook({"tool_name": "Read", "tool_input": {"file_path": "/app/.env.example"}}),
            0,
        )

    def test_read_env_sample(self):
        self.assertEqual(
            self._run_hook({"tool_name": "Read", "tool_input": {"file_path": ".env.sample"}}),
            0,
        )

    def test_read_env_template(self):
        self.assertEqual(
            self._run_hook({"tool_name": "Read", "tool_input": {"file_path": ".env.template"}}),
            0,
        )

    def test_read_normal_file(self):
        self.assertEqual(
            self._run_hook({"tool_name": "Read", "tool_input": {"file_path": "/app/config.ts"}}),
            0,
        )


class TestEditWriteBlocked(_HookTestBase):
    """Edit and Write tools must be blocked for .env files."""

    def test_edit_dot_env(self):
        self.assertEqual(
            self._run_hook({
                "tool_name": "Edit",
                "tool_input": {"file_path": "/app/.env", "old_string": "a", "new_string": "b"},
            }),
            2,
        )

    def test_write_dot_env(self):
        self.assertEqual(
            self._run_hook({
                "tool_name": "Write",
                "tool_input": {"file_path": "/app/.env", "content": "SECRET=x"},
            }),
            2,
        )


class TestBashBlocked(_HookTestBase):
    """Bash commands accessing .env must be blocked."""

    def test_cat_env(self):
        self.assertEqual(
            self._run_hook({"tool_name": "Bash", "tool_input": {"command": "cat .env"}}),
            2,
        )

    def test_source_env(self):
        self.assertEqual(
            self._run_hook({"tool_name": "Bash", "tool_input": {"command": "source .env"}}),
            2,
        )

    def test_command_substitution(self):
        self.assertEqual(
            self._run_hook({"tool_name": "Bash", "tool_input": {"command": "export $(cat .env)"}}),
            2,
        )

    def test_grep_env(self):
        self.assertEqual(
            self._run_hook({"tool_name": "Bash", "tool_input": {"command": "grep SECRET .env"}}),
            2,
        )

    def test_cp_env(self):
        self.assertEqual(
            self._run_hook({"tool_name": "Bash", "tool_input": {"command": "cp .env /tmp/"}}),
            2,
        )

    def test_git_add_env(self):
        self.assertEqual(
            self._run_hook({"tool_name": "Bash", "tool_input": {"command": "git add .env"}}),
            2,
        )

    def test_backtick_substitution(self):
        self.assertEqual(
            self._run_hook({"tool_name": "Bash", "tool_input": {"command": "echo `cat .env`"}}),
            2,
        )

    def test_redirect_from_env(self):
        self.assertEqual(
            self._run_hook({"tool_name": "Bash", "tool_input": {"command": "sort < .env"}}),
            2,
        )

    def test_docker_env_file(self):
        self.assertEqual(
            self._run_hook({"tool_name": "Bash", "tool_input": {"command": "docker run --env-file .env myimage"}}),
            2,
        )


class TestBashAllowed(_HookTestBase):
    """Bash commands that mention .env but don't access it must be allowed."""

    def test_ls_env(self):
        self.assertEqual(
            self._run_hook({"tool_name": "Bash", "tool_input": {"command": "ls .env"}}),
            0,
        )

    def test_stat_env(self):
        self.assertEqual(
            self._run_hook({"tool_name": "Bash", "tool_input": {"command": "stat .env"}}),
            0,
        )

    def test_test_f_env(self):
        self.assertEqual(
            self._run_hook({"tool_name": "Bash", "tool_input": {"command": "test -f .env"}}),
            0,
        )

    def test_git_commit_mentioning_env(self):
        self.assertEqual(
            self._run_hook({
                "tool_name": "Bash",
                "tool_input": {"command": "git commit -m 'add .env to gitignore'"},
            }),
            0,
        )

    def test_comment(self):
        self.assertEqual(
            self._run_hook({"tool_name": "Bash", "tool_input": {"command": "# .env is in gitignore"}}),
            0,
        )


class TestGlobBlocked(_HookTestBase):
    """Glob patterns targeting .env files must be blocked."""

    def test_glob_dot_env(self):
        self.assertEqual(
            self._run_hook({"tool_name": "Glob", "tool_input": {"pattern": "**/.env"}}),
            2,
        )

    def test_glob_env_star(self):
        self.assertEqual(
            self._run_hook({"tool_name": "Glob", "tool_input": {"pattern": "**/.env.*"}}),
            2,
        )


class TestGlobAllowed(_HookTestBase):
    """Glob patterns not targeting .env must be allowed."""

    def test_glob_ts_files(self):
        self.assertEqual(
            self._run_hook({"tool_name": "Glob", "tool_input": {"pattern": "**/*.ts"}}),
            0,
        )

    def test_glob_all_json(self):
        self.assertEqual(
            self._run_hook({"tool_name": "Glob", "tool_input": {"pattern": "*.json"}}),
            0,
        )


class TestEdgeCases(_HookTestBase):
    """Edge cases: invalid JSON, empty input, unknown tools."""

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

    def test_unknown_tool(self):
        self.assertEqual(
            self._run_hook({"tool_name": "CustomTool", "tool_input": {"file_path": ".env"}}),
            0,
        )

    def test_empty_file_path(self):
        self.assertEqual(
            self._run_hook({"tool_name": "Read", "tool_input": {"file_path": ""}}),
            0,
        )

    def test_empty_command(self):
        self.assertEqual(
            self._run_hook({"tool_name": "Bash", "tool_input": {"command": ""}}),
            0,
        )


class TestHelperFunctions(unittest.TestCase):
    """Direct unit tests on helper functions."""

    def test_is_env_filepath_dot_env(self):
        self.assertTrue(mod._is_env_filepath("/app/.env"))

    def test_is_env_filepath_env_local(self):
        self.assertTrue(mod._is_env_filepath("/app/.env.local"))

    def test_is_env_filepath_example_allowed(self):
        self.assertFalse(mod._is_env_filepath("/app/.env.example"))

    def test_is_env_filepath_sample_allowed(self):
        self.assertFalse(mod._is_env_filepath(".env.sample"))

    def test_is_env_filepath_template_allowed(self):
        self.assertFalse(mod._is_env_filepath(".env.template"))

    def test_is_env_filepath_empty(self):
        self.assertFalse(mod._is_env_filepath(""))

    def test_is_env_filepath_normal_file(self):
        self.assertFalse(mod._is_env_filepath("/app/config.ts"))


if __name__ == "__main__":
    unittest.main()
