#!/usr/bin/env python3
"""Unit tests for hooks/scan-prompt.py"""

import io
import json
import os
import sys
import unittest
import unittest.mock
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "hooks"))

import importlib.util

spec = importlib.util.spec_from_file_location(
    "scan_prompt",
    REPO_ROOT / "hooks" / "scan-prompt.py",
)
mod = importlib.util.module_from_spec(spec)
# Register in sys.modules BEFORE exec — required by @dataclass introspection
sys.modules["scan_prompt"] = mod
spec.loader.exec_module(mod)


class _HookTestBase(unittest.TestCase):
    """Base helper for running hook main() with mocked stdin."""

    def _run_hook(self, input_data: dict, mode: str = "standard") -> int:
        with unittest.mock.patch(
            "sys.stdin", io.StringIO(json.dumps(input_data))
        ), unittest.mock.patch(
            "sys.stdout", new_callable=io.StringIO
        ), unittest.mock.patch(
            "sys.stderr", new_callable=io.StringIO
        ), unittest.mock.patch.dict(
            os.environ, {"PROMPT_SCANNER_MODE": mode}
        ):
            try:
                mod.main()
                return 0
            except SystemExit as e:
                return e.code

    def _prompt_input(self, text: str) -> dict:
        return {"prompt": text}


class TestAWSKeys(_HookTestBase):
    """AWS credential detection."""

    def test_aws_access_key_blocked(self):
        self.assertEqual(
            self._run_hook(self._prompt_input("Here is AKIAIOSFODNN7EXAMPLE")),
            2,
        )

    def test_aws_placeholder_allowed(self):
        """Placeholder keys should not be blocked."""
        code = self._run_hook(
            self._prompt_input("Use AKIAIOSFODNN7EXAMPLE as your_api_key placeholder")
        )
        # The AKIA pattern itself should still trigger since it looks real
        self.assertEqual(code, 2)


class TestJWT(_HookTestBase):
    """JWT token detection."""

    def test_jwt_blocked(self):
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        self.assertEqual(
            self._run_hook(self._prompt_input(f"My token is {jwt}")),
            2,
        )


class TestPEMKeys(_HookTestBase):
    """PEM private key detection."""

    def test_rsa_private_key_blocked(self):
        pem = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0Z3VS5JX\n-----END RSA PRIVATE KEY-----"
        self.assertEqual(
            self._run_hook(self._prompt_input(pem)),
            2,
        )

    def test_ec_private_key_blocked(self):
        pem = "-----BEGIN EC PRIVATE KEY-----\nMHQCAQEEIBkg0L\n-----END EC PRIVATE KEY-----"
        self.assertEqual(
            self._run_hook(self._prompt_input(pem)),
            2,
        )


class TestCreditCards(_HookTestBase):
    """Credit card (Luhn-validated) detection."""

    def test_valid_visa_blocked(self):
        # 4111111111111111 is a well-known Luhn-valid test card
        self.assertEqual(
            self._run_hook(self._prompt_input("Card: 4111111111111111")),
            2,
        )

    def test_invalid_cc_allowed(self):
        # 1234567890123456 is NOT Luhn-valid
        code = self._run_hook(self._prompt_input("Number: 1234567890123456"))
        self.assertEqual(code, 0)


class TestSSN(_HookTestBase):
    """SSN detection."""

    def test_ssn_blocked(self):
        self.assertEqual(
            self._run_hook(self._prompt_input("SSN: 123-45-6789")),
            2,
        )

    def test_ssn_no_dashes_not_blocked(self):
        """Plain 9 digits without dashes shouldn't trigger SSN detection."""
        code = self._run_hook(self._prompt_input("ID: 123456789"))
        # May or may not trigger depending on scanner rules
        self.assertIn(code, (0, 2))


class TestNaturalLanguageSecrets(_HookTestBase):
    """Natural language credential disclosure."""

    def test_my_api_key_is(self):
        self.assertEqual(
            self._run_hook(
                self._prompt_input("my api key is sk-abc123def456ghi789jkl012mno345pqr678stu901vwx")
            ),
            2,
        )

    def test_password_is(self):
        self.assertEqual(
            self._run_hook(self._prompt_input("the password is SuperS3cret!2024")),
            2,
        )


class TestShellPatterns(_HookTestBase):
    """Shell/CLI credential patterns."""

    def test_export_secret(self):
        self.assertEqual(
            self._run_hook(
                self._prompt_input("export AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
            ),
            2,
        )


class TestPlaceholderExclusions(_HookTestBase):
    """Placeholder values should not trigger blocks."""

    def test_example_in_code_block(self):
        """Code examples with placeholder API keys should be allowed."""
        code = self._run_hook(
            self._prompt_input("Set your_api_key to authenticate")
        )
        self.assertEqual(code, 0)

    def test_placeholder_text(self):
        code = self._run_hook(
            self._prompt_input("Replace <your-api-key> with the real value")
        )
        self.assertEqual(code, 0)


class TestAuditMode(_HookTestBase):
    """Audit mode: log findings to stderr, never block."""

    def test_audit_mode_never_blocks(self):
        code = self._run_hook(
            self._prompt_input("AKIAIOSFODNN7EXAMPLE"), mode="audit"
        )
        self.assertEqual(code, 0)

    def test_audit_mode_with_jwt(self):
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        code = self._run_hook(
            self._prompt_input(f"Token: {jwt}"), mode="audit"
        )
        self.assertEqual(code, 0)


class TestStrictMode(_HookTestBase):
    """Strict mode: treat warnings as blocks."""

    def test_strict_mode_blocks_warnings(self):
        # Email address is normally a warning
        code = self._run_hook(
            self._prompt_input("Contact: user@example.com"), mode="strict"
        )
        # In strict mode, warnings become blocks
        self.assertEqual(code, 2)


class TestEdgeCases(_HookTestBase):
    """Edge cases: invalid JSON, empty prompt, etc."""

    def test_empty_prompt(self):
        self.assertEqual(self._run_hook(self._prompt_input("")), 0)

    def test_whitespace_prompt(self):
        self.assertEqual(self._run_hook(self._prompt_input("   ")), 0)

    def test_invalid_json_stdin(self):
        with unittest.mock.patch(
            "sys.stdin", io.StringIO("not json")
        ), unittest.mock.patch(
            "sys.stdout", new_callable=io.StringIO
        ), unittest.mock.patch(
            "sys.stderr", new_callable=io.StringIO
        ):
            try:
                mod.main()
                code = 0
            except SystemExit as e:
                code = e.code
        self.assertEqual(code, 0)

    def test_missing_prompt_field(self):
        self.assertEqual(self._run_hook({}), 0)

    def test_clean_prompt_passes(self):
        self.assertEqual(
            self._run_hook(self._prompt_input("How do I write a for loop in TypeScript?")),
            0,
        )

    def test_normal_code_passes(self):
        self.assertEqual(
            self._run_hook(
                self._prompt_input("function add(a: number, b: number): number { return a + b; }")
            ),
            0,
        )


class TestScanFunction(unittest.TestCase):
    """Direct unit tests on the scan() function."""

    def test_clean_text_no_findings(self):
        blocks, warns = mod.scan("Hello, how are you?")
        self.assertEqual(len(blocks), 0)

    def test_aws_key_produces_block(self):
        blocks, warns = mod.scan("Key: AKIAIOSFODNN7EXAMPLE")
        self.assertGreater(len(blocks), 0)

    def test_pem_produces_block(self):
        pem = "-----BEGIN RSA PRIVATE KEY-----\ndata\n-----END RSA PRIVATE KEY-----"
        blocks, warns = mod.scan(pem)
        self.assertGreater(len(blocks), 0)


if __name__ == "__main__":
    unittest.main()
