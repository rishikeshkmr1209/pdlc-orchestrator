#!/usr/bin/env python3
""".env File Guard — Claude Code PreToolUse Hook

Prevents Claude from reading, writing, editing, or executing commands that
access .env files. These files contain secrets and should never be read by
the agent.

Covers:
  - Read tool:  blocks file_path targeting .env files
  - Edit tool:  blocks file_path targeting .env files
  - Write tool: blocks file_path targeting .env files
  - Bash tool:  blocks commands that read, cat, source, pipe, redirect,
                grep, or otherwise access .env file contents
  - Glob tool:  blocks patterns specifically targeting .env files

PreToolUse hook contract:
  stdin  — JSON with tool_name and tool_input
  exit 0 — allow
  exit 2 — block (stdout fed back to Claude as context)
"""

from __future__ import annotations

import json
import os
import re
import sys


# ─────────────────────────────────────────────────────────────────────────────
# .env filename detection
# ─────────────────────────────────────────────────────────────────────────────

# Matches .env files: .env, .env.local, .env.production, .env.dev, etc.
# Also matches paths ending in /.env or containing /.env.something
_ENV_FILE_RE = re.compile(
    r"(?:^|/)\.env(?:\.[a-zA-Z0-9_.-]+)?$"
)

# For bash commands: detect .env filenames as standalone tokens or arguments
# Matches: .env, ./.env, path/to/.env, .env.local, .env.production, etc.
_ENV_IN_CMD_RE = re.compile(
    r"(?:^|\s|=|'|\"|<|>|\||\(|`)"      # preceded by whitespace, =, quotes, redirects, pipe, (, `
    r"("
    r"(?:[^\s'\"<>|&;()`]*/)?"          # optional path prefix
    r"\.env"                             # .env
    r"(?:\.[a-zA-Z0-9_.-]+)?"           # optional .local, .production, etc.
    r")"
    r"(?:\s|$|'|\"|<|>|\|;|&|\)|`)",    # followed by whitespace, EOL, quotes, redirects, ), `, etc.
)

# Commands that read file contents
_READ_COMMANDS = (
    r"\bcat\b", r"\bless\b", r"\bmore\b", r"\bhead\b", r"\btail\b",
    r"\bbatcat\b", r"\bbat\b", r"\bnl\b", r"\bod\b", r"\bxxd\b",
    r"\bstrings\b", r"\bfile\b",
    r"\bsed\b", r"\bawk\b", r"\bperl\b",
    r"\bsource\b", r"\.\s",  # source / dot command
    r"\bgrep\b", r"\begrep\b", r"\bfgrep\b", r"\brg\b", r"\bag\b",
    r"\bsort\b", r"\buniq\b", r"\bwc\b", r"\bcut\b", r"\bpaste\b",
    r"\btr\b", r"\brev\b", r"\bfold\b", r"\bfmt\b",
    r"\bcp\b", r"\bmv\b", r"\brsync\b",
    r"\bvi\b", r"\bvim\b", r"\bnvim\b", r"\bnano\b", r"\bemacs\b",
    r"\bcode\b", r"\bopen\b",
    r"\bpython3?\b", r"\bnode\b", r"\bruby\b",
    r"\bexport\b",  # export $(cat .env)
    r"\benv\b",     # env $(cat .env)
    r"\bxargs\b",   # xargs < .env
    r"\btee\b",     # tee .env
    r"\bdiff\b", r"\bcomm\b", r"\bcmp\b",
    r"\bjq\b", r"\byq\b",
    r"\bcurl\b",    # curl -d @.env
    r"\bscp\b", r"\bsftp\b",  # copying .env remotely
    r"\bdocker\b",  # docker run --env-file .env
    r"\bpodman\b",  # podman run --env-file .env
    r"\bkubectl\b",  # kubectl create secret from .env
)

# Shell redirection/piping patterns with .env
_REDIRECT_PATTERNS = (
    r"<\s*(?:[^\s]*\/)?\.env",           # < .env, < path/.env
    r"\.env\s*\|",                        # .env | pipe
    r"\|\s*.*\.env",                      # pipe to something involving .env
    r"\$\(.*\.env.*\)",                   # $(cat .env) command substitution
    r"`[^`]*\.env[^`]*`",                # `cat .env` backtick substitution
)


def _is_env_filepath(path: str) -> bool:
    """Check if a file path points to a .env file (not .env.example)."""
    if not path:
        return False
    basename = os.path.basename(path.rstrip("/"))
    # Allow .env.example, .env.sample, .env.template — these are safe
    if re.search(r"\.env\.(?:example|sample|template)$", basename, re.IGNORECASE):
        return False
    return bool(_ENV_FILE_RE.search("/" + basename))


def _is_env_filepath_in_args(args: str) -> bool:
    """Check if any space-separated arg is an .env file path."""
    for token in args.split():
        # Strip quotes
        token = token.strip("'\"")
        if _is_env_filepath(token):
            return True
    return False


def _block(reason: str, tool: str, detail: str = "") -> None:
    msg = (
        f"BLOCKED by .env File Guard\n"
        f"Reason : {reason}\n"
        f"Tool   : {tool}\n"
    )
    if detail:
        msg += f"Detail : {detail!r}\n"
    msg += (
        f"\n"
        f".env files contain secrets and must not be accessed by Claude.\n"
        f"If you need environment variable values, ask the user to provide\n"
        f"specific (non-secret) values, or read .env.example instead."
    )
    print(msg, flush=True)
    sys.exit(2)


# ─────────────────────────────────────────────────────────────────────────────
# Tool-specific checks
# ─────────────────────────────────────────────────────────────────────────────

def check_file_tool(tool_name: str, tool_input: dict) -> None:
    """Check Read, Edit, Write tools for .env file access."""
    file_path = tool_input.get("file_path", "")
    if _is_env_filepath(file_path):
        _block(f"direct {tool_name} of .env file", tool_name, file_path)


def check_bash(tool_input: dict) -> None:
    """Check Bash commands for .env file access."""
    command: str = tool_input.get("command", "")
    if not command:
        return

    # Check for .env filename anywhere in the command
    env_match = _ENV_IN_CMD_RE.search(command)
    if not env_match:
        # Also check without strict boundary (catches edge cases)
        if not re.search(r"\.env(?:\.[a-zA-Z0-9_.-]+)?(?:\s|$|'|\"|;|&|\|)", command):
            return

    # At this point .env appears in the command — check if it's being accessed
    # Allow: echo ".env", creating .env.example, gitignore patterns, comments
    # Block: anything that reads, writes, copies, or pipes .env content

    # Skip if the entire command is just a comment
    stripped = command.strip()
    if stripped.startswith("#"):
        return

    # Allow: git commit/log/tag messages that mention .env (just text, not file access)
    if re.match(r"^\s*git\s+(?:commit|log|tag|show|shortlog|whatchanged)\b", stripped):
        return

    # Allow: git add/rm/checkout of non-.env files (the .env in args is just a string)
    # But block: git add .env, git checkout .env (actual .env file operations)
    git_match = re.match(r"^\s*git\s+(add|rm|checkout|restore|stash)\s+(.+)", stripped)
    if git_match:
        git_args = git_match.group(2)
        # Only block if an actual .env file is a direct argument
        if _is_env_filepath_in_args(git_args):
            _block("git command targeting .env file", "Bash", command)
        return

    # Check command substitution FIRST — these are always dangerous regardless
    # of the outer command (e.g., export $(cat .env), echo $(cat .env))
    if re.search(r"\$\([^)]*\.env(?:\.[a-zA-Z0-9_.-]+)?[^)]*\)", command):
        _block("command substitution accessing .env file", "Bash", command)
    if re.search(r"`[^`]*\.env(?:\.[a-zA-Z0-9_.-]+)?[^`]*`", command):
        _block("backtick substitution accessing .env file", "Bash", command)

    # Check shell redirections and pipes involving .env — also always dangerous
    for pattern in _REDIRECT_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            _block("shell redirect/pipe accessing .env file", "Bash", command)

    # Allow: echo/printf that just mentions .env in a string (not redirecting to it)
    # e.g., echo "add .env to gitignore"
    if re.match(r"^\s*(?:echo|printf)\s+['\"].*\.env.*['\"]\s*$", command):
        return

    # Allow: git commands that reference .env in gitignore context
    if re.match(r"^\s*(?:git\s+(?:add|rm|checkout|show)\s+\.gitignore)", command):
        return

    # Allow: ls / stat / test -f (checking existence, not reading content)
    if re.match(r"^\s*(?:ls|stat|test)\b", stripped):
        return

    # Allow: touch .env.example, cp .env.example (example files are safe)
    if re.search(r"\.env\.(?:example|sample|template)\b", command, re.IGNORECASE) and \
       not re.search(r"\.env(?!\.[a-zA-Z])", command):
        return

    # Check commands that read file contents + .env reference
    for cmd_pattern in _READ_COMMANDS:
        if re.search(cmd_pattern, command, re.IGNORECASE):
            _block("command accessing .env file contents", "Bash", command)

    # If .env is in the command and none of the safe patterns matched,
    # and it's not just mentioned in a string, block it conservatively
    _block(".env file referenced in command", "Bash", command)


def check_glob(tool_input: dict) -> None:
    """Check Glob patterns that specifically target .env files."""
    pattern = tool_input.get("pattern", "")
    if not pattern:
        return

    # Block glob patterns specifically hunting for .env files
    # e.g., **/.env, **/.env.*, .env, .env.*
    if re.search(r"(?:^|\*\*/?)\.env(?:\.\*|\.[a-zA-Z]+)?$", pattern):
        _block("glob pattern targeting .env files", "Glob", pattern)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError, ValueError):
        sys.exit(0)

    tool_name: str = data.get("tool_name", "")
    tool_input: dict = data.get("tool_input", {})

    if tool_name in ("Read", "Edit", "Write"):
        check_file_tool(tool_name, tool_input)
    elif tool_name == "Bash":
        check_bash(tool_input)
    elif tool_name == "Glob":
        check_glob(tool_input)

    sys.exit(0)


if __name__ == "__main__":
    main()
