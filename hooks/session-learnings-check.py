#!/usr/bin/env python3
"""Session Learnings Check — Claude Code Stop Hook

Fires when Claude completes a task (Stop event). Reads the session
transcript JSONL file and scans user messages for signals that the user
had to repeat corrections or push for better behavior. If signals are
detected, outputs a reminder to run the /learnings skill.

This hook is lightweight — it only scans for patterns and prints a
suggestion. It does NOT modify any files.

Claude Code Stop hook stdin payload:
  {
    "session_id": "...",
    "transcript_path": "~/.claude/projects/.../session.jsonl",
    "cwd": "...",
    "permission_mode": "...",
    "hook_event_name": "Stop",
    "stop_hook_active": false,
    "last_assistant_message": "..."
  }

Based on research (arxiv:2602.11988): context file updates should be
minimal and surgical. This hook only nudges — the skill does the work.

Exit codes:
  0 — always (Stop hooks should never block)
"""

from __future__ import annotations

import json
import os
import sys

# ─────────────────────────────────────────────────────────────────────────────
# Learning signal patterns
# ─────────────────────────────────────────────────────────────────────────────

# Phrases that indicate the user had to correct or push the agent.
# Grouped by severity to prioritize the nudge message.
CORRECTION_SIGNALS: list[tuple[str, str]] = [
    # Direct repetition / frustration
    ("i already told you", "repeated_instruction"),
    ("i said", "repeated_instruction"),
    ("as i mentioned", "repeated_instruction"),
    ("like i said", "repeated_instruction"),
    ("i asked you to", "repeated_instruction"),
    ("again,", "repeated_instruction"),
    ("once more,", "repeated_instruction"),
    ("for the nth time", "repeated_instruction"),
    ("how many times", "repeated_instruction"),
    ("stop doing", "repeated_instruction"),
    ("don't do that", "repeated_instruction"),
    ("that's not what i", "repeated_instruction"),
    ("not what i asked", "repeated_instruction"),
    ("read my message", "repeated_instruction"),

    # Escalation / push for thoroughness
    ("think harder", "escalation"),
    ("think through", "escalation"),
    ("be more thorough", "escalation"),
    ("check everything", "escalation"),
    ("you missed", "escalation"),
    ("you forgot", "escalation"),
    ("you should have", "escalation"),
    ("why didn't you", "escalation"),
    ("that's incomplete", "escalation"),
    ("not enough", "escalation"),
    ("do it properly", "escalation"),
    ("do it right", "escalation"),
    ("more comprehensive", "escalation"),
    ("all of them", "escalation"),
    ("every single", "escalation"),
    ("cover all", "escalation"),
    ("instead me telling you again", "escalation"),

    # Tool / approach correction
    ("use osgrep", "tool_correction"),
    ("use podman", "tool_correction"),
    ("use trash", "tool_correction"),
    ("don't use rm", "tool_correction"),
    ("don't use grep", "tool_correction"),
    ("don't use docker", "tool_correction"),
    ("wrong tool", "tool_correction"),
    ("wrong approach", "tool_correction"),
    ("not the right way", "tool_correction"),

    # Workflow correction
    ("run the install", "workflow"),
    ("deploy it", "workflow"),
    ("make sure it works", "workflow"),
    ("test it", "workflow"),
    ("verify it", "workflow"),
    ("have you checked", "workflow"),
    ("did you run", "workflow"),
    ("is it working", "workflow"),
    ("will it continue to work", "workflow"),
]


def scan_for_signals(transcript: str) -> dict[str, int]:
    """Scan transcript text for learning signals.

    Returns a dict of signal_type -> count.
    """
    lower = transcript.lower()
    counts: dict[str, int] = {}
    for phrase, signal_type in CORRECTION_SIGNALS:
        if phrase in lower:
            counts[signal_type] = counts.get(signal_type, 0) + 1
    return counts


def build_nudge(counts: dict[str, int]) -> str | None:
    """Build a user-facing nudge message if signals warrant it."""
    total = sum(counts.values())
    if total == 0:
        return None

    parts = []
    if counts.get("repeated_instruction", 0) >= 1:
        parts.append("repeated corrections")
    if counts.get("escalation", 0) >= 1:
        parts.append("requests for more thoroughness")
    if counts.get("tool_correction", 0) >= 1:
        parts.append("tool/approach corrections")
    if counts.get("workflow", 0) >= 1:
        parts.append("workflow reminders")

    if not parts:
        return None

    signals = ", ".join(parts)
    return (
        "\n"
        "────────────────────────────────────────────────────────────────────\n"
        "  Session Learnings Detected\n"
        "────────────────────────────────────────────────────────────────────\n"
        "\n"
        f"  Signals: {signals} ({total} total)\n"
        "\n"
        "  Consider running /learnings to capture these as CLAUDE.md\n"
        "  instructions so future sessions don't repeat the same cycle.\n"
        "\n"
        "  Research (arxiv:2602.11988): keep instructions minimal —\n"
        "  only add what would prevent the specific mistake from recurring.\n"
        "────────────────────────────────────────────────────────────────────\n"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Transcript reading
# ─────────────────────────────────────────────────────────────────────────────

def _extract_user_messages(transcript_path: str) -> str:
    """Read the session JSONL transcript and extract user message text.

    The transcript is a JSONL file where each line is a JSON object.
    We look for entries with role="user" or type="human" and extract
    their text content. We only care about user messages because
    correction signals come from the user, not from Claude.

    We cap at 500KB of text to keep the hook fast.
    """
    expanded = os.path.expanduser(transcript_path)
    if not os.path.isfile(expanded):
        return ""

    parts: list[str] = []
    total_chars = 0
    max_chars = 500_000  # 500KB cap

    try:
        with open(expanded, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if total_chars >= max_chars:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if not isinstance(entry, dict):
                    continue

                # Claude Code transcript JSONL has various formats.
                # Extract text from user/human messages.
                role = entry.get("role", "").lower()
                msg_type = entry.get("type", "").lower()

                is_user = role in ("user", "human") or msg_type in ("human", "user")
                if not is_user:
                    continue

                # Text can be in "content", "text", or "message" fields
                for field in ("content", "text", "message"):
                    val = entry.get(field, "")
                    if isinstance(val, str) and val.strip():
                        parts.append(val)
                        total_chars += len(val)
                    elif isinstance(val, list):
                        # content can be a list of content blocks
                        for block in val:
                            if isinstance(block, str):
                                parts.append(block)
                                total_chars += len(block)
                            elif isinstance(block, dict):
                                txt = block.get("text", "") or block.get("content", "")
                                if txt:
                                    parts.append(txt)
                                    total_chars += len(txt)
    except (OSError, IOError):
        return ""

    return " ".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError, ValueError):
        sys.exit(0)

    if not isinstance(data, dict):
        sys.exit(0)

    # Prevent infinite loops: if a previous Stop hook already triggered
    # continuation, don't scan again.
    if data.get("stop_hook_active", False):
        sys.exit(0)

    # Primary source: read the full transcript JSONL for user messages
    transcript_path = data.get("transcript_path", "")
    transcript = ""

    if transcript_path:
        transcript = _extract_user_messages(transcript_path)

    # Fallback: scan last_assistant_message (unlikely to contain user
    # correction signals, but covers edge cases where the assistant
    # echoes user frustration)
    if not transcript.strip():
        transcript = data.get("last_assistant_message", "")

    if not transcript.strip():
        sys.exit(0)

    counts = scan_for_signals(transcript)
    nudge = build_nudge(counts)

    if nudge:
        # Print to stdout — Claude Code shows Stop hook stdout to the user
        print(nudge, flush=True)

    sys.exit(0)


if __name__ == "__main__":
    main()
