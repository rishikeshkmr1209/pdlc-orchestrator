# Design Review Skill — Evaluation Table

Use this table for testing skill trigger behavior. Not needed during normal operation.

| Scenario | Input | Expected behavior |
|----------|-------|-------------------|
| Trigger -- positive | "review design --ticket=TICKET-1234" | Activates, loads artifacts, runs full review |
| Trigger -- positive | "design review for FEAT-0456" | Activates |
| Trigger -- positive | "evaluate architecture" | Activates, asks for ticket ID |
| Trigger -- negative | "review this TypeScript file" | Does NOT activate (use code-review) |
| Missing artifact | `ph1_problem_spec.md` not found | Reports missing file, does not proceed |
| Mode A | `codebase_analyzed: false` | Pure design review, no codebase access |
| Mode B | `codebase_analyzed: true` | Validates codebase, then reviews design |
| All scores >= 70, no criticals | Clean design | Gate: `approve` |
| Scores >= 50, major concerns | Decent design | Gate: `approve_with_concerns` |
| Any score < 50 or critical | Flawed design | Gate: `reject` |
| Re-review | Previous `ph3_design_review.md` exists | Populates `review_history`, overwrites file |
