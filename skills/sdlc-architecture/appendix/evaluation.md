# Architecture Skill — Evaluation Table

Use this table for testing skill trigger behavior. Not needed during normal operation.

| Scenario | Input | Expected Behavior |
|----------|-------|-------------------|
| Trigger -- positive | "design architecture for TICKET-1234" | Skill activates, loads problem_spec, runs full process |
| Trigger -- positive | "architect this feature" | Skill activates |
| Trigger -- positive | "create design spec for TICKET-5678" | Skill activates with --ticket=TICKET-5678 |
| Trigger -- negative | "implement the login feature" | Skill does NOT activate (implementation, not design) |
| Trigger -- negative | "review this code" | Skill does NOT activate (code-review skill) |
| Missing input | No ph1_problem_spec.md found | Stops with clear error message |
| Greenfield | No existing codebase | Notes greenfield, skips codebase analysis, designs from scratch |
| Refinement | ph3_design_review.md present | Enters refinement mode, addresses feedback, updates design |
| Quality gate | Component missing file path | Fails quality check, adds path before outputting |
| Schema check | Missing required field | Fails validation, adds field before outputting |

## What This Skill Does NOT Do

- Write actual TypeScript, JSX, or GraphQL code
- Implement business logic
- Create component JSX structures
- Write test implementations
- Modify requirements (flag issues instead)
- Skip documenting tradeoffs
- Design without understanding the existing codebase first
- Propose libraries without checking `package.json` first
