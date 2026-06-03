#!/usr/bin/env python3
"""Unit tests for skills/autorefine/analyzer.py"""

import importlib.util
import sys
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Dynamic imports
# ---------------------------------------------------------------------------

_BASE = Path(__file__).resolve().parent.parent / "skills" / "autorefine"

_spec_s = importlib.util.spec_from_file_location("scorer", _BASE / "scorer.py")
scorer = importlib.util.module_from_spec(_spec_s)
sys.modules["scorer"] = scorer
_spec_s.loader.exec_module(scorer)

_spec_a = importlib.util.spec_from_file_location("analyzer", _BASE / "analyzer.py")
analyzer = importlib.util.module_from_spec(_spec_a)
sys.modules["analyzer"] = analyzer
_spec_a.loader.exec_module(analyzer)

ExperimentMetrics = scorer.ExperimentMetrics
ExperimentResult = analyzer.ExperimentResult
SkillInvocation = analyzer.SkillInvocation
SkillScore = analyzer.SkillScore
AnalysisReport = analyzer.AnalysisReport
analyze = analyzer.analyze


class TestAnalyzeEmpty(unittest.TestCase):
    """Test analysis with empty or minimal input."""

    def test_empty_results(self):
        report = analyze([])
        self.assertEqual(report.total_experiments, 0)
        self.assertEqual(report.skill_scores, [])
        self.assertEqual(report.avg_composite_score, 0.0)

    def test_all_failed(self):
        results = [
            ExperimentResult(task_id="t1", iteration=1, status="failed", failure_reason="crash"),
            ExperimentResult(task_id="t2", iteration=1, status="skipped"),
        ]
        report = analyze(results)
        self.assertEqual(report.total_experiments, 2)
        self.assertEqual(report.skill_scores, [])
        self.assertEqual(report.avg_composite_score, 0.0)


class TestAnalyzeRanking(unittest.TestCase):
    """Test skill ranking logic."""

    def _make_result(self, task_id: str, score: float, skills: list[tuple[str, int]]) -> ExperimentResult:
        metrics = ExperimentMetrics(
            completion=score, tokens_used=100, token_budget=500,
            error_count=0, lint_warnings=0, turn_count=3, expected_turns=3,
        )
        scored = scorer.compute_score(metrics)
        invocations = [
            SkillInvocation(skill_name=name, errors=errors)
            for name, errors in skills
        ]
        return ExperimentResult(
            task_id=task_id, iteration=1, status="completed",
            metrics=metrics, scored=scored, skill_invocations=invocations,
        )

    def test_single_skill(self):
        results = [self._make_result("t1", 80.0, [("requirements", 0)])]
        report = analyze(results)
        self.assertEqual(len(report.skill_scores), 1)
        self.assertEqual(report.skill_scores[0].skill_name, "requirements")
        self.assertEqual(report.skill_scores[0].recommended_action, "ok")

    def test_worst_first_ranking(self):
        r1 = self._make_result("t1", 90.0, [("good-skill", 0)])
        r2 = self._make_result("t2", 30.0, [("bad-skill", 0)])
        report = analyze([r1, r2])
        self.assertEqual(report.skill_scores[0].skill_name, "bad-skill")
        self.assertEqual(report.skill_scores[1].skill_name, "good-skill")

    def test_no_skills_in_experiment(self):
        """EC-005: Experiment with no skill invocations."""
        metrics = ExperimentMetrics(
            completion=80.0, tokens_used=100, token_budget=500,
            error_count=0, lint_warnings=0, turn_count=3, expected_turns=3,
        )
        scored = scorer.compute_score(metrics)
        results = [ExperimentResult(
            task_id="t1", iteration=1, status="completed",
            metrics=metrics, scored=scored, skill_invocations=[],
        )]
        report = analyze(results)
        self.assertEqual(report.skill_scores, [])
        self.assertGreater(report.avg_composite_score, 0)


class TestAnalyzeErrorRate(unittest.TestCase):
    """Test error rate calculation and action recommendations."""

    def _make_result_with_errors(self, skill_name: str, errors: int) -> ExperimentResult:
        metrics = ExperimentMetrics(
            completion=50.0, tokens_used=100, token_budget=500,
            error_count=errors, lint_warnings=0, turn_count=3, expected_turns=3,
        )
        scored = scorer.compute_score(metrics)
        return ExperimentResult(
            task_id="t1", iteration=1, status="completed",
            metrics=metrics, scored=scored,
            skill_invocations=[SkillInvocation(skill_name=skill_name, errors=errors)],
        )

    def test_high_error_rate_refine(self):
        """Error rate > 0.3 should recommend 'refine'."""
        result = self._make_result_with_errors("buggy-skill", 1)
        report = analyze([result])
        # 1 error / 1 invocation = 1.0 error rate
        self.assertEqual(report.skill_scores[0].recommended_action, "refine")

    def test_no_errors_ok(self):
        result = self._make_result_with_errors("clean-skill", 0)
        report = analyze([result])
        self.assertEqual(report.skill_scores[0].recommended_action, "ok")


class TestAnalyseBaseline(unittest.TestCase):
    """Test baseline and delta computation."""

    def test_improvement_delta(self):
        metrics1 = ExperimentMetrics(
            completion=50.0, tokens_used=300, token_budget=500,
            error_count=2, lint_warnings=3, turn_count=6, expected_turns=3,
        )
        metrics2 = ExperimentMetrics(
            completion=90.0, tokens_used=100, token_budget=500,
            error_count=0, lint_warnings=0, turn_count=3, expected_turns=3,
        )
        r1 = ExperimentResult(
            task_id="t1", iteration=1, status="completed",
            metrics=metrics1, scored=scorer.compute_score(metrics1),
        )
        r2 = ExperimentResult(
            task_id="t1", iteration=2, status="completed",
            metrics=metrics2, scored=scorer.compute_score(metrics2),
        )
        report = analyze([r1, r2])
        self.assertIsNotNone(report.baseline_score)
        self.assertIsNotNone(report.improvement_delta)
        self.assertGreater(report.improvement_delta, 0)


if __name__ == "__main__":
    unittest.main()
