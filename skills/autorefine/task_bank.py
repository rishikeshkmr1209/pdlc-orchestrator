#!/usr/bin/env python3
"""Autorefine Task Bank

Loads and validates task definitions from markdown files with YAML frontmatter.
Tasks define benchmark scenarios used to measure Claude Code skill quality.

Usage:
    python3 skills/autorefine/task_bank.py --validate           # Validate all tasks
    python3 skills/autorefine/task_bank.py --list               # List tasks sorted by tier
    python3 skills/autorefine/task_bank.py --validate --json    # JSON validation report

Exit codes:
    0 — All tasks valid / success
    1 — Validation errors found
"""

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_TASKS_DIR = Path(__file__).parent / "tasks"

REQUIRED_FRONTMATTER_FIELDS = {"id", "tier", "token_budget", "expected_turns"}

INTEGER_FIELDS = {"tier", "token_budget", "expected_turns"}


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class Task:
    """A benchmark task definition."""
    id: str
    tier: int
    description: str
    success_criteria: list[str]
    token_budget: int
    expected_turns: int
    setup_commands: list[str] = field(default_factory=list)
    file_path: str = ""


# ---------------------------------------------------------------------------
# Frontmatter parser (adapted from validate-skills.py)
# ---------------------------------------------------------------------------

def parse_frontmatter(content: str) -> tuple[dict | None, str]:
    """Extract and parse YAML frontmatter from markdown content.

    Returns (parsed_dict, body_after_frontmatter).
    Returns (None, content) if no valid frontmatter delimiters found.
    """
    stripped = content.lstrip("\ufeff")
    stripped = stripped.replace("\r\n", "\n")

    fm_match = re.match(r"^---[ \t]*\n(.*?)\n---[ \t]*(?:\n|$)", stripped, re.DOTALL)
    if not fm_match:
        return None, content

    fm_text = fm_match.group(1)
    body = stripped[fm_match.end():]

    result: dict = {}
    current_key: str | None = None
    current_value_lines: list[str] = []
    is_list = False

    def _flush() -> None:
        nonlocal current_key, current_value_lines, is_list
        if current_key is None:
            return
        if is_list:
            items = []
            for line in current_value_lines:
                item = line.strip()
                if item.startswith("- "):
                    items.append(item[2:].strip())
                elif item.startswith("-"):
                    items.append(item[1:].strip())
            result[current_key] = items
        else:
            result[current_key] = " ".join(
                line.strip() for line in current_value_lines if line.strip()
            )
        current_key = None
        current_value_lines = []
        is_list = False

    for line in fm_text.split("\n"):
        key_match = re.match(r"^([a-zA-Z_][a-zA-Z0-9_-]*)\s*:\s*(.*)", line)
        if key_match and not line.startswith((" ", "\t")):
            _flush()
            current_key = key_match.group(1)
            value = key_match.group(2).strip()
            if value:
                current_value_lines = [value]
        elif current_key and line.startswith((" ", "\t")):
            stripped_line = line.strip()
            if stripped_line.startswith("- "):
                is_list = True
            current_value_lines.append(line)

    _flush()
    return result, body


# ---------------------------------------------------------------------------
# Task parsing
# ---------------------------------------------------------------------------

def _extract_section(body: str, heading: str) -> str:
    """Extract content under a markdown ## heading."""
    pattern = rf"^##\s+{re.escape(heading)}\s*\n(.*?)(?=^##\s|\Z)"
    match = re.search(pattern, body, re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else ""


def _extract_checklist_items(text: str) -> list[str]:
    """Extract checklist items (- [ ] ...) from text."""
    items = []
    for line in text.split("\n"):
        line = line.strip()
        match = re.match(r"^-\s*\[[ x]\]\s*(.*)", line)
        if match:
            items.append(match.group(1).strip())
    return items


def _extract_code_blocks(text: str) -> list[str]:
    """Extract fenced code block contents from text."""
    blocks = []
    pattern = r"```(?:\w*)\n(.*?)```"
    for match in re.finditer(pattern, text, re.DOTALL):
        content = match.group(1).strip()
        if content:
            blocks.append(content)
    return blocks


def load_task(task_path: str) -> Task:
    """Parse a markdown task file and return a Task dataclass."""
    path = Path(task_path)
    content = path.read_text(encoding="utf-8")

    frontmatter, body = parse_frontmatter(content)
    if frontmatter is None:
        raise ValueError(f"No frontmatter found in {task_path}")

    # Validate required fields
    missing = REQUIRED_FRONTMATTER_FIELDS - set(frontmatter.keys())
    if missing:
        raise ValueError(f"Missing required fields in {task_path}: {', '.join(sorted(missing))}")

    # Parse integer fields
    for int_field in INTEGER_FIELDS:
        try:
            frontmatter[int_field] = int(frontmatter[int_field])
        except (ValueError, TypeError):
            raise ValueError(f"Field '{int_field}' must be an integer in {task_path}")

    # Extract body sections
    description = _extract_section(body, "Description")
    criteria_text = _extract_section(body, "Success Criteria")
    success_criteria = _extract_checklist_items(criteria_text)
    setup_text = _extract_section(body, "Setup Commands")
    setup_commands = _extract_code_blocks(setup_text)

    return Task(
        id=frontmatter["id"],
        tier=frontmatter["tier"],
        description=description,
        success_criteria=success_criteria,
        token_budget=frontmatter["token_budget"],
        expected_turns=frontmatter["expected_turns"],
        setup_commands=setup_commands,
        file_path=str(path),
    )


def list_tasks(tasks_dir: str | None = None) -> list[Task]:
    """Discover and load all tasks from a directory, sorted by tier."""
    dir_path = Path(tasks_dir) if tasks_dir else DEFAULT_TASKS_DIR
    if not dir_path.is_dir():
        return []

    tasks = []
    for md_file in sorted(dir_path.glob("*.md")):
        try:
            task = load_task(str(md_file))
            tasks.append(task)
        except ValueError:
            continue  # skip invalid tasks in listing mode

    tasks.sort(key=lambda t: t.tier)
    return tasks


def validate_task(task: Task) -> list[str]:
    """Return list of validation errors (empty = valid)."""
    errors = []
    if not task.id:
        errors.append("Task id is empty")
    if task.tier < 1 or task.tier > 5:
        errors.append(f"Tier must be 1-5, got {task.tier}")
    if not task.description:
        errors.append("Description is empty")
    if not task.success_criteria:
        errors.append("No success criteria defined")
    if task.token_budget <= 0:
        errors.append(f"Token budget must be positive, got {task.token_budget}")
    if task.expected_turns <= 0:
        errors.append(f"Expected turns must be positive, got {task.expected_turns}")
    return errors


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> int:
    """CLI for task bank operations."""
    parser = argparse.ArgumentParser(description="Autorefine Task Bank")
    parser.add_argument("--validate", action="store_true", help="Validate all tasks")
    parser.add_argument("--list", action="store_true", help="List tasks sorted by tier")
    parser.add_argument("--tasks-dir", type=str, default=None, help="Tasks directory")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    tasks_dir = args.tasks_dir or str(DEFAULT_TASKS_DIR)

    if args.validate:
        dir_path = Path(tasks_dir)
        if not dir_path.is_dir():
            print(f"Tasks directory not found: {tasks_dir}", file=sys.stderr)
            return 1

        all_errors: dict[str, list[str]] = {}
        for md_file in sorted(dir_path.glob("*.md")):
            try:
                task = load_task(str(md_file))
                errors = validate_task(task)
                if errors:
                    all_errors[str(md_file)] = errors
            except ValueError as e:
                all_errors[str(md_file)] = [str(e)]

        if args.json:
            print(json.dumps({"errors": all_errors, "valid": len(all_errors) == 0}))
        else:
            if all_errors:
                for path, errs in all_errors.items():
                    print(f"\n{path}:")
                    for err in errs:
                        print(f"  - {err}")
                print(f"\nValidation failed: {len(all_errors)} file(s) with errors")
            else:
                print("All tasks valid.")
        return 1 if all_errors else 0

    if args.list:
        tasks = list_tasks(tasks_dir)
        if args.json:
            print(json.dumps([asdict(t) for t in tasks], indent=2))
        else:
            for t in tasks:
                print(f"T{t.tier} | {t.id:<20s} | budget={t.token_budget} | turns={t.expected_turns}")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
