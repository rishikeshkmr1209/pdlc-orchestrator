---
name: sdlc-qa-test-generation
description: >
  Generate QA test cases from a story's problem spec and design spec, create
  Jira issues of type Test linked to acceptance criteria, classify regression
  candidates, and autonomously open a PR in qa-automation that automates
  the regression subset. Designed to be invoked by sdlc-pipeline as Phase 3b in
  parallel with the design-review phase. Triggers on "generate qa tests",
  "qa test plan", "create jira test issues from story", "phase 3b qa".
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Bash
  - Skill
context: fork
---

# SDLC Phase 3b — QA Test Generation

Read the problem spec (Phase 1) and design spec (Phase 2) for a ticket, generate
a structured test plan, register the tests in Jira (issuetype=Test, linked to
the parent story via the standard `Tests` link type), classify the regression
subset, and — for that subset — open a single PR in `qa-automation` that
either updates an existing similar spec or adds a new one.

This skill runs **in parallel with `03-sdlc-design-review`** and is
**informational only**: its result does not gate Phase 4. The pipeline gate is
driven solely by the design-review verdict.

## Inputs

Read in a single parallel batch in Turn 1 (per
`skills/_shared/parallel-reads-rule.md`):

- `<md_base_path>/ph1_problem_spec.md` — sections needed: `Requirements`,
  `Acceptance Criteria`, `Edge Cases`, `Constraints`, `Assumptions`,
  `Non-Goals`, `Figma Design Reference` (if present).
- `<md_base_path>/ph2_design_spec.md` — sections needed: `Architecture`,
  `API Contracts`, `Data Models`, `Security Considerations`, `Testing Strategy`.
- `<state_base_path>/pipeline_state_<ticket>.json` — for `figma.link`,
  classification, `phases` map, model assignment.
- `<state_base_path>/artifact-digest.md` — to learn which existing components/
  endpoints this story touches.
- `<state_base_path>/qa_jira_issues.json` (if it exists from a prior run; used
  for idempotency on Ph2 reject loops — see "Idempotency" below).

Resolve `md_base_path` and `state_base_path` from
`config/phase-artifact-map.json` (do not hardcode `docs/artifacts/<ticket>/`).
Use `scripts/extract-sections.py` to extract the listed sections; if a section
is missing, fall back to reading the file in full and warn.

## Workflow

### Step 1 — Bootstrap platform knowledge

Run the helper script (idempotent, fast on reruns):

```bash
PK_PATH="$(bash claude-master-plugin/scripts/ensure-platform-knowledge.sh)"
```

Read `$PK_PATH/CLAUDE.md` to find the index of services. From the components
listed in `ph2_design_spec.md ## Architecture` plus the endpoints in
`## API Contracts`, pick the matching files in `$PK_PATH/services-detailed/`
(e.g. `loyalty-service.md`, `gateway-service.md`) and read those — and only
those. Skip if the story is purely UI-only with no service reference.

### Step 2 — UI handling (no live Figma fetch in this iteration)

If `pipeline_state.figma.link` is non-empty, capture the URL and any
`figma.css_implementation_guide` already stored in state. Reference the link in
the test plan and call out visual checkpoints per AC (focus, hover, error,
loading, RTL, brand variants if present in `figma.brands`). Do **not** attempt
a live MCP fetch in this phase — that is an explicit follow-up.

### Step 3 — Discover existing Zephyr tests (dedup)

Use the Atlassian MCP via the `Skill` or direct MCP tool call to query
JQL filter `28319` together with keywords scraped from this story's domain.
Recommended JQL pattern:

```
filter = 28319 AND (text ~ "<endpoint or component>" OR text ~ "<AC keyword>")
```

For each hit, capture `key`, `summary`, and any linked stories. Build a
candidate-overlap map keyed by AC-ID. The decision rule per generated test
case:

- **No overlap** (no hit, or hits unrelated to this AC) → mark `decision: new`.
- **Strong overlap** (≥2 keyword matches in the existing test summary or the
  same endpoint reference) → mark `decision: update <existing-key>`. The
  "update" action is conservative: we comment on that issue with the proposed
  delta rather than mutating its description.

### Step 4 — Generate test cases

For every Acceptance Criterion in `ph1_problem_spec.md`, generate at minimum:

- one **functional positive** case,
- one **negative / validation** case,
- one **edge** case (boundary or integration corner per `## Edge Cases` and
  `## Data Models`).

For UI ACs add visual / accessibility checkpoints (focus, error state,
keyboard nav, RTL where applicable). For API ACs add contract checks against
the response schema in `## API Contracts`.

Each test case must follow the schema in
`references/test-case-template.md` — id, title, type, preconditions, steps
(numbered), expected, related ACs, priority, decision.

Write the structured test cases to memory; they will be serialised into
`ph3b_qa_test_plan.md` in Step 7.

### Step 5 — Register tests in Jira

Use the Atlassian MCP. The exact payloads live in
`references/jira-mcp-cookbook.md`.

For each test case with `decision: new`:

1. `mcp__atlassian__createJiraIssue` — `project` = parent story's project,
   `issuetype` = `Test`, `summary` = test title, `description` = markdown
   body containing preconditions, numbered steps, expected result, the related
   AC-IDs, and a backlink to the parent story key.
2. `mcp__atlassian__createIssueLink` — link type `Tests`. Read as
   *outwardIssue* **tests** *inwardIssue*, so:
   `outwardIssueKey = <NEW-TEST-KEY>` (the Test does the testing),
   `inwardIssueKey  = <PARENT-STORY-KEY>` (the Story is "tested by").
   See `references/jira-mcp-cookbook.md` §5b for the canonical payload.
3. Append `{ ac, test_id, jira_key, action: "created" }` to
   `qa_jira_issues.json`.

For each test case with `decision: update <existing-key>`:

1. `mcp__atlassian__addCommentToJiraIssue` on `<existing-key>` — comment body
   summarises the proposed delta (added steps, refined expected result, new
   AC mapping). No destructive edit.
2. `mcp__atlassian__createIssueLink` if the existing test is not yet linked
   to the parent story.
3. Append `{ ac, test_id, jira_key, action: "comment-only" }` to
   `qa_jira_issues.json`.

### Step 6 — Classify regression

Apply the heuristic in `references/regression-rules.md` autonomously. A test
is `regression: true` when ANY of the following holds:

- type is `functional` or `integration`, AND
- the AC modifies an existing endpoint or component (cross-check
  `artifact-digest.md ## Codebase Scan`), OR
- the AC is marked must-pass / critical-path in `ph1_problem_spec.md`, OR
- the test asserts a backward-compatibility invariant (per
  `## Backward Compatibility` in ph1, when present).

Do not ask the user. Record the rule that fired in the artifact so the
classification is auditable.

### Step 7 — Write the artifact

Write `<md_base_path>/ph3b_qa_test_plan.md` using the structure under
**Output Format** below. Write `<state_base_path>/qa_jira_issues.json` and
`<state_base_path>/qa_automation.json` (the latter is populated in Step 8).

### Step 8 — Automate the regression subset in `qa-automation`

Resolve the repo path. **Step 8 must be skip-on-missing, not abort-on-missing**
— if `qa-automation` is not present locally, Steps 1–7 (the test plan
and Jira issues) are still valid and must complete:

```bash
REPO="${QA_AUTOMATION_PATH:-$WORKSPACE_ROOT/qa-automation}"
if [ ! -d "$REPO/.git" ]; then
  echo "qa-automation not found at $REPO — skipping Step 8" >&2
  AUTOMATION_STATUS="skipped: qa-automation checkout absent at $REPO"
  # Skip the rest of Step 8 and Step 9; jump to the artifact-write step
  # with Sign-Off = "partial-(no-pr)" and the reason captured in
  # qa_test_plan.md ## Automation PR section. Do NOT exit the skill —
  # the plan + Jira writes from Steps 1–7 are still the primary deliverable.
fi
```

Do NOT auto-clone — the repo must be a known user checkout (it has org-private
branches, AWS-SSO config, and uncommitted state we must respect). The skill
**continues** to the artifact-write step and records the skipped automation;
the rerun-safe state in `.state/qa_automation.json` then captures
`{"status": "skipped", "reason": "..."}` so a later rerun can attempt
automation once the checkout is available.

Detail steps live in `references/automation-cookbook.md`. High-level:

1. Determine `<stream>` by mapping the components in `## Architecture` /
   service names to existing top-level dirs under `tests/` (use directory
   names matching the project's service/domain areas — inspect the existing
   `tests/` structure to find the right match). UI changes go under `e2e/tests/`.
   Fall back to `shared` if nothing matches.
2. Create branch `feature/<stream>/<TICKET-ID>/qa-auto-tests` from `main`
   (matches `qa-automation` branch convention).
3. For each regression-qualified test case:
   - `Grep` the existing repo for similar specs by title keywords + endpoint +
     similar Jira IDs (matching the project's Jira ticket key patterns).
   - **Score** matches: ≥2 keyword matches inside the same `describe(...)`
     block → **update existing** (add a new `test(...)` inside that
     describe; reuse fixture data file). Otherwise → **create new** spec at
     `tests/<stream>/<sub-area>/<jira-id>-<slug>.spec.ts` (or
     `e2e/tests/<brand>/<jira-id>-<slug>.spec.ts` for UI).
   - Reuse `utils/api-actions/*` and `e2e/pages/*` page objects. Only add
     helpers when none fit (per simplify rules in `CLAUDE.md`).
   - Tag the test name `@regression <TICKET-ID>` and embed the Jira Test key
     in the description-block string, e.g.:
     `test("@regression <TICKET-ID> should ...", async () => { ... })`.
   - Append fixture data to the right brand/market JSON in
     `fixtures/api/<stream>/<brand>/test-data-api-<brand>-<market>-<env>.json`.
4. Run lint pipeline:
   ```bash
   ( cd "$REPO" && npm run lint:fix && npm run format && npm run lint:all )
   ```
5. If lint passes:
   - Commit (Conventional Commits style; reference the ticket).
   - `git push -u origin <branch>`
   - `gh pr create --title "<TICKET-ID>: QA automation for <story title>" \
        --body @<temp-body-file>` — body lists each generated test, the Jira
     Test issue key, and the parent story key.
   - Capture the PR URL.
6. If lint fails after `lint:fix`:
   - **Do not push.** Leave the branch local.
   - Record the lint output in `qa_automation.json` and in the artifact's
     "Automation PR" section.

Write `qa_automation.json` with: `{ branch, repo_path, pr_url|null,
files_changed: [...], lint_status, regression_tests_automated: [...] }`.

### Step 9 — Comment on the parent story

Use `mcp__atlassian__addCommentToJiraIssue` to post a single concise summary
to the parent story: number of Test issues created, regression subset size,
PR URL (or "lint failed — see branch <branch>"), link to
`ph3b_qa_test_plan.md`. One comment per skill run; do not spam on reruns.

## Idempotency (rerun-safe)

This skill MUST be safe to rerun (e.g. when design-review verdict = reject and
Phase 2 loops back). Before any Jira write or any branch push:

1. Read `qa_jira_issues.json` if it exists. Skip Jira creation for AC/test
   pairs already recorded; instead diff and append a follow-up comment only
   if the test content materially changed.
2. Read `qa_automation.json` if it exists. If the branch already exists in
   `qa-automation`, check it out and amend; do not create a duplicate
   branch or PR. If a PR is already open for this branch, push additional
   commits rather than opening a new PR.

Use deterministic dedup keys: `<parent-story-key>::<AC-ID>::<sha256(title)[:12]>`.

## Output Format

Write `<md_base_path>/ph3b_qa_test_plan.md`:

```
## Meta
- Ticket: <TICKET-ID>
- Classification: <from pipeline_state>
- Phase: 3b (QA Test Generation, parallel to design-review)
- Generated at: <ISO timestamp>
- Inputs: ph1_problem_spec.md, ph2_design_spec.md, artifact-digest.md
- Platform knowledge: <PK_PATH>

## Inputs Summary
[brief recap of ACs covered, services touched]

## Existing Zephyr Matches (JQL filter 28319)
[table: AC | matched test key | match score | decision]

## AC → Test Matrix
[table: AC-ID | test ids | regression? | decision (new|update)]

## Test Cases
[full structured cases per references/test-case-template.md]

## Regression Subset
[table: test id | jira key | rule fired | repo location (existing|new) ]

## Jira Issues Created / Linked
[table: jira key | action | parent link | url]

## Automation PR
- Branch: <branch>
- PR URL: <url or "not opened — lint failed">
- Files changed: <count> (<list>)
- Lint status: pass | fail (<excerpt if fail>)

## Sign-Off
- Status: complete | partial-(jira-only) | partial-(no-pr)
- Notes: <any human follow-up needed>
```

State files (JSON):

- `<state_base_path>/qa_jira_issues.json` — array of records
  `{ ac, test_id, jira_key, action, dedup_key, created_at }`.
- `<state_base_path>/qa_automation.json` — single object as per Step 8.

## References

- `references/test-case-template.md` — schema for one generated test case.
- `references/regression-rules.md` — heuristic table with rationale.
- `references/jira-mcp-cookbook.md` — exact MCP payloads (createJiraIssue,
  createIssueLink, JQL search, addCommentToJiraIssue).
- `references/automation-cookbook.md` — branch + write + lint + PR sequence,
  including failure handling and rerun amendments.

## Evaluation

| Scenario | Input | Expected behavior |
|----------|-------|-------------------|
| Trigger — positive | "generate qa tests for TICKET-1234" | Skill activates, runs full Steps 1–9 |
| Trigger — positive | "phase 3b qa for TICKET-2222" | Skill activates |
| Trigger — negative | "review my code" | Skill does NOT activate |
| Edge: no design spec | ph2_design_spec.md missing | Halt with clear error pointing to Phase 2 |
| Edge: rerun after Ph2 reject | qa_jira_issues.json present | Reuses existing keys, no duplicate Jira issues, amends branch instead of new PR |
| Edge: lint failure | npm run lint:all fails after fix | No push, no PR; lint output captured in artifact |
| Edge: no `qa-automation` checkout | path missing | Step 8 skipped with explicit note in artifact; Steps 1–7 still complete |
| Security: never logs JWT or AWS creds | n/a | All MCP payloads built from spec text only; no credential interpolation |
