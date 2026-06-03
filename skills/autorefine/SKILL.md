---
name: autorefine
user-invocable: false
description: >
  Run auto-refinement experiments to measure and improve Claude Code skill quality.
  Triggers on "autorefine", "refine skills", "benchmark skills", "measure skill quality",
  "run autorefine", or "skill quality check".
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Grep
  - Glob
  - AskUserQuestion
---

# Autorefine — Skill Quality Measurement and Improvement

Run benchmark tasks against Claude Code skills, measure quality via composite scoring, identify underperformers, and produce improvement reports.

## Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--tier` | No | all | Run only tasks of this tier (1-5) |
| `--iterations` | No | 5 | Number of experiment iterations |
| `--target-score` | No | 85 | Stop early when score exceeds this |
| `--task` | No | all | Run a specific task by ID |

## Process

### 1. Load Task Bank

Read available tasks from `skills/autorefine/tasks/`:

```bash
python3 skills/autorefine/task_bank.py --list
```

If `--tier` is specified, filter to that tier only.
If `--task` is specified, run only that task.

### 2. Establish Baseline

For each task, run the first experiment to establish a baseline score:

1. Create a fresh worktree using the Agent tool with `isolation: "worktree"`
2. The subagent receives the task description and success criteria
3. After the subagent completes, read `metrics.json` from the worktree (ARCH-003)
4. Score the result using the scoring engine:

```bash
python3 -c "
from skills.autorefine.scorer import compute_score, ExperimentMetrics
import json
metrics = ExperimentMetrics(**json.load(open('metrics.json')))
result = compute_score(metrics)
print(json.dumps({'composite_score': result.composite_score, 'components': {
    'completion': result.completion_score,
    'token_efficiency': result.token_efficiency,
    'error_penalty': result.error_penalty,
    'code_quality': result.code_quality,
    'turn_efficiency': result.turn_efficiency,
}}))
"
```

### 3. Experiment Loop

For each iteration (up to `--iterations`):

1. Pick the next task (round-robin across tiers)
2. Spawn a worktree subagent to execute the task
3. Collect metrics from the subagent's `metrics.json`
4. Score the result
5. Check early stop: if score >= `--target-score`, stop
6. If experiment fails, log the failure and continue (REQ-012)

### 4. Analyze Results

After all iterations complete:

```bash
python3 skills/autorefine/analyzer.py
```

This produces a ranked list of underperforming skills with recommended actions.

### 5. Generate Report

```bash
python3 skills/autorefine/reporter.py
```

Reports are saved to `skills/autorefine/reports/<timestamp>/`:
- `experiments.json` — machine-readable results
- `summary.md` — human-readable summary with score table
- `skill-scores.md` — skill rankings with action recommendations

### 6. Present Results

Display the summary to the user:
- Overall score trend (baseline → current)
- Top underperforming skills
- Recommended actions (refine, investigate, ok)

Ask the user if they want to:
- View detailed report files
- Re-run specific tasks
- Proceed with skill refinement

## Metrics Collection (ARCH-003)

When using worktree subagents in interactive mode, the subagent MUST write a `metrics.json` file to the worktree root before returning:

```json
{
  "completion": 80.0,
  "tokens_used": 1500,
  "error_count": 1,
  "lint_warnings": 3,
  "turn_count": 5,
  "skills_invoked": ["requirements", "generate-tests"],
  "duration_ms": 45000
}
```

## Headless Mode

For overnight unattended runs, use the headless runner directly:

```bash
python3 skills/autorefine/headless.py \
  --tasks skills/autorefine/tasks/ \
  --iterations 20 \
  --target-score 85 \
  --output skills/autorefine/reports/
```

See `references/scoring-rubric.md` for scoring formula details.
See `references/task-authoring-guide.md` for writing new benchmark tasks.

## Evaluation

| Scenario | Input | Expected Behavior |
|----------|-------|-------------------|
| Trigger — positive | "run autorefine" | Loads tasks, runs experiments, produces report |
| Trigger — positive | "benchmark skills" | Same as above |
| Trigger — positive | "autorefine --tier 1" | Runs only T1 tasks |
| Trigger — negative | "refine this code" | Does NOT activate (not about skill quality) |
| Empty task bank | No .md files in tasks/ | Reports "No tasks found" and exits |
| All tasks fail | Every experiment crashes | Reports 0 scores, recommends investigation |
| Target score hit | Score >= 85 on iteration 3 | Stops early, generates report |
