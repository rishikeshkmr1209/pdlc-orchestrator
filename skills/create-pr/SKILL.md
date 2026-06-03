---
name: 10-create-pr
description: >
  Use when user says "create a PR", "open a pull request", "make a PR",
  "submit a pull request", "create pull request", or "open PR".
  Requires gh CLI authenticated and a non-main working branch.
allowed-tools:
  - Bash
  - Read
---

# Create PR Skill

You are creating a GitHub pull request following project PR standards. Use the `gh` CLI to create the PR after generating an appropriate title and description from the git history.

## Pre-flight Checks

Before creating the PR, verify:

```bash
# 1. Check gh is authenticated
gh auth status

# 2. Confirm not on main/master
BRANCH=$(git branch --show-current)
if [[ "$BRANCH" == "main" || "$BRANCH" == "master" ]]; then
  echo "ERROR: Cannot create PR from main or master branch"
  exit 1
fi

# 3. Check for uncommitted changes
git status --porcelain

# 4. Verify branch has commits ahead of main
git log --oneline $(git merge-base HEAD origin/main)..HEAD
```

If there are uncommitted changes, stop and ask the user to commit or stash them first.

## Extract Jira Ticket ID

**Jira ticket is required by the security team — no exceptions.**

1. Try to extract from the branch name: e.g., `TICKET-1234-add-social-login` → `TICKET-1234`
2. If not found in branch name, check commit messages for a Jira ID pattern (`[A-Z]+-[0-9]+`)
3. If still not found, **ask the user**: "What is the Jira ticket ID for this change? (e.g., TICKET-1234)"

Do not proceed to create the PR until a valid Jira ticket ID is confirmed.

## Gather Context

```bash
# Get commits on this branch (not in main)
git log --oneline --no-merges $(git merge-base HEAD origin/main)..HEAD

# Get changed files
git diff --stat $(git merge-base HEAD origin/main)..HEAD

# Get full diff for context (truncate if large)
git diff $(git merge-base HEAD origin/main)..HEAD -- '*.ts' '*.js' '*.tsx' '*.jsx' | head -200
```

## Generate PR Title

Format: `<TICKET-ID>: <Short description>`

- **TICKET-ID:** The Jira ticket extracted above (e.g., `TICKET-1234`)
- **description:** imperative mood, ≤72 chars, no period at end

Examples:
- `TICKET-1234: Add social login button for Google`
- `TICKET-5678: Fix token expiry race condition on mobile`
- `TICKET-9012: Upgrade aws-sdk to v3`

**Branch naming convention (remind user if branch doesn't already follow this):**
`<TICKET-ID>-short-description` — e.g., `TICKET-1234-add-social-login`

## Generate PR Description

**IRON LAW: You MUST use the EXACT template structure from `templates/pr-description.md`. NEVER generate a custom PR body format. NEVER use `## Summary` as the PR body. NEVER invent your own section headers. The security team requires this specific template — no exceptions.**

Before generating, READ `templates/pr-description.md` to get the exact template.

The PR body MUST contain these sections in this EXACT order:
1. `### Jira Ticket Number` — link format: `[TICKET-ID](https://your-org.atlassian.net/browse/TICKET-ID)` (REQUIRED)
2. `### Type of Change` — check appropriate boxes (Bug fix / New feature / Breaking change / Other)
3. `### Context` — explain **Before** and **After** behavior (not just what changed, but WHY)
4. `### Architecture Document (if applicable)` — link to ADR or write "N/A"
5. `### Evidence / Screenshots / Test Artifacts` — Before/After table or "N/A"
6. `### Postman Collection / SDK Update (if applicable)` — check relevant boxes
7. `### How Has This Been Tested?` — check testing methods used
8. `### Checklist` — ALL project-standard checkboxes from the template (do NOT omit any)
9. `### Anything else we should know?` — additional context or "N/A"

**Rules:**
- Fill in all sections based on git diff, commit messages, and SDLC artifacts (if available)
- If a section has no relevant content, write "N/A" — NEVER skip the section
- The checklist must include ALL items from the template — check applicable ones with `[x]`, leave others as `[ ]`
- If SDLC artifacts exist (verification_report, risk_assessment), include scores and monitoring requirements in the Context section

## Push and Create

```bash
# Push branch to remote
git push -u origin $(git branch --show-current)

# Create the PR
gh pr create \
  --title "JIRA-1234: Your description here" \
  --body "$(cat <<'PREOF'
<generated description using template>
PREOF
)" \
  --base main
```

For work-in-progress:
```bash
gh pr create --draft --title "JIRA-1234: WIP — your description" --body "..."
```

## After Creation

1. Display the PR URL prominently.
2. Remind the user to add screenshots/recordings to the Evidence section if the PR has UI changes.
3. Remind the user to check if Postman collections or SDKs need updating if API contracts changed.
4. Check if CI started: `gh pr checks --watch` (optional — ask user).
5. Suggest adding reviewers if known: `gh pr edit --add-reviewer <username>`.

## Safety Rules

- Never create a PR without a Jira ticket ID — it is required by the security team.
- Never create a PR targeting a branch other than `main` without explicit user instruction.
- Never force-push during this process.
- If the branch is already behind `main`, ask the user whether to rebase first.
- Never add `[skip ci]` to commit messages.

## References

- `templates/pr-description.md` — standard PR description template

## Evaluation

| Scenario | Input | Expected behavior |
|----------|-------|-------------------|
| Trigger — positive | "create a PR for my changes" | Skill activates, runs pre-flight, generates PR |
| Trigger — positive | "open a pull request" | Skill activates |
| Trigger — negative | "what is a pull request?" | Skill does NOT activate |
| Pre-flight failure | On main branch | Reports error, does not create PR |
| Pre-flight failure | Uncommitted changes | Asks user to commit first |
| No commits | Branch same as main | Reports "no commits to PR" |
