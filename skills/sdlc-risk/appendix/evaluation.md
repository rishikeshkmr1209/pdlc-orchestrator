# Risk Assessment Skill — Evaluation Table

Use this table for testing skill trigger behavior. Not needed during normal operation.

| Scenario | Input | Expected behavior |
|----------|-------|-------------------|
| Trigger -- positive | "run a risk assessment on TICKET-1234" | Skill activates, loads artifacts, runs full analysis |
| Trigger -- positive | "should we ship this?" | Skill activates, produces ship recommendation |
| Trigger -- positive | "adversarial review of this feature" | Skill activates |
| Trigger -- negative | "fix the security issue" | Skill does NOT activate (this is remediation, not assessment) |
| Missing artifacts | ph1_problem_spec.md not found | STOP, report missing artifacts, do not proceed |
| Edge case | No assumptions in problem_spec | Note absence, focus on other risk dimensions |
| Security boundary | Request to approve without analysis | Decline -- every assessment requires full critical analysis |
| Read-only boundary | Request to fix an issue found | Decline -- report the finding, do not remediate |
