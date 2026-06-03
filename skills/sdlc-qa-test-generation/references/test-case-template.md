# Test case schema

Each generated test case must have all of the fields below. The skill keeps
them in memory as a list of dicts and serialises into the
`## Test Cases` section of `ph3b_qa_test_plan.md` and into the Jira issue
description.

```yaml
id: TC-<TICKET>-<NN>            # zero-padded sequential per ticket
title: "<one-line, imperative>"
type: functional | negative | edge | integration | regression | smoke | accessibility
priority: P0 | P1 | P2          # P0 = blocker, P1 = critical, P2 = nice-to-have
related_acs:                    # AC-IDs from ph1_problem_spec.md (one or more)
  - AC-001
preconditions:
  - "<plain-english setup, one bullet per fact>"
steps:                          # numbered, deterministic, copyable
  - "1. <action>"
  - "2. <action>"
expected: |
  <expected outcome — observable, single-statement>
data:                           # references to fixture data (optional)
  fixture: fixtures/api/<stream>/<brand>/test-data-api-<brand>-<market>-<env>.json
  key: "<top-level key>"
decision:                       # set by Step 5
  action: new | update
  existing_jira_key: <KEY|null>
regression: false               # set by Step 6 heuristic
regression_reason: null         # populated when regression=true; cites the rule
automation:                     # set by Step 8
  status: skipped | created | updated
  spec_path: <relative path in qa-automation>
  test_name: "<exact test() title>"
```

## Markdown rendering (for Jira description and ph3b artifact)

Render each case as:

```markdown
### TC-<TICKET>-<NN> — <title>
**Type:** <type> · **Priority:** <priority> · **ACs:** <AC-001, AC-002>

**Preconditions**
- <bullet>

**Steps**
1. <step>
2. <step>

**Expected**
<expected>

**Data:** `<fixture path>` → key `<key>`
**Regression:** <yes|no> (<rule that fired>)
**Decision:** <new | update KEY>
**Automation:** <skipped | created at path | updated at path>
```

## Style rules

- Steps must be deterministic. Do not write "etc." or "verify all fields" —
  list every field.
- Expected must be observable (HTTP status + body shape, DOM assertion, log
  line). Avoid "should work correctly".
- Data references must point to existing fixture files when possible.
- Title must include the verb being tested ("returns 401 when token expired",
  not "401 case").
