# Automation cookbook (qa-automation)

Step 8 of the skill. Produces a single PR per story containing the regression
subset.

## Preconditions

- `qa-automation` is checked out at `${INTL_QA_AUTOMATION_PATH:-$WORKSPACE_ROOT/qa-automation}`.
- `gh` CLI is authenticated (`gh auth status`) — the skill does not log in.
- The repo is on `main` (or the agreed default branch). If on a feature
  branch with uncommitted state, **abort Step 8** and record
  `qa_automation.json.status = "skipped: dirty workdir"`. Never stash or
  reset uncommitted user work.

## 1. Determine the stream

`STREAM` is a **bare identifier** — no `tests/` prefix, no trailing slash.
Path concatenation (e.g. `tests/$STREAM`) and the branch name
(`feature/$STREAM/...`) embed `STREAM` directly, so any prefix or slash
here would corrupt both.

Map components from `ph2_design_spec.md ## Architecture` to one of these
identifiers:

| Component / service | `STREAM` value | Resolved API path | Resolved UI path |
|---------------------|---------------|-------------------|------------------|
| Loyalty (offers, identify, transactions) | `loyalty` | `tests/loyalty/` | n/a |
| Partners API | `partners` | `tests/partners/` | n/a |
| Partners Admin | `partners-admin` | `tests/partners-admin/` | n/a |
| Partner service | `partner-service` | `tests/partner-service/` | n/a |
| User service / auth | `user-service` | `tests/user-service/` | n/a |
| Fulfillment service | `fulfillment-service` | `tests/fulfillment-service/` | n/a |
| Menu service | `menu-service` | `tests/menu-service/` | n/a |
| UI (web/mobile) | `<brand>` (e.g. `bk`, `plk`, `fhs`, `fz`) | n/a | `e2e/tests/<brand>/` |
| Anything else | `shared` (note in artifact for human override) | `tests/shared/` | n/a |

Validation: assert that `STREAM` matches `^[a-z][a-z0-9-]*$` (lowercase,
no slashes, no leading/trailing whitespace) **before** building any path
or branch name. If validation fails, fall back to `shared` and surface in
`## Sign-Off` notes.

Also infer `<sub-area>` from the dominant API/path noun (e.g. `identify`,
`offer-assignment`, `fulfillment-commit`).

## 2. Branch

```bash
TICKET="<TICKET-ID>"
STREAM="<resolved>"
BRANCH="feature/${STREAM}/${TICKET}/qa-auto-tests"

cd "$REPO"
git fetch --quiet origin
# Idempotency: if the branch already exists locally or remotely, reuse it.
if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  git checkout "$BRANCH"
elif git ls-remote --heads origin "$BRANCH" | grep -q "$BRANCH"; then
  git checkout -b "$BRANCH" "origin/$BRANCH"
else
  git checkout -b "$BRANCH" origin/main
fi
```

## 3. Decide update-vs-new per regression test

For each test case with `regression: true`:

```bash
# Search for similar specs by title keywords + endpoint + similar Jira IDs.
KEYWORDS=("<endpoint>" "<noun1>" "<noun2>")
SIMILAR=$(grep -rln -E "<endpoint>|<noun1>" tests/$STREAM e2e/tests 2>/dev/null || true)
```

- For each candidate file, count keyword matches inside the same
  `describe(...)` block. A block matches if **≥2** keywords hit.
- If a block matches → **update** mode: insert a new `test(...)` inside the
  matched describe; reuse the surrounding fixture import and helpers.
- Else → **new** mode: create
  `tests/<stream>/<sub-area>/<lower-ticket>-<slug>.spec.ts` (or
  `e2e/tests/<brand>/<lower-ticket>-<slug>.spec.ts`).

Always reuse:

- `utils/api-actions/<service>-api-actions.ts` — never re-implement HTTP
  helpers.
- `utils/headers/<service>-headers.ts` — for header construction.
- `utils/constants/endpoints.ts` and the per-service status-code enums.
- `e2e/pages/*` and `e2e/actions/*` for UI flows.

## 4. Test code conventions

Tag and name:

```ts
test.describe("@regression <TICKET-ID> <feature> — <area>", () => {
  test("@regression CBA-XXXX should <observable behaviour>", async ({ request }) => {
    // arrange — pull from fixture, reuse helpers
    // act — single API or UI call
    // assert — concrete status code + body shape, or DOM assertion
  });
});
```

- Add `@smoke` next to `@regression` if the AC is critical-path.
- Embed both the **Jira Test key** (from `qa_jira_issues.json`) and the
  parent story key in the test title — keeps Jira ↔ test mapping discoverable
  via `grep`.
- Place fixture data under
  `fixtures/api/<stream>/<brand>/test-data-api-<brand>-<market>-<env>.json`
  using the existing nested-key convention.

## 5. Lint and format

```bash
cd "$REPO"
npm run lint:fix
npm run format
npm run lint:all     # must succeed before push
```

If `lint:all` exits non-zero:

- Capture stdout/stderr.
- Set `qa_automation.json.lint_status = "fail"` and store the last 80 lines.
- **Do not push, do not open a PR.** Leave the branch checked out locally.
- Set artifact `## Automation PR` to "lint failed — see branch <branch>;
  see qa_automation.json for excerpt".
- Continue (do not abort the whole skill — Steps 1–7 outputs are still valid).

## 6. Commit, push, PR

```bash
git add -A
git commit -m "$(cat <<'EOF'
<TICKET-ID>: add QA automation for <story title>

Generated by sdlc-qa-test-generation (Phase 3b).
Linked Jira tests: <comma-list of test keys>
Plan: docs/artifacts/<TICKET-ID>/ph3b_qa_test_plan.md
EOF
)"
git push -u origin "$BRANCH"

gh pr create \
  --title "<TICKET-ID>: QA automation for <story title>" \
  --body "$(cat <<'EOF'
## Summary
Adds automated regression coverage for <TICKET-ID> generated from the SDLC
pipeline Phase 3b QA test plan.

## Tests
- TC-<TICKET-ID>-01 — <title> → <spec path>
- TC-<TICKET-ID>-02 — <title> → <spec path>
...

## Linked Jira issues
- Parent story: <PARENT-KEY>
- Test issues: <KEY1>, <KEY2>, ...

## Plan link
docs/artifacts/<TICKET-ID>/ph3b_qa_test_plan.md (in the calling project repo)

## Checklist
- [ ] CI green
- [ ] Local: `npm run loyalty -- --grep @regression <TICKET-ID>`
EOF
)"
```

## 7. Idempotent rerun

If `qa_automation.json` already lists a `pr_url`:

- Re-checkout the same branch.
- Apply only the diff: tests not yet in `regression_tests_automated[]`.
- Run lint, commit on top, `git push` (no new PR).
- Append the new tests to `qa_automation.json.regression_tests_automated[]`.
- Comment on the existing PR (via `gh pr comment <pr-number> --body ...`)
  noting the additional tests added on rerun.

## 8. Out of scope

- Modifying `.circleci/config.yml` to add the new spec to a workflow — devs
  do this in PR review, or it is a follow-up automation iteration.
- Backporting tests to release branches.
- Mutating existing tests' assertions (only **adding** test cases inside an
  existing describe is allowed in update mode).
