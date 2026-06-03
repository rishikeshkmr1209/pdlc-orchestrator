---
name: finishing-a-development-branch
user-invocable: false
description: >
  Use when implementation is complete and you need to verify readiness before
  creating a PR. Triggers on "I'm done", "ready to create PR", "feature complete",
  "finish this branch", or when SDLC pipeline reaches the PR creation boundary.
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
---

# Finishing a Development Branch

You are performing the final quality gate before PR creation. Verify the branch is truly ready — tests pass, code is clean, project standards are met, and git hygiene is correct.

## Iron Laws

- NEVER DECLARE A BRANCH DONE WITHOUT RUNNING THE FULL TEST SUITE.
- NEVER COMMIT DEBUG LOGS, TODO COMMENTS, OR .only()/.skip() IN THE FINAL STATE.
- NEVER PUSH WITHOUT CHECKING BRANCH IS REBASED ON LATEST MAIN.
- NEVER CREATE A PR WITHOUT THE JIRA TICKET IN THE BRANCH NAME AND PR TITLE.

**Violating the letter of these rules is violating the spirit of finishing well.**

| Excuse | Reality |
|--------|---------|
| "Tests passed earlier" | Code changed since then. Run tests NOW. |
| "It's just one TODO" | TODOs in PRs become permanent. Remove or convert to a Jira ticket. |
| "I'll rebase after the PR" | Merge conflicts in PR reviews waste reviewer time. Rebase now. |
| "The ticket ID is in the commits" | Security team requires it in branch name AND PR title. No exceptions. |

---

## Process

### Step 1: Run Full Test Suite

```bash
# Run the project's test command
yarn test   # or: npm test / jest / pytest
```

**If tests fail:** STOP. Do not proceed. Fix failures first.
**If tests pass:** Record the count and continue.

### Step 2: Code Cleanliness Check

Run these checks on all changed files:

```bash
# Find debug statements
git diff main --name-only -- '*.ts' '*.tsx' '*.js' '*.jsx' | xargs grep -n 'console\.log\|console\.debug\|debugger' 2>/dev/null

# Find TODO/FIXME in changed files
git diff main --name-only -- '*.ts' '*.tsx' '*.js' '*.jsx' | xargs grep -n 'TODO\|FIXME\|HACK\|XXX' 2>/dev/null

# Find .skip() and .only() in test files
git diff main --name-only -- '*.test.*' '*.spec.*' | xargs grep -n '\.skip\|\.only' 2>/dev/null

# Find commented-out code blocks (3+ consecutive commented lines)
git diff main --name-only -- '*.ts' '*.tsx' '*.js' '*.jsx' | xargs grep -n '^[[:space:]]*//' 2>/dev/null
```

**If any found:** Report them and ask user whether to fix or proceed.

### Step 3: Project-Specific Checks

```bash
# Check for PII in log statements
git diff main -- '*.ts' '*.tsx' '*.js' '*.jsx' | grep -n 'logger\.\|console\.' | grep -i 'email\|phone\|name\|address\|user\.' 2>/dev/null

# Check for hardcoded brand/tenant checks (update patterns to match project brand codes)
git diff main -- '*.ts' '*.tsx' | grep -n "=== '<BRAND_CODE>'" 2>/dev/null

# Check for .env file references
git diff main -- '*.ts' '*.tsx' '*.js' '*.jsx' | grep -n '\.env' 2>/dev/null
```

**Additional manual checks:**
- [ ] Feature flag implemented if feature is toggleable
- [ ] If native plugin changed: both web fallback and native implementation present
- [ ] If GraphQL schema changed: Postman collection noted for update
- [ ] If SDK interface changed: SDK version bump planned

### Step 4: Git Hygiene

```bash
# Verify branch name has ticket ID
git branch --show-current

# Check all commits have ticket ID
git log main..HEAD --oneline

# Check no .env files staged
git diff main --name-only | grep '\.env$'

# Check branch is not behind main
git fetch origin main && git log HEAD..origin/main --oneline
```

**If branch is behind main:**
```bash
git rebase origin/main
# Re-run tests after rebase
```

### Step 5: Verify Tests Include New Code

```bash
# Check that test files exist for changed source files
git diff main --name-only -- '*.ts' '*.tsx' --not '*.test.*' --not '*.spec.*'
# For each source file, verify a corresponding test file exists
```

**If coverage < 80% on new business logic:** Flag to user.

### Step 6: Pre-PR Summary

Present a summary to the user:

```
## Branch Readiness Report

**Branch:** <branch-name>
**Ticket:** <TICKET-ID>
**Tests:** X passing, 0 failing
**Code cleanliness:** [clean | N issues found]
**project checks:** [all pass | N items flagged]
**Git hygiene:** [clean | needs rebase]

**Ready for PR:** [Yes | No — N items need attention]
```

### Step 7: Handoff to PR Creation

When all checks pass:

**REQUIRED NEXT SKILL:** Invoke `create-pr` via the Skill tool.
Pass the ticket ID and any SDLC artifact paths for inclusion in the PR description.

---

## Red Flags

**Never:**
- Proceed to PR creation with failing tests
- Skip the project-specific checks (PII, brand, .env)
- Create a PR from `main` or `master` branch
- Force-push without explicit user confirmation

**Always:**
- Run tests fresh (not from cache or previous run)
- Check for debug artifacts (console.log, .only, TODO)
- Verify Jira ticket ID in branch name
- Present the readiness report before proceeding

## Evaluation

| Scenario | Input | Expected behavior |
|----------|-------|-------------------|
| Trigger — positive | "I'm done, ready for PR" | Skill activates, runs readiness checks |
| Trigger — positive | "feature complete, let's create a PR" | Skill activates |
| Trigger — negative | "finish writing this function" | Skill does NOT activate |
| Edge case — failing tests | Test suite has failures | Reports failures, blocks PR creation |
