# Scoring Rubric

## Composite Score Formula

```
score = (completion × 0.50) + (token_efficiency × 0.25) + (error_penalty × 0.10)
      + (code_quality × 0.10) + (turn_efficiency × 0.05)
```

## Component Scores

### Completion (50% weight)

Measures whether the generated code fulfills the task's success criteria.

| Score | Meaning |
|-------|---------|
| 100 | All success criteria met, tests pass, no build errors |
| 75 | Most criteria met, minor failures |
| 50 | Partial completion, some criteria met |
| 25 | Minimal progress, few criteria met |
| 0 | No meaningful output or complete failure |

### Token Efficiency (25% weight)

Measures how efficiently tokens were used relative to the task's budget.

**Formula:** `max(0, 100 - (tokens_used / token_budget × 100))`

| Score | Meaning |
|-------|---------|
| 100 | Zero tokens used (theoretical max) |
| 50 | Used exactly half the budget |
| 0 | Used entire budget or exceeded it |

### Error Penalty (10% weight)

Penalizes tool failures, permission denials, and retries during execution.

**Formula:** `max(0, 100 - (error_count × 10))`

Each error deducts 10 points. 10+ errors = score of 0.

### Code Quality (10% weight)

Measures linting and type correctness of generated code.

**Formula:** `max(0, 100 - (lint_warnings × 5))`

Each warning deducts 5 points. 20+ warnings = score of 0.

### Turn Efficiency (5% weight)

Measures conversation conciseness relative to expected turns.

**Formula:** `max(0, 100 - (turn_count - expected_turns) × 10)`

Fewer turns than expected is clamped to 100 (bonus not given).
Each excess turn deducts 10 points.

## Score Calibration

| Range | Quality | Interpretation |
|-------|---------|---------------|
| 90-100 | Excellent | Skill performing optimally |
| 75-89 | Good | Minor improvements possible |
| 60-74 | Adequate | Notable inefficiencies, worth investigating |
| 40-59 | Poor | Significant issues, refinement recommended |
| 0-39 | Critical | Skill needs major overhaul |

## Weight Rationale

- **Completion (50%)**: The primary goal is correct, working code. Everything else is secondary.
- **Token efficiency (25%)**: Cost control is critical for autonomous loops. Excessive token usage makes the system impractical.
- **Error penalty (10%)**: Errors indicate fragile tool usage or incorrect assumptions.
- **Code quality (10%)**: Lint-clean code reduces downstream maintenance.
- **Turn efficiency (5%)**: Minor factor — fewer turns is nice but not critical.
