#!/usr/bin/env python3
"""SDLC Pipeline — Context Monitor Hook (PostToolUse)

Monitors context window consumption by parsing the transcript JSONL file.
Emits warnings when context usage exceeds configured thresholds to prevent
quality degradation from context rot.

Thresholds (GSD-matched):
  - 65%: WARN  — consider compressing artifacts or delegating to subagents
  - 75%: CRITICAL — compress immediately or risk output quality degradation

Hook contract:
  - Receives JSON on stdin with: session_id, transcript_path, tool_name,
    tool_input, tool_response, tool_use_id
  - Exits 0 always (monitoring only, never blocks)
  - Prints warnings to stderr (shown to user as hook feedback)

NOTE: PostToolUse hooks do NOT receive context_window data directly.
This hook parses the transcript JSONL file to estimate context usage
from the most recent assistant turn's token counts.
"""

from __future__ import annotations

import json
import os
import sys

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

WARN_THRESHOLD = float(os.environ.get("CONTEXT_WARN_PCT", "65"))
CRITICAL_THRESHOLD = float(os.environ.get("CONTEXT_CRITICAL_PCT", "75"))

# Only check every N tool calls to avoid excessive file I/O
CHECK_INTERVAL = int(os.environ.get("CONTEXT_CHECK_INTERVAL", "5"))

# Context window size (configurable for different models)
MAX_CONTEXT_TOKENS = int(os.environ.get("CONTEXT_WINDOW_SIZE", "200000"))

# Max transcript file size to read (50MB safety limit)
MAX_TRANSCRIPT_SIZE = 50 * 1024 * 1024

# State file to track call count and read offset (avoids full re-parse)
STATE_DIR = os.path.join(
    os.environ.get("TMPDIR", "/tmp"), "claude-hooks"
)
STATE_FILE = os.path.join(STATE_DIR, ".context-monitor-state.json")


def load_state() -> dict:
    """Load persistent state (call counter)."""
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {"call_count": 0, "last_session": None}


def save_state(state: dict) -> None:
    """Save persistent state."""
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)
    except OSError:
        pass  # Non-critical — next call will just re-check


def estimate_context_usage(transcript_path: str) -> float | None:
    """Parse transcript JSONL to estimate context usage percentage.

    Looks for the most recent message with token usage information.
    Returns percentage (0-100) or None if unable to determine.
    """
    if not transcript_path or not os.path.exists(transcript_path):
        return None

    # Safety: skip files that are too large
    try:
        file_size = os.path.getsize(transcript_path)
        if file_size > MAX_TRANSCRIPT_SIZE:
            return None
    except OSError:
        return None

    last_usage = None

    try:
        with open(transcript_path, "r") as f:
            # Read only the last 64KB for efficiency on large transcripts
            if file_size > 65536:
                f.seek(max(0, file_size - 65536))
                f.readline()  # skip partial first line
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Look for token usage in message entries
                # Claude Code transcript entries may have usage info
                usage = None
                if isinstance(entry, dict):
                    usage = entry.get("usage")
                    if not usage and "message" in entry:
                        msg = entry["message"]
                        if isinstance(msg, dict):
                            usage = msg.get("usage")

                if usage and isinstance(usage, dict):
                    input_tokens = usage.get("input_tokens", 0)
                    cache_read = usage.get("cache_read_input_tokens", 0)
                    cache_creation = usage.get("cache_creation_input_tokens", 0)
                    output_tokens = usage.get("output_tokens", 0)

                    # Context consumption = input + cache tokens (not output)
                    total_used = input_tokens + cache_read + cache_creation
                    if total_used > 0:
                        last_usage = {
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                            "cache_read": cache_read,
                            "cache_creation": cache_creation,
                            "total_used": total_used,
                        }
    except OSError:
        return None

    if not last_usage:
        return None

    pct = (last_usage["total_used"] / MAX_CONTEXT_TOKENS) * 100
    return min(pct, 100.0)


def main() -> int:
    """Hook entry point."""
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0  # Can't parse input — exit silently

    session_id = hook_input.get("session_id", "")
    transcript_path = hook_input.get("transcript_path", "")

    # Load state and check if we should run this time
    state = load_state()

    # Reset counter on new session
    if state.get("last_session") != session_id:
        state = {"call_count": 0, "last_session": session_id}

    state["call_count"] = state.get("call_count", 0) + 1

    # Only check every N calls
    if state["call_count"] % CHECK_INTERVAL != 0:
        save_state(state)
        return 0

    save_state(state)

    # Estimate context usage
    pct = estimate_context_usage(transcript_path)
    if pct is None:
        return 0  # Can't determine — exit silently

    # Emit warnings based on thresholds
    if pct >= CRITICAL_THRESHOLD:
        print(
            f"CONTEXT CRITICAL ({pct:.0f}%): Context window is {pct:.0f}% consumed. "
            f"Quality degradation is likely. Consider:\n"
            f"  - Delegate remaining work to subagents (Task tool)\n"
            f"  - Compress artifact-digest.md and re-read instead of full artifacts\n"
            f"  - Save checkpoint and resume in a fresh session",
            file=sys.stderr,
        )
    elif pct >= WARN_THRESHOLD:
        print(
            f"CONTEXT WARNING ({pct:.0f}%): Context window is {pct:.0f}% consumed. "
            f"Consider compressing artifacts or delegating to subagents.",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
