# Autorefine — Skill Quality Measurement System

Measures and improves Claude Code skill quality by running benchmark tasks, scoring results with a composite formula, and identifying underperforming skills.

## Quick Start

### Interactive Mode (inside Claude Code)

```
/autorefine
```

Or with options:

```
/autorefine --tier 1                    # Run only Tier 1 (trivial) tasks
/autorefine --iterations 10             # Run 10 experiment iterations
/autorefine --target-score 90           # Stop early when score hits 90
/autorefine --task t1-is-prime          # Run a single specific task
```

Claude Code will spawn isolated worktree subagents for each task, collect metrics, score results, and present a ranked report of skill performance.

### Headless Mode (background / overnight)

Run unattended from the terminal — ideal for overnight continuous learning:

```bash
python3 skills/autorefine/headless.py \
  --tasks skills/autorefine/tasks/ \
  --iterations 20 \
  --target-score 85 \
  --output skills/autorefine/reports/
```

This uses `claude -p --output-format stream-json` under the hood. Requires `claude` CLI to be installed and authenticated.

### Run in Background (nohup)

To keep it running after you close the terminal:

```bash
nohup python3 skills/autorefine/headless.py \
  --tasks skills/autorefine/tasks/ \
  --iterations 50 \
  --target-score 90 \
  --output skills/autorefine/reports/ \
  > /tmp/autorefine.log 2>&1 &

echo "PID: $!"
```

Check progress:

```bash
tail -f /tmp/autorefine.log
```

Reports are written to `skills/autorefine/reports/<timestamp>/` as they complete.

---

## How It Works

```
Task Bank (5 tiers)  →  Experiment Runner  →  Scorer  →  Analyzer  →  Reporter
     .md files            /tmp projects      weighted      rank         JSON +
                          claude -p          formula      skills        Markdown
```

1. **Task Bank** loads benchmark tasks from `tasks/` (YAML frontmatter + markdown)
2. **Runner** creates a `/tmp` project, executes the task, collects metrics
3. **Scorer** applies the composite formula to produce a 0-100 score
4. **Analyzer** correlates scores with skill invocations, ranks underperformers
5. **Reporter** generates JSON and Markdown reports

---

## Scoring Formula

```
score = (completion    x 0.50)
      + (token_eff     x 0.25)
      + (error_penalty x 0.10)
      + (code_quality  x 0.10)
      + (turn_eff      x 0.05)
```

| Component | Weight | What it measures |
|-----------|--------|------------------|
| Completion | 50% | Did the code build, tests pass, criteria met? |
| Token Efficiency | 25% | Tokens used vs. task budget |
| Error Penalty | 10% | Tool failures, permission denials, retries |
| Code Quality | 10% | Lint warnings and type errors |
| Turn Efficiency | 5% | Conversation turns vs. expected |

| Score Range | Quality | Action |
|-------------|---------|--------|
| 90-100 | Excellent | No action needed |
| 75-89 | Good | Minor improvements possible |
| 60-74 | Adequate | Worth investigating |
| 40-59 | Poor | Refinement recommended |
| 0-39 | Critical | Major overhaul needed |

---

## Task Bank

Five tiers of increasing complexity in `tasks/`:

| File | Tier | Description |
|------|------|-------------|
| `t1-is-prime.md` | 1 | Trivial — single function + tests |
| `t2-todo-cli.md` | 2 | Simple — CLI app with CRUD |
| `t3-jwt-auth.md` | 3 | Medium — JWT auth middleware |
| `t4-rest-crud.md` | 4 | Complex — REST API with validation |
| `t5-sdlc-pipeline.md` | 5 | Full pipeline — multi-file system |

### Writing New Tasks

See `references/task-authoring-guide.md`. Tasks are markdown files with YAML frontmatter:

```yaml
---
id: t1-is-prime
tier: 1
title: "Is Prime Function"
token_budget: 500
expected_turns: 3
setup_commands:
  - "mkdir src"
success_criteria:
  - "src/is-prime.js exists with isPrime function"
  - "tests pass with at least 5 test cases"
---

Write an `isPrime(n)` function in `src/is-prime.js` ...
```

---

## Running Tests

Unit tests for all modules:

```bash
# All autorefine tests (53 tests)
python3 -m pytest tests/test_scorer.py tests/test_task_bank.py tests/test_analyzer.py tests/test_runner.py tests/test_reporter.py -v

# Individual modules
python3 -m pytest tests/test_scorer.py -v      # 14 tests
python3 -m pytest tests/test_task_bank.py -v   # 15 tests
python3 -m pytest tests/test_analyzer.py -v    # 8 tests
python3 -m pytest tests/test_runner.py -v      # 9 tests
python3 -m pytest tests/test_reporter.py -v    # 6 tests
```

Each module also has a self-test via CLI:

```bash
python3 skills/autorefine/scorer.py       # Prints sample scored result
python3 skills/autorefine/analyzer.py     # Prints sample analysis
python3 skills/autorefine/task_bank.py --list   # Lists available tasks
```

---

## CLI Reference

### headless.py

```
python3 skills/autorefine/headless.py [OPTIONS]

Options:
  --tasks DIR          Tasks directory (default: skills/autorefine/tasks/)
  --iterations N       Max experiment iterations (default: 20)
  --target-score N     Stop early when score >= N (default: 85)
  --output DIR         Report output directory (default: skills/autorefine/reports/)
```

### runner.py

Run a single experiment:

```
python3 skills/autorefine/runner.py --task <path-to-task.md> [--mode headless|interactive] [--iteration N]
```

### task_bank.py

```
python3 skills/autorefine/task_bank.py --list              # List all tasks
python3 skills/autorefine/task_bank.py --validate <path>   # Validate a task file
```

---

## Reports

Reports are saved to `skills/autorefine/reports/<timestamp>/`:

```
reports/
  2026-03-12-16-30/
    experiments.json    # Machine-readable full results
    summary.md          # Human-readable score table and trends
    skill-scores.md     # Skill rankings with action recommendations
    run.log             # Headless runner log (headless mode only)
```

### Reading Reports

```bash
# Latest report summary
cat skills/autorefine/reports/$(ls -t skills/autorefine/reports/ | head -1)/summary.md

# Skill rankings
cat skills/autorefine/reports/$(ls -t skills/autorefine/reports/ | head -1)/skill-scores.md
```

---

## Architecture

```
skills/autorefine/
  SKILL.md                  # Interactive orchestrator (Claude Code skill)
  scorer.py                 # Composite scoring engine
  task_bank.py              # Task loading and validation
  runner.py                 # Single experiment execution
  analyzer.py               # Skill performance analysis
  reporter.py               # Report generation (JSON + Markdown)
  headless.py               # Overnight headless runner
  tasks/                    # Benchmark task definitions (5 tiers)
  references/               # Scoring rubric, task authoring guide
  reports/                  # Generated reports (gitignored except .gitkeep)
```

All modules are standalone Python (stdlib only, no external deps). Each uses dynamic imports via `importlib.util` for sibling module loading since the directory is not a Python package.

---

## Continuous Learning Workflow

For ongoing skill improvement:

1. **Nightly run** — Schedule headless mode via cron or launchd:
   ```bash
   # Example crontab entry — run every night at 2am
   0 2 * * * cd /path/to/claude-master-plugin && python3 skills/autorefine/headless.py --iterations 50 --output skills/autorefine/reports/ >> /tmp/autorefine-cron.log 2>&1
   ```

2. **Review reports** — Check the latest summary each morning:
   ```bash
   cat skills/autorefine/reports/$(ls -t skills/autorefine/reports/ | head -1)/summary.md
   ```

3. **Act on recommendations** — The analyzer outputs one of:
   - `ok` — skill is performing well
   - `investigate` — error rate 10-30%, worth looking into
   - `refine` — error rate >30%, skill needs improvement

4. **Iterate** — Modify the underperforming SKILL.md, re-run autorefine, compare scores

---

## Prerequisites

- Python 3.10+
- `claude` CLI installed and authenticated (for headless mode)
- No external Python dependencies (stdlib only)
