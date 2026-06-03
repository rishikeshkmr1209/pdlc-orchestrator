---
name: jira-classification
description: >
  Phase 0 of the SDLC pipeline. Classifies a JIRA ticket into one of six
  types (Hotfix, Bug, Spike, Story, Small Feature, Large Feature) and determines
  the phase set to execute. Always invoked automatically by sdlc-pipeline before
  any other phase starts.
allowed-tools:
  - Read
  - Bash
  - Write
---

# JIRA Classification Skill

## Prime Directive

> **Classify first, build right.** The wrong phase set wastes days. The right phase set ships confidently.

This skill determines what kind of work a JIRA ticket represents and maps it to the correct SDLC pipeline execution plan. It runs as **Phase 0** — before any artifact is created, before any phase starts. The pipeline cannot proceed until classification is confirmed by the user.

---

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--ticket=TICKET-ID` | Yes | JIRA ticket ID (e.g., `PROJECT-7842`, `TICKET-1234`) |

---

## Input Modes

This skill operates in two modes depending on how the pipeline was invoked:

### Mode A — JIRA API
When the user runs `/client-master:00-sdlc-pipeline --ticket=PROJECT-7842` without pasting ticket content, fetch the ticket from JIRA using the MCP Atlassian tool. Extract: summary, description, issue type, labels, components, priority, acceptance criteria, linked issues.

### Mode B — Inline Text
When the user pastes ticket content directly into the command (e.g., `/client-master:00-sdlc-pipeline --ticket=PROJECT-7842 <pasted text>`), use the pasted content directly. No API call needed.

After processing inline text in Step 2.5, if no Figma link is detected in the pasted content, ask the user once:
> "Do you have a Figma design link for this ticket? If yes, paste the URL — otherwise reply 'no'."
If the user provides a URL: use it as `figma.link`. If they say 'no' or skip: leave `figma.link` as null.

If neither JIRA API access nor inline text is available, ask the user to paste the ticket content before proceeding.

---

## Process

### Step 1: Load Classification Config

Read `claude-master-plugin/config/jira_execution_phases.json` to load all phase sets and their descriptions.

### Step 2: Normalize Ticket Data

**Strip null fields before analysis.** JIRA API responses include many null/empty fields that add noise without signal. Before extracting classification signals, remove:
- Any field whose value is `null`, `""`, `[]`, or `{}`
- Nested objects where all child fields are null
- Fields irrelevant to classification (e.g., `watches`, `votes`, `worklog`, `attachment`, `timetracking`, `aggregatetimespent`)

For **Mode A** (JIRA API): apply this normalization to the raw MCP response object before analysis.
For **Mode B** (inline text): skip — user-pasted content is already trimmed.

Only carry forward fields that have non-null, non-empty values into Step 3 analysis.

### Step 2.5: Detect Figma Links

Scan the normalized ticket text (description, comments, and any `remoteLinks` or `attachment` URLs) for Figma URLs matching:

```
https://www\.figma\.com/(file|design|proto)/[A-Za-z0-9]+
```

- **If one or more Figma links are found:** set `figma.link` to the first match (prefer `file` or `design` over `proto`). Multiple links → pick the one most likely to be the primary design file (e.g., labeled "Design" or "UI" in surrounding text).
- **If no Figma link is found:** leave `figma.link` as null — the figma object is still initialized in Step 8 with `fetched: false`.

This value is stored in `pipeline_state_<ticket>.json` at Step 8 and drives the Figma Design Fetch in Phase 1 (requirements Step 3.5) and the Figma Component Audit in Phase 4.5.

### Step 3: Analyze Ticket

From the normalized ticket content, extract and evaluate:

| Signal | What to look for |
|--------|-----------------|
| **Issue type** | JIRA's own type field (Bug, Story, Epic, Task, Spike) — use as a strong signal but not the only one |
| **Summary** | Keywords: "fix", "broken", "regression", "crash" → Bug/Hotfix; "investigate", "research", "explore", "spike" → Spike; "add", "build", "implement" → Feature/Story |
| **Description length** | Short + urgent → Hotfix/Bug; long + detailed → Feature |
| **Priority** | Blocker/Critical + production impact → Hotfix; others → Bug or Feature |
| **Acceptance criteria** | Present and detailed → Story/Feature; absent → Bug/Hotfix/Spike |
| **Components affected** | Multiple brands or shared infra → Large Feature; single component → Small Feature/Story |
| **Labels** | Look for "hotfix", "spike", "tech-debt", "design-required" |
| **Linked issues** | Many dependencies → Large Feature |

### Step 4: Determine Classification and Confidence

Based on the signals, select the classification type and assign a confidence score (0.0–1.0):

| Type | Key indicators |
|------|---------------|
| **Hotfix** | Production broken, blocker/critical priority, needs immediate fix |
| **Bug** | Defect with known cause, not production-critical, no new functionality |
| **Spike** | Investigation question, time-box mentioned, no deliverable code expected |
| **Story** | User-facing behaviour change, clear ACs, no architectural uncertainty |
| **Small Feature** | New functionality, contained scope, single team, no cross-brand impact |
| **Large Feature** | Multi-brand, architectural change, cross-team dependencies, extensive ACs |

### Step 5: Present Findings to User

Always show the classification findings before proceeding. Format:

```
Classification: Large Feature (confidence: 0.91)

Reasoning:
- Ticket involves new component architecture (e.g., new UI components and hooks)
- Affects multiple brands/tenants via brand-specific configuration
- 9 acceptance criteria across 4 requirements
- Feature flag dependency with multi-region rollout

Phase set that will execute (10 phases):
  requirements → architecture → design-review → impl-planning →
  implementation → simplify → review → verification → risk → pr

Confirm? (yes / or type a different classification: Hotfix | Bug | Spike | Story | Small Feature | Large Feature)
```

### Step 6: Handle User Response

- **User confirms** (yes / y): proceed with detected classification. Set `user_override: null`.
- **User provides a different type**: use the user-provided type. Look up its phase set from `jira_execution_phases.json`. Set `user_override: "<UserProvidedType>"`.
- **User asks why**: explain the reasoning in more detail, then re-present the confirmation prompt.

### Step 7: Resolve Affected Repos

Before writing `pipeline_state_<ticket>.json`, identify which repos are affected by this ticket.

**Primary source — JIRA `components` field:**
- Extract the `components` array from the normalized ticket data
- Each component value is a service/repo name (e.g., `"<service-name>"`, `"<gateway-service>"`)
- Verify each component exists as a directory under `PROJECT_ROOT` using Glob: `<component>/package.json`
- Set `confidence: "high"` if one or more verified components found

**Fallback — JIRA `summary` + `description` keyword matching:**
- If `components` is empty or no components verified on disk:
  - Read `.claude/codebase-index/index.json` → check `domain_concepts`
  - Extract service-name keywords from summary/description (e.g., domain-specific service and module names)
  - Match against `domain_concepts` keys and repo names in `modules[]`
  - Set `confidence: "low"`
- If no match found at all: set `repos: []`, `confidence: "unresolved"`

### Step 8: Initialize Pipeline State

Once classification is confirmed, run `mkdir -p docs/artifacts/<ticket>/.state` from the project root to create the full directory path, then write `pipeline_state_<ticket>.json`.

The `phases` object must contain **only the phases in the confirmed phase set** — no others. Each phase is initialized as `pending`.

**Model assignments — always read at runtime from `claude-master-plugin/config/pipeline-models.json` (single source of truth — no hardcoded values here):**

```bash
python3 -c "import json; cfg=json.load(open('claude-master-plugin/config/pipeline-models.json')); print(json.dumps(cfg))"
```

- For each phase in the confirmed phase set, assign `model` from `cfg['phases'][<phase>]['model']` (or `cfg['default']['model']` if not listed).
- If classification type is `Large Feature`, override planning-phase models using `cfg['large_feature_overrides'][<phase>]['model']` where present.
- All other classification types use only the default `phases` values.
- **Never hardcode model names here.** If model values change, update only `pipeline-models.json`.

```json
{
  "ticket": "<TICKET-ID>",
  "classification": {
    "type": "<confirmed type>",
    "confidence": 0.0,
    "reasoning": "<one sentence summary of key signals>",
    "phase_set": ["<phase1>", "<phase2>"],
    "classified_at": "<ISO8601 IST>",
    "user_confirmed_at": "<ISO8601 IST>",
    "user_override": null
  },
  "affected_repos": {
    "source": "jira_components",
    "repos": ["<repo1>", "<repo2>"],
    "confidence": "high"
  },
  "mode": "gates",
  "started_at": "<ISO8601 IST>",
  "updated_at": "<ISO8601 IST>",
  "current_phase": "<first phase in phase_set>",
  "phases": {
    "<phase>": { "status": "pending", "model": "<model>", "started_at": null, "completed_at": null, "duration_ms": null, "user_wait_ms": 0, "active_duration_ms": null, "active_wallclock_time_taken": null, "iterations": 0, "tokens_used": { "cache_creation": null, "cache_read": null, "input": null, "output": null, "total": null, "cost_usd": null } }
  },
  "tokens_summary": { "total_cache_creation": 0, "total_cache_read": 0, "total_input": 0, "total_output": 0, "total": 0, "total_cost_usd": 0 },
  "model_transitions": {},
  "figma": { "link": "<detected-url-or-null>", "fetched": false, "figma_to_new_component_mapping": null }
}
```

### Step 8: Initialize Artifact Digest

Create `docs/artifacts/<ticket>/.state/artifact-digest.md` with initial classification info:

```markdown
# Artifact Digest: <TICKET-ID>

## Classification
- Type: <confirmed type>
- Phase set: <phase1> → <phase2> → ...
- Reasoning: <one sentence summary>
```

If the file already exists (pipeline resuming), update only the `## Classification` section — do not overwrite other sections.

### Step 9: Hand Off to Pipeline

Return control to `sdlc-pipeline` with:
- Confirmed classification type
- Confirmed phase set
- Confirmation that `pipeline_state_<ticket>.json` and `artifact-digest.md` are initialized

The pipeline reads `pipeline_state_<ticket>.json` to determine which phases to execute and in what order.

---

## Output Summary (Terminal)

After completing, display:

```
Phase 0 complete — Classification confirmed

  Type:       Large Feature
  Confidence: 0.91
  Phase set:  requirements → architecture → design-review → impl-planning →
              implementation → simplify → review → verification → risk → pr

  Artifacts initialized:
    docs/artifacts/<ticket>/.state/pipeline_state_<ticket>.json  ✓
    docs/artifacts/<ticket>/.state/artifact-digest.md  ✓

Starting Phase 1: requirements ...
```

---

## Error Handling

| Condition | Behavior |
|-----------|----------|
| JIRA API unavailable | Ask user to paste ticket content inline |
| Ticket not found | Report ticket ID not found, ask user to verify |
| Ambiguous classification | Present top 2 candidates with reasoning, ask user to choose |
| Unknown user response | Re-present the confirmation prompt with valid options listed |
| `jira_execution_phases.json` missing | HALT — report path and ask user to restore config |
