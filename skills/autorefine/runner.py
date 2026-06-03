#!/usr/bin/env python3
"""Autorefine Experiment Runner

Executes a single experiment: creates a /tmp project, runs a task via Claude,
collects metrics, and cleans up.

Usage:
    python3 skills/autorefine/runner.py --task <path> --mode headless
    python3 skills/autorefine/runner.py --help

Exit codes:
    0 — Success
    1 — Error
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

# Dynamic import of sibling modules
_MODULE_DIR = Path(__file__).resolve().parent


def _import_module(name: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, _MODULE_DIR / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


task_bank = _import_module("task_bank")
scorer_mod = _import_module("scorer")

Task = task_bank.Task
ExperimentMetrics = scorer_mod.ExperimentMetrics
ScoredResult = scorer_mod.ScoredResult

# Import analyzer types
analyzer_mod = _import_module("analyzer")
ExperimentResult = analyzer_mod.ExperimentResult
SkillInvocation = analyzer_mod.SkillInvocation


# ---------------------------------------------------------------------------
# Experiment execution
# ---------------------------------------------------------------------------

def _create_tmp_project(task: Task) -> str:
    """Create a temporary project directory and run setup commands."""
    tmp_dir = tempfile.mkdtemp(prefix="autorefine-")

    for cmd in task.setup_commands:
        subprocess.run(
            cmd,
            shell=True,
            cwd=tmp_dir,
            capture_output=True,
            timeout=60,
        )

    return tmp_dir


def _parse_stream_json_metrics(output: str) -> dict:
    """Parse stream-json output from `claude -p` for metrics.

    Looks for usage data in message events. Falls back to defaults
    if fields are missing (ARCH-002 fallback strategy).
    """
    tokens_used = 0
    turn_count = 0
    error_count = 0
    skills_invoked: list[str] = []

    for line in output.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        event_type = event.get("type", "")

        # Count assistant messages as turns
        if event_type == "assistant" or event.get("role") == "assistant":
            turn_count += 1

        # Extract token usage from message events
        usage = event.get("usage", {})
        if usage:
            tokens_used += usage.get("input_tokens", 0)
            tokens_used += usage.get("output_tokens", 0)

        # Track tool use for skill invocations
        if event_type == "tool_use":
            tool_name = event.get("name", "")
            if tool_name == "Skill":
                skill_input = event.get("input", {})
                skill_name = skill_input.get("skill", "unknown")
                if skill_name not in skills_invoked:
                    skills_invoked.append(skill_name)

        # Count tool errors
        if event_type == "tool_result" and event.get("is_error", False):
            error_count += 1

    return {
        "tokens_used": tokens_used,
        "turn_count": max(turn_count, 1),  # at least 1 turn
        "error_count": error_count,
        "skills_invoked": skills_invoked,
    }


def _run_headless(task: Task, tmp_dir: str) -> dict:
    """Run task via `claude -p --output-format stream-json`."""
    prompt = (
        f"You are in directory {tmp_dir}. Complete this task:\n\n"
        f"{task.description}\n\n"
        f"Success criteria:\n"
        + "\n".join(f"- {c}" for c in task.success_criteria)
    )

    try:
        result = subprocess.run(
            ["claude", "-p", "--output-format", "stream-json", prompt],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            cwd=tmp_dir,
        )
        metrics = _parse_stream_json_metrics(result.stdout)
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        # claude not available or timed out
        metrics = {
            "tokens_used": 0,
            "turn_count": 1,
            "error_count": 1,
            "skills_invoked": [],
        }
        sys.stderr.write(f"Warning: headless execution failed: {e}\n")

    return metrics


_SOURCE_EXTENSIONS = (".js", ".ts", ".py", ".jsx", ".tsx", ".json", ".md")


def _assess_completion(task: Task, tmp_dir: str) -> float:
    """Simple completion assessment: check if expected files exist."""
    if not os.path.isdir(tmp_dir):
        return 0.0

    # Count source files by globbing specific extensions (avoids walking node_modules)
    source_count = 0
    for ext in _SOURCE_EXTENSIONS:
        source_count += sum(1 for _ in Path(tmp_dir).rglob(f"*{ext}"))

    if source_count == 0:
        return 0.0

    # Basic heuristic: more files and criteria = higher completion
    criteria_count = len(task.success_criteria)
    if criteria_count == 0:
        return 50.0

    file_ratio = min(source_count / max(criteria_count, 1), 1.0)
    return round(file_ratio * 100, 1)


def _count_lint_warnings(tmp_dir: str) -> int:
    """Run eslint if available and count warnings. Skips if no package.json exists."""
    # Only run eslint for JS/TS projects
    if not (Path(tmp_dir) / "package.json").exists():
        return 0

    try:
        result = subprocess.run(
            ["npx", "eslint", ".", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=tmp_dir,
        )
        if result.stdout:
            data = json.loads(result.stdout)
            return sum(f.get("warningCount", 0) + f.get("errorCount", 0) for f in data)
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError,
            TypeError, AttributeError):
        pass
    return 0


def run_experiment(task: Task, mode: str = "headless", iteration: int = 1) -> ExperimentResult:
    """Execute a single experiment: create /tmp project, run task, collect metrics.

    Args:
        task: The benchmark task to execute
        mode: "interactive" (returns metrics dict) or "headless" (parses claude -p JSON)
        iteration: Current iteration number

    Returns:
        ExperimentResult with status, metrics, and scored result
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    tmp_dir = ""

    try:
        # Create temporary project
        tmp_dir = _create_tmp_project(task)
        start_time = time.monotonic()

        if mode == "headless":
            raw_metrics = _run_headless(task, tmp_dir)
        elif mode == "interactive":
            # Interactive mode: metrics come from the caller (SKILL.md orchestrator)
            # Return a placeholder result; the orchestrator fills in metrics.json
            raw_metrics = {
                "tokens_used": 0,
                "turn_count": 1,
                "error_count": 0,
                "skills_invoked": [],
            }
        else:
            raise ValueError(f"Unknown mode: {mode}")

        duration_ms = int((time.monotonic() - start_time) * 1000)

        # Assess completion
        completion = _assess_completion(task, tmp_dir)
        lint_warnings = _count_lint_warnings(tmp_dir)

        # Build metrics
        metrics = ExperimentMetrics(
            completion=completion,
            tokens_used=raw_metrics["tokens_used"],
            token_budget=task.token_budget,
            error_count=raw_metrics["error_count"],
            lint_warnings=lint_warnings,
            turn_count=raw_metrics["turn_count"],
            expected_turns=task.expected_turns,
            skills_invoked=raw_metrics["skills_invoked"],
            duration_ms=duration_ms,
        )

        # Score
        scored = scorer_mod.compute_score(metrics)

        # Build skill invocations
        invocations = [
            SkillInvocation(skill_name=s)
            for s in raw_metrics["skills_invoked"]
        ]

        return ExperimentResult(
            task_id=task.id,
            iteration=iteration,
            status="completed",
            metrics=metrics,
            scored=scored,
            skill_invocations=invocations,
            timestamp=timestamp,
            tmp_dir=tmp_dir,
        )

    except Exception as e:
        return ExperimentResult(
            task_id=task.id,
            iteration=iteration,
            status="failed",
            failure_reason=str(e),
            timestamp=timestamp,
            tmp_dir=tmp_dir,
        )
    finally:
        # Cleanup /tmp directory
        if tmp_dir and os.path.isdir(tmp_dir):
            try:
                shutil.rmtree(tmp_dir)
            except OSError:
                sys.stderr.write(f"Warning: failed to clean up {tmp_dir}\n")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> int:
    """CLI for running a single experiment."""
    parser = argparse.ArgumentParser(description="Autorefine Experiment Runner")
    parser.add_argument("--task", required=True, help="Path to task markdown file")
    parser.add_argument("--mode", default="headless", choices=["headless", "interactive"])
    parser.add_argument("--iteration", type=int, default=1)
    args = parser.parse_args()

    task = task_bank.load_task(args.task)
    result = run_experiment(task, mode=args.mode, iteration=args.iteration)
    print(json.dumps(asdict(result), indent=2))
    return 0 if result.status == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
