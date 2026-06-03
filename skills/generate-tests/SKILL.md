---
name: 07.2-generate-tests
description: >
  Use when user says "write tests", "generate tests", "add unit tests",
  "create test file", "test this function", "add test coverage",
  or "write a playwright test for".
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
context: fork
---

# Generate Tests Skill

You are generating tests for the project's JavaScript/TypeScript codebase. Produce complete, runnable test files that follow project testing conventions.

## Integration

**DOWNSTREAM OF:** When invoked from the SDLC pipeline, read `ph2_design_spec.md` testing_strategy section before generating tests to align coverage with the approved design.

**Phase 3b QA test plan (when present):** If
`docs/artifacts/<ticket>/ph3b_qa_test_plan.md` exists, read its `## AC → Test
Matrix` and `## Regression Subset` sections before generating tests. Treat
the matrix as authoritative for AC coverage: each AC must map to at least one
test in your output. Cases already automated by Phase 3b in
`qa-automation` (see `## Automation PR` in the QA plan) do not need to
be re-implemented here — focus this skill's output on Jest unit tests and
component-level Playwright tests for the application repo, not the QA
automation repo. If the QA plan is absent (Hotfix/Bug/Spike/Story), proceed
with the existing flow.

## Process

### 1. Understand the Target
- Read the source file(s) to be tested
- Identify all exported functions, classes, hooks, or components
- Note the function signatures, types, and documented behavior
- Identify error cases and edge cases from the implementation

### 2. Discover Project Conventions
```
# Find existing test files to match patterns
- Look for **/__tests__/*.test.ts or *.spec.ts files
- Check jest.config.* for setup files and module name mapper
- Check if @testing-library/react, msw, or other test utilities are used
- Verify whether tests are co-located or in __tests__ directories
```

### 3. Choose Test Type

**Jest Unit Tests** — use when:
- Testing pure functions, utilities, services, hooks
- The target doesn't require a browser
- Mocking dependencies is appropriate

**Playwright E2E Tests** — use when:
- Testing a user-facing flow end-to-end
- Testing across multiple pages or components
- The request mentions "user flow", "browser", "E2E", or "end-to-end"

**Both** — when coverage of both layers is requested.

### 4. Generate the Tests

Follow the templates in `templates/`:
- `templates/jest-unit.md` — Jest patterns and structure
- `templates/playwright-e2e.md` — Playwright page object model

### 5. Write the Files

Write generated tests to the correct location:
- Jest: `[source-dir]/__tests__/[filename].test.ts` or co-located per project convention
- Playwright: `e2e/tests/[feature-name].spec.ts` with page objects in `e2e/pages/`

### 6. Report

After writing:
- List all files created and their paths
- Describe what scenarios are covered
- Note any scenarios that couldn't be tested without additional context
- Estimate coverage improvement if measurable

## What to Test

### For functions:
1. **Happy path** — correct inputs → expected outputs
2. **Edge cases** — empty arrays, zero, null, undefined, boundary values
3. **Error cases** — invalid inputs, dependency failures, thrown errors
4. **Type narrowing** — TypeScript union types handled correctly

### For API handlers:
1. Valid request → correct response status and body
2. Missing/invalid request body → 400 with validation details
3. Unauthorized request → 401
4. Resource not found → 404
5. Dependency failure → 500 with safe error message

### For React components:
1. Renders without errors with required props
2. Displays correct content based on props
3. User interactions trigger correct callbacks
4. Loading and error states render correctly
5. Accessibility: semantic roles and labels present

### For React hooks:
1. Returns expected initial state
2. State transitions are correct
3. Cleanup functions are called

## Operating Modes

### Mode A: Test-After (default)

User has existing code. Generate tests to improve coverage.
**Use when:** user mentions an existing file by name, or asks to "add tests" for existing code.

This is the standard flow described in the Process section above.

### Mode B: TDD (test-first)

User is about to implement. Generate failing tests from the design spec first.
**Use when:** user says "write tests before I implement", "TDD", "test-first", or when
`ph2_design_spec.md` exists but the implementation files do not yet exist.

**TDD Iron Law:** NEVER generate passing tests against unwritten code. If the implementation file does not exist, the tests MUST fail.

**TDD Mode Process:**
1. Read `ph2_design_spec.md` — component definitions, API contracts, and testing_strategy
2. Read `ph1_problem_spec.md` — acceptance criteria and edge cases
3. Generate failing tests for each component's responsibility
4. Generate failing tests for each acceptance criterion
5. Write the test files — ALL tests should fail initially (import errors are expected)
6. Report: "These X tests will fail until you implement [files]. Run: `yarn test --watch`"

**Do NOT write the implementation** — that is the implementer's job.

**Red Flags (TDD Mode):**
If you find yourself writing test mocks that make assertions trivially pass without exercising
real logic — STOP. That is not a test, it is a green checkbox. Ask: "Would this test catch a
bug in the implementation?"

---

## Quality Gates

Generated tests must:
- [ ] Be syntactically valid TypeScript
- [ ] Import from the correct source path
- [ ] Not import test utilities that aren't in the project's dependencies
- [ ] Use `jest.clearAllMocks()` in `beforeEach` when using mocks
- [ ] Have descriptive `describe` and `it` labels that read as specifications
- [ ] Not use `any` type in test code without justification
- [ ] Not have hardcoded implementation details that will break on refactor

## Evaluation

| Scenario | Input | Expected behavior |
|----------|-------|-------------------|
| Trigger — positive | "write Jest tests for this utility function" | Skill activates, generates test file |
| Trigger — positive | "add test coverage to auth.service.ts" | Skill activates |
| Trigger — negative | "how does useEffect work?" | Skill does NOT activate |
| Edge case — empty exports | File with no exports | Reports "no testable exports found" |
| E2E request | "write a Playwright test for the checkout flow" | Generates spec + page object files |
