---
name: systematic-debugging
user-invocable: false
description: >
  Use when encountering any bug, test failure, unexpected behavior, or production
  issue — before proposing fixes. Also use when previous fix attempts have failed.
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
---

# Systematic Debugging

You are diagnosing a technical issue in the project codebase. Random fixes waste time and create new bugs. Your job is to find the root cause FIRST, then fix it.

## Iron Laws

- NEVER FIX WITHOUT ROOT CAUSE INVESTIGATION FIRST — symptom fixes are failure.
- NEVER ADD PERMANENT LOGGING TO DIAGNOSE — remove debug logs before committing.
- NEVER DISABLE A FAILING TEST — investigate why it fails.
- IF 3+ FIXES FAILED — STOP AND QUESTION THE ARCHITECTURE.
- NEVER BATCH MULTIPLE FIXES — one change at a time, verify after each.

**Violating the letter of these rules is violating the spirit of debugging.**

| Excuse | Reality |
|--------|---------|
| "The fix is obvious" | If it were obvious, the bug wouldn't exist. Investigate first. |
| "I'll add a console.log to debug" | Debug logs in production cost money (CloudWatch/DataDog). Use structured logger with debug flag, then remove. |
| "The test is flaky, I'll skip it" | Flaky tests hide real bugs. Investigate the race condition or timing issue. |
| "Quick fix now, investigate later" | Later never comes. The root cause becomes a recurring incident. |
| "I'll try changing X and see" | That's guessing, not debugging. Form a hypothesis first. |
| "Multiple fixes save time" | Can't isolate what worked. Causes new bugs. One at a time. |

---

## The Four Phases

Complete each phase before proceeding to the next.

### Phase 1: Root Cause Investigation

**BEFORE attempting ANY fix:**

1. **Read error messages carefully**
   - Don't skip past errors or warnings — they often contain the solution
   - Read stack traces completely, note line numbers and file paths
   - Check error codes against known patterns

2. **Reproduce consistently**
   - Can you trigger it reliably? What are the exact steps?
   - If not reproducible: gather more data, don't guess

3. **Check recent changes**
   - `git log --oneline -10` — what changed recently?
   - `git diff` — any uncommitted changes that could cause this?
   - New dependencies, config changes, environment differences?

4. **Trace the data flow**
   - Where does the bad value originate?
   - What called this function with the bad value?
   - Keep tracing backward until you find the source
   - Fix at the source, not at the symptom

5. **Use git stash to verify baseline when uncertain**
   - `git stash` → run tests → record results → `git stash pop`
   - This proves whether failures are yours or pre-existing

### Phase 2: Pattern Analysis

1. **Find working examples** — locate similar working code in the same codebase
2. **Compare differences** — what's different between working and broken?
3. **Check dependencies** — what settings, config, or environment does this need?

### Phase 3: Hypothesis and Testing

1. **Form a single hypothesis** — "I think X is the root cause because Y"
2. **Test minimally** — smallest possible change to test the hypothesis
3. **Verify before continuing** — did it work? If not, form NEW hypothesis
4. **Don't stack fixes** — if hypothesis was wrong, revert and try a different one

### Phase 4: Implementation

1. **Write a failing test** — reproduces the bug, proves the fix works
2. **Implement single fix** — address the root cause, ONE change only
3. **Verify fix** — run full test suite, not just the failing test
4. **Check blast radius** — grep for all usages of the changed code

**If 3+ fixes have failed:** STOP. Question the architecture:
- Is this pattern fundamentally sound?
- Should we refactor vs. continue fixing symptoms?
- Discuss with the user before attempting more fixes

---

## Project-Specific Debugging Guide

### DynamoDB Issues
- **403 errors**: Known issue — check `node_modules/dynamodb-localhost/dynamodb/installer.js` uses `https` not `http`. See CLAUDE.md for the manual fix.
- **GSI not found**: Verify GSI was added to the DynamoDB table definition in `serverless.yml`, not just the code.
- **ConditionalCheckFailedException**: Another process modified the item. Check for race conditions in concurrent Lambda invocations.

### GraphQL Issues
- **"Failed to get the current sub/segment from the context"**: A dependency is NOT mocked and is making a real API call. Mock it with `jest.spyOn()`.
- **N+1 queries**: Use DataLoader pattern. Check if resolver is making individual DB calls inside a list resolver.
- **Federation errors**: Check that the subgraph schema is compatible with the gateway. Run `rover subgraph check`.

### Capacitor / Mobile Issues
- **Bridge failures**: Check if web fallback is implemented with `Capacitor.isNativePlatform()` guard.
- **Native-only API crash**: Missing platform check. Always guard with `if (Capacitor.isNativePlatform())`.
- **Deep link not working**: Validate URL scheme in `capacitor.config.ts` and iOS/Android entitlements.

### Dependency Injection / IoC Container Issues
- **DI container returns undefined**: The `typescript-ioc` container relies on constructor defaults. If you removed a default with `!` (definite assignment), the DI container gets `undefined`. Restore the default.
- **Port 5000 conflict on Mac**: AirPlay Receiver uses port 5000. Use a different port or disable AirPlay in System Preferences.

### Lambda / Serverless Issues
- **Cold start timeout**: Check if initialization code is blocking (e.g., synchronous file reads, heavy imports).
- **Memory exceeded**: Check for unbounded array growth, large JSON parsing, or missing pagination.
- **IAM permission denied**: Check the function's IAM role in `serverless.yml`. Verify the resource ARN matches.

---

## Red Flags — STOP and Return to Phase 1

If you catch yourself:
- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "Add multiple changes, run tests"
- "Skip the test, I'll manually verify"
- "It's probably X, let me fix that"
- Proposing solutions before tracing the data flow
- "One more fix attempt" (when already tried 2+)

**ALL of these mean: STOP. Return to Phase 1.**

## Quick Reference

| Phase | Key Activity | Success Criteria |
|-------|-------------|------------------|
| 1. Root Cause | Read errors, reproduce, trace data flow | Understand WHAT and WHY |
| 2. Pattern | Find working examples, compare | Identify differences |
| 3. Hypothesis | Form theory, test minimally | Confirmed or new hypothesis |
| 4. Implementation | Failing test, single fix, verify | Bug resolved, all tests pass |

## Evaluation

| Scenario | Input | Expected behavior |
|----------|-------|-------------------|
| Trigger — positive | "debug this failing test" | Skill activates, begins Phase 1 investigation |
| Trigger — positive | "why is this error happening" | Skill activates |
| Trigger — negative | "write a new debug utility function" | Skill does NOT activate |
| Edge case — multiple failures | 3+ fix attempts fail | Stops and questions architecture |
