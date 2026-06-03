#!/usr/bin/env python3
"""Unit tests for hooks/guard-destructive-commands.py"""

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
    "guard_destructive_commands",
    REPO_ROOT / "hooks" / "guard-destructive-commands.py",
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class _HookTestBase(unittest.TestCase):
    """Base helper for running hook main() with mocked stdin."""

    def _run_hook(self, input_data: dict) -> int:
        """Run hook main() with mocked stdin, return exit code."""
        with unittest.mock.patch(
            "sys.stdin", io.StringIO(json.dumps(input_data))
        ), unittest.mock.patch("sys.stdout", new_callable=io.StringIO):
            try:
                mod.main()
                return 0
            except SystemExit as e:
                return e.code

    def _bash_input(self, command: str) -> dict:
        return {"tool_name": "Bash", "tool_input": {"command": command}}


class TestDestructiveRm(_HookTestBase):
    """True positives: recursive rm targeting critical paths."""

    def test_rm_rf_root(self):
        self.assertEqual(self._run_hook(self._bash_input("rm -rf /")), 2)

    def test_rm_rf_home(self):
        self.assertEqual(self._run_hook(self._bash_input("rm -rf ~")), 2)

    def test_rm_rf_etc(self):
        self.assertEqual(self._run_hook(self._bash_input("rm -rf /etc")), 2)

    def test_sudo_rm_rf_root(self):
        self.assertEqual(self._run_hook(self._bash_input("sudo rm -rf /")), 2)

    def test_rm_rf_usr(self):
        self.assertEqual(self._run_hook(self._bash_input("rm -rf /usr")), 2)

    def test_rm_recursive_flag_long(self):
        self.assertEqual(
            self._run_hook(self._bash_input("rm --recursive /")), 2
        )

    def test_rm_rf_var(self):
        self.assertEqual(self._run_hook(self._bash_input("rm -rf /var")), 2)

    def test_rm_rf_system(self):
        self.assertEqual(
            self._run_hook(self._bash_input("rm -rf /System")), 2
        )

    def test_rm_rf_with_glob(self):
        self.assertEqual(self._run_hook(self._bash_input("rm -rf /*")), 2)


class TestStaticRules(_HookTestBase):
    """True positives: static dangerous patterns."""

    def test_mkfs(self):
        self.assertEqual(
            self._run_hook(self._bash_input("mkfs.ext4 /dev/sda1")), 2
        )

    def test_dd_block_device(self):
        self.assertEqual(
            self._run_hook(
                self._bash_input("dd if=/dev/zero of=/dev/sda bs=1M")
            ),
            2,
        )

    def test_dd_nvme(self):
        self.assertEqual(
            self._run_hook(
                self._bash_input("dd if=/dev/zero of=/dev/nvme0n1 bs=1M")
            ),
            2,
        )

    def test_diskutil_erase(self):
        self.assertEqual(
            self._run_hook(
                self._bash_input("diskutil eraseDisk JHFS+ NewDisk disk2")
            ),
            2,
        )

    def test_fork_bomb(self):
        self.assertEqual(
            self._run_hook(self._bash_input(":(){ :|:& };:")), 2
        )

    def test_shred_block_device(self):
        self.assertEqual(
            self._run_hook(self._bash_input("shred -n 3 /dev/sda")), 2
        )

    def test_wipefs(self):
        self.assertEqual(
            self._run_hook(self._bash_input("wipefs -a /dev/sda")), 2
        )

    def test_truncate_etc_passwd(self):
        self.assertEqual(
            self._run_hook(self._bash_input("> /etc/passwd")), 2
        )

    def test_chmod_777_root(self):
        self.assertEqual(
            self._run_hook(self._bash_input("chmod -R 777 /")), 2
        )


class TestSafeCommands(_HookTestBase):
    """False positives: safe commands that must NOT be blocked."""

    def test_rm_single_file(self):
        self.assertEqual(
            self._run_hook(self._bash_input("rm /tmp/test.txt")), 0
        )

    def test_rm_rf_safe_dir(self):
        self.assertEqual(
            self._run_hook(self._bash_input("rm -rf /tmp/myproject/dist")), 0
        )

    def test_ls(self):
        self.assertEqual(self._run_hook(self._bash_input("ls -la /")), 0)

    def test_git_status(self):
        self.assertEqual(
            self._run_hook(self._bash_input("git status")), 0
        )

    def test_npm_install(self):
        self.assertEqual(
            self._run_hook(self._bash_input("npm install express")), 0
        )

    def test_dd_safe_target(self):
        self.assertEqual(
            self._run_hook(
                self._bash_input("dd if=/dev/zero of=/tmp/testfile bs=1M count=10")
            ),
            0,
        )

    def test_echo_command(self):
        self.assertEqual(
            self._run_hook(self._bash_input("echo 'hello world'")), 0
        )

    def test_mkdir(self):
        self.assertEqual(
            self._run_hook(self._bash_input("mkdir -p /tmp/newdir")), 0
        )


class TestEdgeCases(_HookTestBase):
    """Edge cases: invalid input, non-Bash tools, empty commands."""

    def test_empty_command(self):
        self.assertEqual(
            self._run_hook({"tool_name": "Bash", "tool_input": {"command": ""}}),
            0,
        )

    def test_non_bash_tool(self):
        self.assertEqual(
            self._run_hook({"tool_name": "Read", "tool_input": {"file_path": "/"}}),
            0,
        )

    def test_invalid_json_stdin(self):
        with unittest.mock.patch(
            "sys.stdin", io.StringIO("not json")
        ), unittest.mock.patch("sys.stdout", new_callable=io.StringIO):
            try:
                mod.main()
                code = 0
            except SystemExit as e:
                code = e.code
        self.assertEqual(code, 0)

    def test_empty_json_stdin(self):
        self.assertEqual(self._run_hook({}), 0)

    def test_missing_tool_input(self):
        self.assertEqual(self._run_hook({"tool_name": "Bash"}), 0)

    def test_chained_command_with_dangerous(self):
        """Dangerous command chained after safe command should still block."""
        self.assertEqual(
            self._run_hook(self._bash_input("echo hi; rm -rf /")), 2
        )


class TestCheckDestructiveRmUnit(unittest.TestCase):
    """Direct unit tests on check_destructive_rm function."""

    def test_returns_tuple(self):
        blocked, reason = mod.check_destructive_rm("rm -rf /")
        self.assertTrue(blocked)
        self.assertIn("/", reason)

    def test_safe_returns_false(self):
        blocked, reason = mod.check_destructive_rm("rm /tmp/file.txt")
        self.assertFalse(blocked)
        self.assertEqual(reason, "")


if __name__ == "__main__":
    unittest.main()
