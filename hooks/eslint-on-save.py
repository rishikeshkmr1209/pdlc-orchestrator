#!/usr/bin/env python3
"""ESLint On-Save Hook — Claude Code PostToolUse Hook

Runs `eslint --fix` on any JS/TS file immediately after Claude writes
or edits it. Auto-fixable issues (formatting, simple rules) are
corrected silently. Errors that remain after --fix are printed to
stdout so Claude sees them in the same response turn and corrects
the code before finishing.

Supported tools: Write, Edit
Supported extensions: .js .ts .jsx .tsx .mjs .cjs .mts .cts

Exit codes (Claude Code hook contract):
  0 — file is clean (or not lintable), proceed normally
  2 — lint errors remain after --fix; output is fed back to Claude
"""

import json
import os
import subprocess
import sys
from pathlib import Path

LINTABLE_EXTENSIONS = {
    ".js", ".ts", ".jsx", ".tsx",
    ".mjs", ".cjs", ".mts", ".cts",
}


# ---------------------------------------------------------------------------
# ESLint discovery
# ---------------------------------------------------------------------------

def find_eslint(file_path: Path) -> list[str] | None:
    """
    Walk up from the file's directory to find the nearest ESLint binary.
    Prefers a locally-installed eslint in node_modules/.bin/ over a
    global one, which ensures the correct version and config are used.

    Returns a command list suitable for subprocess, or None if not found.
    """
    search_dirs = [file_path.parent, *file_path.parent.parents]

    for directory in search_dirs:
        # Locally-installed eslint (npm / pnpm / yarn workspaces)
        local_bin = directory / "node_modules" / ".bin" / "eslint"
        if local_bin.is_file():
            return [str(local_bin)]

        # package.json present — try npx so pnpm/yarn workspaces resolve correctly
        pkg = directory / "package.json"
        if pkg.is_file():
            try:
                with open(pkg) as f:
                    pkg_data = json.load(f)
                deps = {
                    **pkg_data.get("devDependencies", {}),
                    **pkg_data.get("dependencies", {}),
                }
                if "eslint" in deps:
                    return ["npx", "--yes", "eslint"]
            except (json.JSONDecodeError, OSError):
                pass

        # Stop searching once we hit a git root
        if (directory / ".git").is_dir():
            break

    # Fall back to system-installed eslint
    try:
        result = subprocess.run(
            ["which", "eslint"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return ["eslint"]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return None


# ---------------------------------------------------------------------------
# Lint runner
# ---------------------------------------------------------------------------

def run_eslint(eslint_cmd: list[str], file_path: Path) -> tuple[bool, str]:
    """
    Run eslint --fix, then re-check for remaining errors.

    Returns (has_errors: bool, error_output: str).
    """
    cwd = str(file_path.parent)

    # Pass 1: auto-fix (silently corrects formatting, simple rule violations)
    try:
        subprocess.run(
            eslint_cmd + ["--fix", str(file_path)],
            capture_output=True, text=True, timeout=60, cwd=cwd,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False, ""  # Can't run ESLint — fail open

    # Pass 2: report remaining errors in a compact, easy-to-read format
    try:
        check = subprocess.run(
            eslint_cmd + ["--format", "compact", str(file_path)],
            capture_output=True, text=True, timeout=60, cwd=cwd,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False, ""

    if check.returncode == 0:
        return False, ""

    output = (check.stdout or check.stderr or "").strip()
    return bool(output), output


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError, ValueError):
        sys.exit(0)

    # Only act on file-writing tools
    if data.get("tool_name") not in ("Write", "Edit"):
        sys.exit(0)

    raw_path: str = data.get("tool_input", {}).get("file_path", "")
    if not raw_path:
        sys.exit(0)

    file_path = Path(raw_path).resolve()

    if file_path.suffix not in LINTABLE_EXTENSIONS:
        sys.exit(0)

    if not file_path.exists():
        sys.exit(0)

    eslint_cmd = find_eslint(file_path)
    if not eslint_cmd:
        # No ESLint found in this project — skip silently
        sys.exit(0)

    has_errors, error_output = run_eslint(eslint_cmd, file_path)

    if not has_errors:
        sys.exit(0)

    print(
        f"ESLint: errors remain in {file_path} after auto-fix.\n"
        f"Fix the following issues before finishing:\n\n"
        f"{error_output}\n",
        flush=True,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
