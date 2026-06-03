#!/usr/bin/env python3
"""Autorefine Headless Runner

Orchestrates multiple experiments overnight via `claude -p`, enforcing
iteration caps and early stop on target score.

Usage:
    python3 skills/autorefine/headless.py --tasks skills/autorefine/tasks/ --iterations 20 --target-score 85 --output skills/autorefine/reports/

Exit codes:
    0 — Success (completed or early stop)
    1 — Error
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# Dynamic imports
_MODULE_DIR = Path(__file__).resolve().parent


def _import_module(name: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, _MODULE_DIR / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


task_bank_mod = _import_module("task_bank")
scorer_mod = _import_module("scorer")
analyzer_mod = _import_module("analyzer")
reporter_mod = _import_module("reporter")
runner_mod = _import_module("runner")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_ITERATIONS = 20
DEFAULT_TARGET_SCORE = 85
DEFAULT_TASKS_DIR = str(_MODULE_DIR / "tasks")
DEFAULT_OUTPUT_DIR = str(_MODULE_DIR / "reports")


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def _setup_logging(report_dir: Path | None = None) -> logging.Logger:
    """Configure logging to stderr and optionally to a run.log file."""
    logger = logging.getLogger("autorefine")
    logger.setLevel(logging.INFO)

    # Clear existing handlers to avoid duplicates on repeated calls
    logger.handlers.clear()

    # Always log to stderr
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
    ))
    logger.addHandler(stderr_handler)

    # Log to file if report dir exists
    if report_dir:
        report_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(report_dir / "run.log")
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s"
        ))
        logger.addHandler(file_handler)

    return logger


# ---------------------------------------------------------------------------
# Main orchestration loop
# ---------------------------------------------------------------------------

def run_headless(
    tasks_dir: str,
    iterations: int,
    target_score: float,
    output_dir: str,
) -> int:
    """Run the headless experiment loop.

    1. Load tasks sorted by tier
    2. Run each task as an experiment
    3. Score results
    4. Check early stop condition
    5. Analyze and generate report

    Returns exit code (0 = success, 1 = error).
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H-%M")
    report_dir = Path(output_dir) / timestamp
    logger = _setup_logging(report_dir)

    logger.info("Autorefine headless runner starting")
    logger.info(f"Tasks dir: {tasks_dir}")
    logger.info(f"Iterations: {iterations}, Target score: {target_score}")
    logger.info(f"Output: {report_dir}")

    # Load tasks
    tasks = task_bank_mod.list_tasks(tasks_dir)
    if not tasks:
        logger.error(f"No valid tasks found in {tasks_dir}")
        return 1

    logger.info(f"Loaded {len(tasks)} tasks: {[t.id for t in tasks]}")

    # Run experiments
    all_results = []
    baseline_score: float | None = None
    iteration = 0

    for i in range(iterations):
        iteration = i + 1
        logger.info(f"--- Iteration {iteration}/{iterations} ---")

        for task in tasks:
            logger.info(f"Running task: {task.id} (tier {task.tier})")

            result = runner_mod.run_experiment(task, mode="headless", iteration=iteration)
            all_results.append(result)

            if result.status == "failed":
                logger.warning(f"Task {task.id} failed: {result.failure_reason}")
                continue  # REQ-012: skip failures, continue

            score = result.scored.composite_score if result.scored else 0.0
            logger.info(f"Task {task.id} scored: {score}")

            # REQ-011: first completed result is baseline
            if baseline_score is None and result.scored:
                baseline_score = score
                logger.info(f"Baseline established: {baseline_score}")

            # REQ-010: early stop on target score
            if result.scored and score >= target_score:
                logger.info(f"Target score {target_score} reached! Score: {score}")
                break

        # Check if any task in this iteration hit target
        iter_results = [r for r in all_results if r.iteration == iteration
                       and r.status == "completed" and r.scored]
        if iter_results and max(r.scored.composite_score for r in iter_results) >= target_score:
            logger.info("Early stop: target score achieved")
            break

    # Analyze results
    logger.info("Analyzing results...")
    analysis = analyzer_mod.analyze(all_results)

    # Generate report
    config = {
        "iterations": iterations,
        "target_score": target_score,
        "tasks_dir": tasks_dir,
        "actual_iterations": iteration,
    }
    summary_path = reporter_mod.generate_report(
        all_results, analysis, str(report_dir.parent), config
    )

    logger.info(f"Report generated: {summary_path}")
    logger.info(f"Total experiments: {len(all_results)}")
    logger.info(f"Average score: {analysis.avg_composite_score}")
    if analysis.improvement_delta is not None:
        logger.info(f"Improvement from baseline: {analysis.improvement_delta}")

    return 0


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> int:
    """CLI entry point for headless runner."""
    parser = argparse.ArgumentParser(
        description="Autorefine Headless Runner — overnight experiment orchestrator"
    )
    parser.add_argument(
        "--tasks", default=DEFAULT_TASKS_DIR,
        help=f"Tasks directory (default: {DEFAULT_TASKS_DIR})"
    )
    parser.add_argument(
        "--iterations", type=int, default=DEFAULT_ITERATIONS,
        help=f"Max iterations (default: {DEFAULT_ITERATIONS})"
    )
    parser.add_argument(
        "--target-score", type=float, default=DEFAULT_TARGET_SCORE,
        help=f"Early stop target score (default: {DEFAULT_TARGET_SCORE})"
    )
    parser.add_argument(
        "--output", default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory for reports (default: {DEFAULT_OUTPUT_DIR})"
    )

    args = parser.parse_args()

    return run_headless(
        tasks_dir=args.tasks,
        iterations=args.iterations,
        target_score=args.target_score,
        output_dir=args.output,
    )


if __name__ == "__main__":
    sys.exit(main())
