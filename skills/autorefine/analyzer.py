#!/usr/bin/env python3
"""Autorefine Skill Analyzer

Correlates low experiment scores with skill invocations, ranks underperforming
skills, and recommends actions (refine, investigate, ok).

Usage:
    python3 skills/autorefine/analyzer.py    # Self-test

Exit codes:
    0 — Success
    1 — Error
"""

import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

# Import scorer types via relative path hack for standalone execution
_SCORER_PATH = Path(__file__).resolve().parent / "scorer.py"


def _import_scorer():
    """Dynamically import scorer module."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("scorer", _SCORER_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


scorer = _import_scorer()
ExperimentMetrics = scorer.ExperimentMetrics
ScoredResult = scorer.ScoredResult


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ERROR_RATE_REFINE_THRESHOLD = 0.3
ERROR_RATE_INVESTIGATE_THRESHOLD = 0.1


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class SkillInvocation:
    """Record of a single skill invocation during an experiment."""
    skill_name: str
    triggered_at: str = ""       # ISO-8601
    duration_ms: int = 0
    tool_calls: int = 0
    errors: int = 0


@dataclass
class ExperimentResult:
    """Complete result of a single experiment run."""
    task_id: str
    iteration: int
    status: str                   # "completed" | "failed" | "skipped"
    failure_reason: str | None = None
    metrics: ExperimentMetrics | None = None
    scored: ScoredResult | None = None
    skill_invocations: list[SkillInvocation] = field(default_factory=list)
    timestamp: str = ""           # ISO-8601
    tmp_dir: str = ""


@dataclass
class SkillScore:
    """Aggregated score for a single skill across experiments."""
    skill_name: str
    avg_score_contribution: float
    invocation_count: int
    error_rate: float            # errors / invocations
    recommended_action: str      # "refine" | "investigate" | "ok"


@dataclass
class AnalysisReport:
    """Analysis of experiment results with skill rankings."""
    skill_scores: list[SkillScore] = field(default_factory=list)
    total_experiments: int = 0
    avg_composite_score: float = 0.0
    baseline_score: float | None = None
    improvement_delta: float | None = None


# ---------------------------------------------------------------------------
# Analysis functions
# ---------------------------------------------------------------------------

def analyze(results: list[ExperimentResult]) -> AnalysisReport:
    """Correlate scores with skill invocations, rank underperformers.

    Args:
        results: List of experiment results (may include failed/skipped)

    Returns:
        AnalysisReport with skills ranked worst-first
    """
    if not results:
        return AnalysisReport()

    # Filter to completed experiments with scores
    completed = [r for r in results if r.status == "completed" and r.scored is not None]

    total = len(results)
    if not completed:
        return AnalysisReport(total_experiments=total)

    # Compute average composite score
    scores = [r.scored.composite_score for r in completed]
    avg_score = sum(scores) / len(scores)

    # Aggregate skill metrics
    skill_data: dict[str, dict] = {}
    for result in completed:
        experiment_score = result.scored.composite_score
        for inv in result.skill_invocations:
            name = inv.skill_name
            if name not in skill_data:
                skill_data[name] = {
                    "scores": [],
                    "invocations": 0,
                    "errors": 0,
                }
            skill_data[name]["scores"].append(experiment_score)
            skill_data[name]["invocations"] += 1
            skill_data[name]["errors"] += inv.errors

    # Build SkillScore list
    skill_scores = []
    for name, data in skill_data.items():
        inv_count = data["invocations"]
        error_rate = data["errors"] / inv_count if inv_count > 0 else 0.0
        avg_contribution = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0.0

        if error_rate > ERROR_RATE_REFINE_THRESHOLD:
            action = "refine"
        elif error_rate > ERROR_RATE_INVESTIGATE_THRESHOLD:
            action = "investigate"
        else:
            action = "ok"

        skill_scores.append(SkillScore(
            skill_name=name,
            avg_score_contribution=round(avg_contribution, 2),
            invocation_count=inv_count,
            error_rate=round(error_rate, 3),
            recommended_action=action,
        ))

    # Sort worst-first (lowest avg score first)
    skill_scores.sort(key=lambda s: s.avg_score_contribution)

    # Compute baseline and delta if first result has a score
    baseline = scores[0] if scores else None
    delta = None
    if baseline is not None and len(scores) > 1:
        delta = round(scores[-1] - baseline, 2)

    return AnalysisReport(
        skill_scores=skill_scores,
        total_experiments=total,
        avg_composite_score=round(avg_score, 2),
        baseline_score=baseline,
        improvement_delta=delta,
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> int:
    """Self-test with sample data."""
    sample_metrics = ExperimentMetrics(
        completion=80.0, tokens_used=300, token_budget=500,
        error_count=1, lint_warnings=2, turn_count=5, expected_turns=3,
        skills_invoked=["sdlc-requirements"], duration_ms=12000,
    )
    sample_scored = scorer.compute_score(sample_metrics)

    results = [
        ExperimentResult(
            task_id="t1-is-prime", iteration=1, status="completed",
            metrics=sample_metrics, scored=sample_scored,
            skill_invocations=[
                SkillInvocation(skill_name="sdlc-requirements", errors=1),
                SkillInvocation(skill_name="generate-tests", errors=0),
            ],
        ),
    ]

    report = analyze(results)
    print(json.dumps(asdict(report), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
