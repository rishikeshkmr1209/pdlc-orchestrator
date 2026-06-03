---
id: t5-sdlc-pipeline
tier: 5
token_budget: 100000
expected_turns: 40
---

# Task: Run Full SDLC Pipeline on Feature Ticket

## Description

Execute the complete 10-phase SDLC pipeline (`/client-master:00-sdlc-pipeline --ticket=TEST-001`) on a small feature: "Add a utility function that converts temperatures between Celsius, Fahrenheit, and Kelvin with unit tests." This exercises the full pipeline from requirements through PR creation, testing every SDLC skill in sequence.

## Success Criteria

- [ ] Phase 1 (Requirements): `ph1_problem_spec.md` generated with requirements and acceptance criteria
- [ ] Phase 2 (Architecture): `ph2_design_spec.md` generated with component design
- [ ] Phase 3 (Design Review): `ph3_design_review.md` generated with verdict
- [ ] Phase 4 (Impl Planning): `ph4_implementation_plan.md` generated
- [ ] Phase 5 (Implementation): Code files created matching the plan
- [ ] Phase 6 (Simplify): Code reviewed for quality
- [ ] Phase 7 (Review): Spec compliance, tests, and security reviewed
- [ ] Phase 8 (Verification): `ph8_verification_report.md` generated
- [ ] Phase 9 (Risk): `ph9_risk_assessment.md` generated with ship recommendation
- [ ] Phase 10 (PR): Pull request created on GitHub
- [ ] All 10 phases complete without pipeline halts

## Setup Commands

```bash
mkdir -p src && npm init -y && npm install --save-dev jest
```
