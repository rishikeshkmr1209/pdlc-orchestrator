# Jira MCP cookbook

Exact tool calls and payload shapes used by Step 3 (JQL discovery) and Step 5
(register tests). All calls go through the user's globally-configured
Atlassian MCP — the plugin does not bake credentials.

## Resolve cloud ID once per run

```
mcp__atlassian__getAccessibleAtlassianResources
→ pick the cloudId for "your-org.atlassian.net"
```

Cache it for all subsequent calls in this skill run.

## Step 3 — Search existing Zephyr tests via JQL filter 28319

```
mcp__atlassian__searchJiraIssuesUsingJql
  cloudId: <cloudId>
  jql: 'filter = 28319 AND (text ~ "<endpoint or component>" OR text ~ "<AC keyword>")'
  fields: ["summary", "issuetype", "status", "issuelinks", "labels"]
  limit: 50
```

For each hit compute a match score:
- +2 if the existing test's `summary` contains a primary keyword from the AC
  (endpoint name, component name, or domain noun).
- +1 per additional keyword match.
- +2 if `issuelinks` already references a story in the same epic as the
  parent.

Threshold for "strong overlap" (decision: update) = score ≥ 3.

## Step 5a — Create a Jira Test issue (decision: new)

```
mcp__atlassian__createJiraIssue
  cloudId: <cloudId>
  projectKey: "<from parent story key, e.g. ILO>"
  issueTypeName: "Test"
  summary: "<test title — keep under 120 chars>"
  description: |
    <markdown body — see test-case-template.md "Markdown rendering">

    ## Linked Acceptance Criteria
    - AC-001
    - AC-002

    Parent story: <PARENT-KEY>
  additionalFields:
    labels: ["sdlc-pipeline", "phase-3b", "auto-generated", "<TICKET-ID>"]
```

Capture the returned `key` (e.g. `TICKET-1235`).

## Step 5b — Link Test → Story with type "Tests"

The Jira "Tests" link type has `outward: "tests"` and
`inward: "is tested by"`. Read as: *outwardIssue* **tests** *inwardIssue*.
The Test issue is the subject of "tests" (it does the testing); the parent
story is the object (it is being tested). So:

- `outwardIssueKey` = the new Test issue
- `inwardIssueKey`  = the parent story

```
mcp__atlassian__createIssueLink
  cloudId: <cloudId>
  type: "Tests"
  outwardIssueKey: "<NEW-TEST-KEY>"      # Test (subject of "tests")
  inwardIssueKey:  "<PARENT-STORY-KEY>"  # Story (object — "is tested by")
```

(Verify the link-type name in your Jira instance with
`mcp__atlassian__getIssueLinkTypes`. The conventional name is `Tests` /
`is tested by`. If your instance renames either side, swap accordingly and
record the canonical mapping in `qa_test_plan.md ## Sign-Off`.)

## Step 5c — Update path (decision: update)

Do **not** edit the existing Test issue's description. Comment instead:

```
mcp__atlassian__addCommentToJiraIssue
  cloudId: <cloudId>
  issueIdOrKey: "<EXISTING-TEST-KEY>"
  commentBody: |
    Phase 3b for <PARENT-STORY-KEY> proposes the following delta on this test:

    **Added preconditions**
    - <bullet>

    **Added/updated steps**
    1. <step>

    **Refined expected**
    <expected>

    **Newly mapped ACs**
    - AC-00X (story <PARENT-KEY>)
```

If the existing test is not yet linked to the parent story, also call
`createIssueLink` per Step 5b.

## Step 9 — Summary comment on the parent story

```
mcp__atlassian__addCommentToJiraIssue
  cloudId: <cloudId>
  issueIdOrKey: "<PARENT-STORY-KEY>"
  commentBody: |
    **Phase 3b — QA Test Generation complete**

    - Test cases generated: N (regression subset: M)
    - Jira Test issues created: K (see labels: phase-3b, <TICKET-ID>)
    - Existing Zephyr tests amended (comment-only): J
    - Automation PR: <url or "lint failed; branch <name> left local">
    - Plan: docs/artifacts/<TICKET>/ph3b_qa_test_plan.md
```

Post once per skill run. On idempotent reruns, only post if the artifact has
materially changed (new tests, new PR url, or a status change).

## Failure handling

- If `createJiraIssue` fails: log the failure to `qa_jira_issues.json` with
  `action: "create-failed"` and the error message; continue with the remaining
  tests rather than aborting the skill.
- If `createIssueLink` fails (e.g. link type name differs): record the
  unlinked key under `qa_jira_issues.json[].link_status: "unlinked"` and
  surface in the `## Sign-Off` notes.
