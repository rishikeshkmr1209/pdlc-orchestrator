#!/usr/bin/env python3
"""Unit tests for skills/autorefine/reporter.py"""

import importlib.util
import json
import sys
import tempfile
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
analyzer_mod = importlib.util.module_from_spec(_spec_a)
sys.modules["analyzer"] = analyzer_mod
_spec_a.loader.exec_module(analyzer_mod)

_spec_r = importlib.util.spec_from_file_location("reporter", _BASE / "reporter.py")
reporter = importlib.util.module_from_spec(_spec_r)
sys.modules["reporter"] = reporter
_spec_r.loader.exec_module(reporter)

ExperimentMetrics = scorer.ExperimentMetrics
ExperimentResult = analyzer_mod.ExperimentResult
SkillInvocation = analyzer_mod.SkillInvocation
AnalysisReport = analyzer_mod.AnalysisReport
generate_report = reporter.generate_report
analyze = analyzer_mod.analyze


class TestGenerateReport(unittest.TestCase):
    """Test report generation produces correct files."""

    def _make_results(self) -> list[ExperimentResult]:
        m1 = ExperimentMetrics(
            completion=80.0, tokens_used=300, token_budget=500,
            error_count=1, lint_warnings=2, turn_count=5, expected_turns=3,
            skills_invoked=["requirements"],
        )
        m2 = ExperimentMetrics(
            completion=60.0, tokens_used=400, token_budget=500,
            error_count=3, lint_warnings=5, turn_count=8, expected_turns=3,
            skills_invoked=["generate-tests"],
        )
        return [
            ExperimentResult(
                task_id="t1", iteration=1, status="completed",
                metrics=m1, scored=scorer.compute_score(m1),
                skill_invocations=[SkillInvocation(skill_name="requirements", errors=1)],
            ),
            ExperimentResult(
                task_id="t2", iteration=2, status="completed",
                metrics=m2, scored=scorer.compute_score(m2),
                skill_invocations=[SkillInvocation(skill_name="generate-tests", errors=3)],
            ),
            ExperimentResult(
                task_id="t3", iteration=3, status="failed",
                failure_reason="timeout",
            ),
        ]

    def test_report_files_exist(self):
        results = self._make_results()
        analysis = analyze(results)
        with tempfile.TemporaryDirectory() as tmp:
            summary_path = generate_report(results, analysis, tmp)
            report_dir = Path(summary_path).parent
            self.assertTrue((report_dir / "experiments.json").exists())
            self.assertTrue((report_dir / "summary.md").exists())
            self.assertTrue((report_dir / "skill-scores.md").exists())

    def test_experiments_json_schema(self):
        results = self._make_results()
        analysis = analyze(results)
        with tempfile.TemporaryDirectory() as tmp:
            summary_path = generate_report(results, analysis, tmp)
            report_dir = Path(summary_path).parent
            data = json.loads((report_dir / "experiments.json").read_text())
            self.assertIn("run_id", data)
            self.assertIn("experiments", data)
            self.assertIn("summary", data)
            self.assertEqual(data["summary"]["total"], 3)
            self.assertEqual(data["summary"]["completed"], 2)
            self.assertEqual(data["summary"]["failed"], 1)

    def test_summary_md_content(self):
        results = self._make_results()
        analysis = analyze(results)
        with tempfile.TemporaryDirectory() as tmp:
            summary_path = generate_report(results, analysis, tmp)
            content = Path(summary_path).read_text()
            self.assertIn("Autorefine Experiment Summary", content)
            self.assertIn("Total experiments", content)
            self.assertIn("t1", content)
            self.assertIn("Failed Experiments", content)
            self.assertIn("timeout", content)

    def test_skill_scores_md(self):
        results = self._make_results()
        analysis = analyze(results)
        with tempfile.TemporaryDirectory() as tmp:
            summary_path = generate_report(results, analysis, tmp)
            report_dir = Path(summary_path).parent
            content = (report_dir / "skill-scores.md").read_text()
            self.assertIn("Skill Performance Scores", content)
            self.assertIn("requirements", content)
            self.assertIn("generate-tests", content)


class TestEmptyReport(unittest.TestCase):
    """Test report generation with no experiments."""

    def test_empty_experiments(self):
        analysis = analyze([])
        with tempfile.TemporaryDirectory() as tmp:
            summary_path = generate_report([], analysis, tmp)
            self.assertTrue(Path(summary_path).exists())
            content = Path(summary_path).read_text()
            self.assertIn("Total experiments", content)

    def test_all_failed_experiments(self):
        results = [
            ExperimentResult(task_id="t1", iteration=1, status="failed", failure_reason="crash"),
        ]
        analysis = analyze(results)
        with tempfile.TemporaryDirectory() as tmp:
            summary_path = generate_report(results, analysis, tmp)
            report_dir = Path(summary_path).parent
            data = json.loads((report_dir / "experiments.json").read_text())
            self.assertEqual(data["summary"]["completed"], 0)
            self.assertEqual(data["summary"]["failed"], 1)


if __name__ == "__main__":
    unittest.main()
