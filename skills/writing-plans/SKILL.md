---
name: writing-plans
user-invocable: false
description: >
  Use when user says "plan this", "write a plan", "how should we approach",
  "break this down", or needs a multi-step implementation plan for any non-SDLC task.
allowed-tools:
  - Read
  - Grep
  - Glob
  - Write
  - Bash
---

# Writing Plans

You are creating a structured implementation plan for a multi-step task. Plans prevent wasted work, surface risks early, and make execution reviewable.

## Iron Laws

- NEVER START CODING BEFORE THE PLAN IS WRITTEN AND ACKNOWLEDGED.
- NEVER WRITE A PLAN WITHOUT READING THE RELEVANT CODEBASE FIRST.
- NEVER EXCEED 15 STEPS — if a plan needs more, split into sub-plans.
- NEVER SKIP THE RISKS SECTION — every plan has risks, even "simple" ones.

**Violating the letter of these rules is violating the spirit of planning.**

| Excuse | Reality |
|--------|---------|
| "This is simple enough to skip planning" | Simple tasks become complex once you start. A 5-minute plan saves hours. |
| "I'll plan as I go" | That is called guessing. Write the plan first. |
| "The user just wants code" | The user wants *correct* code. Planning produces correct code. |

---

## When to Use This Skill

Use for non-SDLC tasks that involve multiple files or steps:
- Refactoring (moving code, renaming, restructuring)
- Infrastructure changes (CI/CD, AWS, deployment)
- Dependency upgrades (major version bumps)
- Debugging sessions (systematic investigation)
- Configuration changes (cross-service, multi-file)
- Migration tasks (data, schema, API versioning)

For full feature development with requirements/architecture/review, use the SDLC pipeline instead.

---

## Process

### Step 1: Understand the Goal

Before planning, clarify:
1. **What** is the desired end state?
2. **Why** is this change needed?
3. **What exists today?** Read relevant files, configs, tests.
4. **What are the constraints?** Backward compatibility, downtime, dependencies.

### Step 2: Research the Codebase

Read the relevant code before writing any plan:
- Find existing patterns for similar work
- Identify all files that will be touched
- Check test coverage on affected areas
- Note any dependencies or consumers

### Step 3: Write the Plan

Output to `.claude/plans/<task-name>.md` with this structure:

```markdown
# Plan: <Task Name>

## Goal
<1-2 sentences: what this plan achieves>

## Context
<What exists today, why change is needed>

## Steps
1. **<Action>**: <What to do and why>
   - Files: <specific paths>
   - Verify: <how to confirm this step worked>
2. **<Action>**: ...
   ...

## Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| <what could go wrong> | <consequence> | <how to prevent or recover> |

## Verification
- [ ] <How to confirm the entire plan succeeded>
- [ ] <Tests to run>
- [ ] <Manual checks>

## Rollback
<How to undo if something goes wrong>
```

### Step 4: Present for Review

Show the plan to the user before execution. Ask:
- "Does this plan cover everything?"
- "Any steps I should add or remove?"
- "Ready to execute?"

Do NOT start executing until the user acknowledges the plan.

---

## Plan Quality Checklist

- [ ] Every step has specific file paths (not "update the config")
- [ ] Every step has a verification method
- [ ] Steps are ordered by dependency (prerequisites first)
- [ ] Risks section has at least 2 entries
- [ ] Rollback section exists and is actionable
- [ ] Plan has 15 or fewer steps (split if more)
- [ ] Codebase was read before writing the plan

---

## Step Writing Rules

**Good steps:**
- "Add `validateInput()` to `src/services/order-service.ts` before the `createOrder` call at line 45"
- "Run `yarn test src/services/__tests__/order-service.test.ts` to verify no regressions"

**Bad steps:**
- "Update the service" (which service? which file?)
- "Make it work" (what does "work" mean?)
- "Fix the tests" (which tests? what's wrong?)

Each step should be independently executable and verifiable.

---

## Integration

**REQUIRED NEXT SKILL:** After the user approves the plan, invoke `executing-plans` to execute it step by step.

If this is a feature development task, consider whether the SDLC pipeline (`/client-master:00-sdlc-pipeline`) is more appropriate.

## Evaluation

| Scenario | Input | Expected behavior |
|----------|-------|-------------------|
| Trigger — positive | "plan this refactoring" | Skill activates, begins codebase research |
| Trigger — positive | "break this down into steps" | Skill activates |
| Trigger — negative | "what's the plan for lunch?" | Skill does NOT activate |
| Edge case — >15 steps | Complex task needing 20+ steps | Splits into sub-plans |
