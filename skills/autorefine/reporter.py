#!/usr/bin/env python3
"""Autorefine Report Generator

Produces experiment reports: summary.md, experiments.json, and skill-scores.md
from experiment results and analysis.

Usage:
    python3 skills/autorefine/reporter.py    # Self-test

Exit codes:
    0 — Success
    1 — Error
"""

import json
import sys
from dataclasses import asdict
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


scorer_mod = _import_module("scorer")
analyzer_mod = _import_module("analyzer")

ExperimentResult = analyzer_mod.ExperimentResult
AnalysisReport = analyzer_mod.AnalysisReport
ExperimentMetrics = scorer_mod.ExperimentMetrics


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def _generate_experiments_json(
    experiments: list[ExperimentResult],
    analysis: AnalysisReport,
    run_id: str,
    config: dict | None = None,
) -> dict:
    """Build the experiments.json structure."""
    completed = [e for e in experiments if e.status == "completed" and e.scored]
    failed = [e for e in experiments if e.status == "failed"]

    scores = [e.scored.composite_score for e in completed]
    best_score = max(scores) if scores else 0.0

    return {
        "run_id": run_id,
        "config": config or {},
        "baseline": {
            "score": analysis.baseline_score,
        },
        "experiments": [
            {
                "task_id": e.task_id,
                "iteration": e.iteration,
                "status": e.status,
                "composite_score": e.scored.composite_score if e.scored else None,
                "metrics": asdict(e.metrics) if e.metrics else None,
                "failure_reason": e.failure_reason,
            }
            for e in experiments
        ],
        "summary": {
            "total": len(experiments),
            "completed": len(completed),
            "failed": len(failed),
            "avg_score": analysis.avg_composite_score,
            "best_score": round(best_score, 2),
            "improvement_from_baseline": analysis.improvement_delta,
        },
    }


def _generate_summary_md(
    experiments: list[ExperimentResult],
    analysis: AnalysisReport,
    timestamp_str: str,
) -> str:
    """Generate human-readable summary.md."""
    completed = [e for e in experiments if e.status == "completed" and e.scored]
    failed = [e for e in experiments if e.status == "failed"]

    lines = [
        "# Autorefine Experiment Summary",
        "",
        f"**Date:** {timestamp_str}",
        f"**Total experiments:** {len(experiments)}",
        f"**Completed:** {len(completed)} | **Failed:** {len(failed)}",
        f"**Average score:** {analysis.avg_composite_score}",
        "",
    ]

    if analysis.baseline_score is not None:
        lines.append(f"**Baseline score:** {analysis.baseline_score}")
    if analysis.improvement_delta is not None:
        direction = "+" if analysis.improvement_delta >= 0 else ""
        lines.append(f"**Improvement:** {direction}{analysis.improvement_delta}")
    lines.append("")

    # Score table
    if completed:
        lines.append("## Experiment Scores")
        lines.append("")
        lines.append("| Task | Iteration | Score | Completion | Token Eff. | Errors |")
        lines.append("|------|-----------|-------|------------|------------|--------|")
        for e in completed:
            s = e.scored
            lines.append(
                f"| {e.task_id} | {e.iteration} | {s.composite_score} "
                f"| {s.completion_score} | {s.token_efficiency} | {s.error_penalty} |"
            )
        lines.append("")

    # Failed experiments
    if failed:
        lines.append("## Failed Experiments")
        lines.append("")
        for e in failed:
            lines.append(f"- **{e.task_id}** (iteration {e.iteration}): {e.failure_reason}")
        lines.append("")

    return "\n".join(lines)


def _generate_skill_scores_md(analysis: AnalysisReport) -> str:
    """Generate skill-scores.md ranking skills with recommendations."""
    lines = [
        "# Skill Performance Scores",
        "",
        f"**Total experiments analyzed:** {analysis.total_experiments}",
        f"**Average composite score:** {analysis.avg_composite_score}",
        "",
    ]

    if not analysis.skill_scores:
        lines.append("No skill invocation data available.")
        return "\n".join(lines)

    lines.append("## Skill Rankings (worst-first)")
    lines.append("")
    lines.append("| Rank | Skill | Avg Score | Invocations | Error Rate | Action |")
    lines.append("|------|-------|-----------|-------------|------------|--------|")
    for i, ss in enumerate(analysis.skill_scores, 1):
        lines.append(
            f"| {i} | {ss.skill_name} | {ss.avg_score_contribution} "
            f"| {ss.invocation_count} | {ss.error_rate:.1%} | {ss.recommended_action} |"
        )
    lines.append("")

    # Action summary
    refine = [s for s in analysis.skill_scores if s.recommended_action == "refine"]
    investigate = [s for s in analysis.skill_scores if s.recommended_action == "investigate"]

    if refine:
        lines.append("## Skills Needing Refinement")
        lines.append("")
        for s in refine:
            lines.append(f"- **{s.skill_name}**: error rate {s.error_rate:.1%}, avg score {s.avg_score_contribution}")
        lines.append("")

    if investigate:
        lines.append("## Skills to Investigate")
        lines.append("")
        for s in investigate:
            lines.append(f"- **{s.skill_name}**: error rate {s.error_rate:.1%}, avg score {s.avg_score_contribution}")
        lines.append("")

    return "\n".join(lines)


def generate_report(
    experiments: list[ExperimentResult],
    analysis: AnalysisReport,
    output_dir: str,
    config: dict | None = None,
) -> str:
    """Write all report files to output_dir, return path to summary.md.

    Creates a timestamped subdirectory containing:
    - experiments.json
    - summary.md
    - skill-scores.md
    """
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y-%m-%d-%H-%M")
    timestamp_display = now.strftime("%Y-%m-%d %H:%M UTC")
    report_dir = Path(output_dir) / timestamp
    report_dir.mkdir(parents=True, exist_ok=True)

    # Write experiments.json
    exp_json = _generate_experiments_json(experiments, analysis, timestamp, config)
    (report_dir / "experiments.json").write_text(
        json.dumps(exp_json, indent=2), encoding="utf-8"
    )

    # Write summary.md
    summary_md = _generate_summary_md(experiments, analysis, timestamp_display)
    summary_path = report_dir / "summary.md"
    summary_path.write_text(summary_md, encoding="utf-8")

    # Write skill-scores.md
    skill_md = _generate_skill_scores_md(analysis)
    (report_dir / "skill-scores.md").write_text(skill_md, encoding="utf-8")

    return str(summary_path)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> int:
    """Self-test with sample data."""
    sample_metrics = ExperimentMetrics(
        completion=80.0, tokens_used=300, token_budget=500,
        error_count=1, lint_warnings=2, turn_count=5, expected_turns=3,
    )
    scored = scorer_mod.compute_score(sample_metrics)
    results = [
        ExperimentResult(
            task_id="t1-is-prime", iteration=1, status="completed",
            metrics=sample_metrics, scored=scored,
        ),
    ]
    analysis = analyzer_mod.analyze(results)

    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        path = generate_report(results, analysis, tmp)
        print(f"Report generated at: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
