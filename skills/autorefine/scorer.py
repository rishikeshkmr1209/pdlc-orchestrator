#!/usr/bin/env python3
"""Autorefine Scoring Engine

Computes composite quality scores from experiment metrics using a weighted formula:
  score = (completion × 0.50) + (token_efficiency × 0.25) + (error_penalty × 0.10)
        + (code_quality × 0.10) + (turn_efficiency × 0.05)

Usage:
    python3 skills/autorefine/scorer.py          # Self-test
    python3 skills/autorefine/scorer.py --help

Exit codes:
    0 — Success
    1 — Error
"""

import json
import sys
from dataclasses import asdict, dataclass, field


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCORE_WEIGHTS = {
    "completion": 0.50,
    "token_efficiency": 0.25,
    "error_penalty": 0.10,
    "code_quality": 0.10,
    "turn_efficiency": 0.05,
}


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class ExperimentMetrics:
    """Raw metrics collected from a single experiment run."""
    completion: float          # 0-100: did code build, tests pass?
    tokens_used: int           # Total input + output tokens
    token_budget: int          # From task definition
    error_count: int           # Tool failures, permission denials, retries
    lint_warnings: int         # ESLint/type errors in generated code
    turn_count: int            # Conversation turns to complete
    expected_turns: int        # Estimated ideal turn count from task
    skills_invoked: list[str] = field(default_factory=list)
    duration_ms: int = 0       # Wall clock time


@dataclass
class ScoredResult:
    """Weighted composite score with component breakdown."""
    composite_score: float     # 0-100 weighted score
    completion_score: float    # 0-100
    token_efficiency: float    # 0-100
    error_penalty: float       # 0-100
    code_quality: float        # 0-100
    turn_efficiency: float     # 0-100
    metrics: ExperimentMetrics | None = None


@dataclass
class ScoreDelta:
    """Comparison between baseline and current scored results."""
    baseline_score: float
    current_score: float
    delta: float
    improvement_pct: float
    improved: bool


# ---------------------------------------------------------------------------
# Scoring functions
# ---------------------------------------------------------------------------

def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    """Clamp a value between low and high bounds."""
    return max(low, min(high, value))


def compute_score(metrics: ExperimentMetrics) -> ScoredResult:
    """Apply weighted formula to raw metrics, return 0-100 composite score.

    Component formulas:
      completion_score  = metrics.completion (already 0-100)
      token_efficiency  = max(0, 100 - (tokens_used / token_budget × 100))
      error_penalty     = max(0, 100 - (error_count × 10))
      code_quality      = max(0, 100 - (lint_warnings × 5))
      turn_efficiency   = max(0, 100 - (turn_count - expected_turns) × 10)
    """
    completion_score = _clamp(metrics.completion)

    if metrics.token_budget > 0:
        token_ratio = (metrics.tokens_used / metrics.token_budget) * 100
        token_efficiency = _clamp(100 - token_ratio)
    else:
        token_efficiency = 0.0

    error_penalty = _clamp(100 - (metrics.error_count * 10))
    code_quality = _clamp(100 - (metrics.lint_warnings * 5))

    turn_overshoot = metrics.turn_count - metrics.expected_turns
    turn_efficiency = _clamp(100 - (turn_overshoot * 10))

    composite = (
        completion_score * SCORE_WEIGHTS["completion"]
        + token_efficiency * SCORE_WEIGHTS["token_efficiency"]
        + error_penalty * SCORE_WEIGHTS["error_penalty"]
        + code_quality * SCORE_WEIGHTS["code_quality"]
        + turn_efficiency * SCORE_WEIGHTS["turn_efficiency"]
    )
    composite = _clamp(composite)

    return ScoredResult(
        composite_score=round(composite, 2),
        completion_score=round(completion_score, 2),
        token_efficiency=round(token_efficiency, 2),
        error_penalty=round(error_penalty, 2),
        code_quality=round(code_quality, 2),
        turn_efficiency=round(turn_efficiency, 2),
        metrics=metrics,
    )


def compare_scores(baseline: ScoredResult, current: ScoredResult) -> ScoreDelta:
    """Compute delta and improvement percentage between baseline and current."""
    delta = current.composite_score - baseline.composite_score
    if baseline.composite_score > 0:
        improvement_pct = (delta / baseline.composite_score) * 100
    else:
        improvement_pct = 100.0 if delta > 0 else 0.0

    return ScoreDelta(
        baseline_score=baseline.composite_score,
        current_score=current.composite_score,
        delta=round(delta, 2),
        improvement_pct=round(improvement_pct, 2),
        improved=delta > 0,
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> int:
    """Self-test: compute score for a sample metric set and print JSON."""
    sample = ExperimentMetrics(
        completion=80.0,
        tokens_used=300,
        token_budget=500,
        error_count=1,
        lint_warnings=2,
        turn_count=5,
        expected_turns=3,
        skills_invoked=["sdlc-requirements"],
        duration_ms=12000,
    )
    result = compute_score(sample)
    print(json.dumps(asdict(result), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
