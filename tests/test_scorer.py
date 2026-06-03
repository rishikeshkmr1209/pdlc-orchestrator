#!/usr/bin/env python3
"""Unit tests for skills/autorefine/scorer.py"""

import importlib.util
import sys
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Dynamic import (scorer.py lives outside the test package)
# ---------------------------------------------------------------------------

_SCORER_PATH = Path(__file__).resolve().parent.parent / "skills" / "autorefine" / "scorer.py"
_spec = importlib.util.spec_from_file_location("scorer", _SCORER_PATH)
scorer = importlib.util.module_from_spec(_spec)
sys.modules["scorer"] = scorer
_spec.loader.exec_module(scorer)

ExperimentMetrics = scorer.ExperimentMetrics
ScoredResult = scorer.ScoredResult
ScoreDelta = scorer.ScoreDelta
compute_score = scorer.compute_score
compare_scores = scorer.compare_scores
SCORE_WEIGHTS = scorer.SCORE_WEIGHTS


class TestScoreWeights(unittest.TestCase):
    """Verify weight constants sum to 1.0."""

    def test_weights_sum_to_one(self):
        total = sum(SCORE_WEIGHTS.values())
        self.assertAlmostEqual(total, 1.0, places=5)


class TestComputeScore(unittest.TestCase):
    """Test the composite scoring formula."""

    def _make_metrics(self, **overrides) -> ExperimentMetrics:
        defaults = {
            "completion": 100.0,
            "tokens_used": 250,
            "token_budget": 500,
            "error_count": 0,
            "lint_warnings": 0,
            "turn_count": 3,
            "expected_turns": 3,
            "skills_invoked": [],
            "duration_ms": 5000,
        }
        defaults.update(overrides)
        return ExperimentMetrics(**defaults)

    def test_perfect_score(self):
        """All metrics at ideal values should yield 100."""
        m = self._make_metrics(tokens_used=0)
        result = compute_score(m)
        self.assertEqual(result.composite_score, 100.0)
        self.assertEqual(result.completion_score, 100.0)
        self.assertEqual(result.token_efficiency, 100.0)
        self.assertEqual(result.error_penalty, 100.0)
        self.assertEqual(result.code_quality, 100.0)
        self.assertEqual(result.turn_efficiency, 100.0)

    def test_all_zeros(self):
        """Worst case: 0 completion, max tokens, many errors."""
        m = self._make_metrics(
            completion=0.0,
            tokens_used=1000,
            token_budget=500,
            error_count=20,
            lint_warnings=30,
            turn_count=20,
            expected_turns=3,
        )
        result = compute_score(m)
        self.assertEqual(result.composite_score, 0.0)

    def test_weighted_formula(self):
        """Verify the formula manually for a known case."""
        m = self._make_metrics(
            completion=80.0,
            tokens_used=300,
            token_budget=500,
            error_count=1,
            lint_warnings=2,
            turn_count=5,
            expected_turns=3,
        )
        result = compute_score(m)

        # Manual calculation:
        # completion_score = 80
        # token_efficiency = max(0, 100 - (300/500)*100) = 100 - 60 = 40
        # error_penalty = max(0, 100 - 1*10) = 90
        # code_quality = max(0, 100 - 2*5) = 90
        # turn_efficiency = max(0, 100 - (5-3)*10) = 80
        # composite = 80*0.5 + 40*0.25 + 90*0.1 + 90*0.1 + 80*0.05
        #           = 40 + 10 + 9 + 9 + 4 = 72
        self.assertAlmostEqual(result.composite_score, 72.0, places=1)
        self.assertAlmostEqual(result.completion_score, 80.0, places=1)
        self.assertAlmostEqual(result.token_efficiency, 40.0, places=1)
        self.assertAlmostEqual(result.error_penalty, 90.0, places=1)
        self.assertAlmostEqual(result.code_quality, 90.0, places=1)
        self.assertAlmostEqual(result.turn_efficiency, 80.0, places=1)

    def test_clamping_above_100(self):
        """Completion above 100 should clamp to 100."""
        m = self._make_metrics(completion=150.0, tokens_used=0)
        result = compute_score(m)
        self.assertEqual(result.completion_score, 100.0)

    def test_clamping_below_zero(self):
        """Negative component scores should clamp to 0."""
        m = self._make_metrics(
            completion=0.0,
            tokens_used=5000,
            token_budget=500,
            error_count=50,
            lint_warnings=100,
            turn_count=30,
            expected_turns=3,
        )
        result = compute_score(m)
        self.assertEqual(result.token_efficiency, 0.0)
        self.assertEqual(result.error_penalty, 0.0)
        self.assertEqual(result.code_quality, 0.0)
        self.assertEqual(result.turn_efficiency, 0.0)

    def test_zero_token_budget(self):
        """Zero token budget should give 0 token efficiency (no division by zero)."""
        m = self._make_metrics(token_budget=0)
        result = compute_score(m)
        self.assertEqual(result.token_efficiency, 0.0)

    def test_fewer_turns_than_expected(self):
        """Fewer turns than expected should yield high turn efficiency."""
        m = self._make_metrics(turn_count=1, expected_turns=5)
        result = compute_score(m)
        # turn_efficiency = max(0, 100 - (1-5)*10) = 100 - (-40) = 140 → clamped to 100
        self.assertEqual(result.turn_efficiency, 100.0)

    def test_metrics_reference(self):
        """ScoredResult should hold a reference to the original metrics."""
        m = self._make_metrics()
        result = compute_score(m)
        self.assertIs(result.metrics, m)


class TestCompareScores(unittest.TestCase):
    """Test score delta computation."""

    def _scored(self, composite: float) -> ScoredResult:
        return ScoredResult(
            composite_score=composite,
            completion_score=composite,
            token_efficiency=composite,
            error_penalty=composite,
            code_quality=composite,
            turn_efficiency=composite,
        )

    def test_improvement(self):
        baseline = self._scored(60.0)
        current = self._scored(72.0)
        delta = compare_scores(baseline, current)
        self.assertEqual(delta.baseline_score, 60.0)
        self.assertEqual(delta.current_score, 72.0)
        self.assertEqual(delta.delta, 12.0)
        self.assertAlmostEqual(delta.improvement_pct, 20.0, places=1)
        self.assertTrue(delta.improved)

    def test_regression(self):
        baseline = self._scored(80.0)
        current = self._scored(70.0)
        delta = compare_scores(baseline, current)
        self.assertEqual(delta.delta, -10.0)
        self.assertFalse(delta.improved)

    def test_no_change(self):
        baseline = self._scored(50.0)
        current = self._scored(50.0)
        delta = compare_scores(baseline, current)
        self.assertEqual(delta.delta, 0.0)
        self.assertFalse(delta.improved)

    def test_baseline_zero(self):
        """Baseline of 0 should not cause division by zero."""
        baseline = self._scored(0.0)
        current = self._scored(50.0)
        delta = compare_scores(baseline, current)
        self.assertEqual(delta.improvement_pct, 100.0)
        self.assertTrue(delta.improved)

    def test_both_zero(self):
        baseline = self._scored(0.0)
        current = self._scored(0.0)
        delta = compare_scores(baseline, current)
        self.assertEqual(delta.improvement_pct, 0.0)
        self.assertFalse(delta.improved)


if __name__ == "__main__":
    unittest.main()
