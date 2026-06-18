# SDLC Stage to Agent/Skill Mapping

This document maps the 11-stage delivery flow to the matching capabilities in this repository, including the relevant skill path(s) and supporting docs.

| Stage | Role / Focus | Best repo match | Skill / Docs path | Notes |
|---|---|---|---|---|
| 1. Problem Decomposer | Clarify WHAT to build from the ticket/requirement | `sdlc-requirements` skill | [skills/sdlc-requirements/SKILL.md](../skills/sdlc-requirements/SKILL.md) | Handles requirements interrogation, acceptance criteria, and ambiguity discovery. |
| 2. Planner | Create implementation blueprint (no code) | `sdlc-impl-planning` skill | [skills/sdlc-impl-planning/SKILL.md](../skills/sdlc-impl-planning/SKILL.md) | Focuses on implementation planning, waves, and dependency mapping. |
| 3. Design Architect | Decide HOW to build it | `sdlc-architecture` skill | [skills/sdlc-architecture/SKILL.md](../skills/sdlc-architecture/SKILL.md) | Produces architecture/design artifacts and ADR-style decisions. |
| 4. Design Critic | Challenge architecture before coding | `sdlc-design-review` skill | [skills/sdlc-design-review/SKILL.md](../skills/sdlc-design-review/SKILL.md) | Gate that reviews design quality and risks before implementation. |
| 5. Builder | Implement according to approved design | Main inline implementation phase in pipeline orchestration | [skills/sdlc-pipeline/SKILL.md](../skills/sdlc-pipeline/SKILL.md), [config/phase-artifact-map.json](../config/phase-artifact-map.json) | Repo docs indicate this is handled by normal Claude behavior rather than a separate specialized stage skill. |
| 6. Tester | Write tests and prove behavior | `test-engineer` subagent + `generate-tests` skill | [agents/03-test-engineer.md](../agents/03-test-engineer.md), [skills/generate-tests/SKILL.md](../skills/generate-tests/SKILL.md) | Best fit for JUnit/Jest/Playwright-style proof work. |
| 7. Critic / Verifier | Audit quality, maintainability, security | `spec-reviewer` + `code-reviewer` + `security-auditor` + `sdlc-verify` | [agents/01-code-reviewer.md](../agents/01-code-reviewer.md), [agents/02-security-auditor.md](../agents/02-security-auditor.md), [skills/sdlc-verify/SKILL.md](../skills/sdlc-verify/SKILL.md) | Covers SOLID/DRY, review quality, and OWASP/security concerns. |
| 8. Fixer | Resolve only critical/high issues and iterate | `systematic-debugging` skill (closest match) | [skills/systematic-debugging/SKILL.md](../skills/systematic-debugging/SKILL.md) | Repo does not define a separate standalone fixer stage; debugging/fix flow is handled inline. |
| 9. Functional Design | Create functional test cases from requirements/design | `sdlc-qa-test-generation` skill | [skills/sdlc-qa-test-generation/SKILL.md](../skills/sdlc-qa-test-generation/SKILL.md) | Generates QA plans and links tests to acceptance criteria. |
| 10. Functional Validator | Ensure completeness and UX alignment | `sdlc-verify` skill | [skills/sdlc-verify/SKILL.md](../skills/sdlc-verify/SKILL.md) | Verifies requirement coverage and implementation completeness. |
| 11. PR Generator | Create ship-ready PR | `create-pr` skill + `PR Manager` agent | [skills/create-pr/SKILL.md](../skills/create-pr/SKILL.md), [agents/04-pr-manager.md](../agents/04-pr-manager.md) | Handles PR format, Jira linkage, and PR lifecycle. |

## Final outputs

| Output | Best repo mapping | Evidence |
|---|---|---|
| SHIP | PR creation flow | [skills/create-pr/SKILL.md](../skills/create-pr/SKILL.md), [agents/04-pr-manager.md](../agents/04-pr-manager.md) |
| Integrate with CI | DevOps flow | [agents/06-devops-engineer.md](../agents/06-devops-engineer.md) |

## Pipeline entry point

The overall orchestration flow is defined by the pipeline skill:

- [skills/sdlc-pipeline/SKILL.md](../skills/sdlc-pipeline/SKILL.md)
- [README.md](../README.md) (pipeline overview and skill list)

## Repo-specific note

Some of the original “one agent per stage” model is handled inline in this repo. In particular, the builder/fixer responsibilities are not always represented by separate standalone agents; they are part of the main implementation flow described in the pipeline docs.
