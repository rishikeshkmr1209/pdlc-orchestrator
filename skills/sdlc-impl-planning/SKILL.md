---
name: 04-sdlc-impl-planning
description: >
  Use when sdlc-pipeline invokes after design review approval. Reads all prior
  SDLC artifacts and produces a self-contained implementation plan.
allowed-tools:
  - Read
  - Grep
  - Glob
  - Write
  - Bash
---

# SDLC Implementation Planning Skill

You are producing a self-contained implementation plan from prior SDLC artifacts. The plan must contain enough context that a fresh session (with no prior conversation history) can execute it correctly and continue through remaining pipeline phases.

## Arguments

| Argument             | Required | Description                               |
| -------------------- | -------- | ----------------------------------------- |
| `--ticket=TICKET-ID` | Yes      | Jira ticket ID. Used to locate artifacts. |

## Process

> **Before reading any files:** Read `skills/_shared/parallel-reads-rule.md` and follow it for all file reads in this phase.

### 1. Load Artifacts

Extract only the required sections from each artifact using the extraction script:

```bash
python3 claude-master-plugin/scripts/extract-sections.py \
  docs/artifacts/<ticket>/ph1_problem_spec.md \
  "Requirements" "Acceptance Criteria" "Constraints" "Non-Goals" "Assumptions" "Edge Cases" "Figma Design Reference" "Design Tokens"

python3 claude-master-plugin/scripts/extract-sections.py \
  docs/artifacts/<ticket>/ph2_design_spec.md \
  "Architecture" "Implementation Guidelines" "Testing Strategy" "Data Models"

python3 claude-master-plugin/scripts/extract-sections.py \
  docs/artifacts/<ticket>/ph3_design_review.md \
  "Summary" "Architectural Review" "Complexity Concerns" "Missing Considerations"

# ph3b is OPTIONAL — only present when the phase_set includes
# qa-test-generation (Small Feature, Large Feature). If the file is absent,
# extract-sections.py prints a warning but the impl-planning skill proceeds
# without it. When present, fold the QA test plan into the testing section of
# the implementation plan so implementers know which ACs are already covered
# by automation and which still need manual coverage.
if [ -f "docs/artifacts/<ticket>/ph3b_qa_test_plan.md" ]; then
  python3 claude-master-plugin/scripts/extract-sections.py \
    docs/artifacts/<ticket>/ph3b_qa_test_plan.md \
    "AC → Test Matrix" "Regression Subset" "Automation PR"
fi
```

(See `claude-master-plugin/config/phase-artifact-map.json → Ph4_impl_planning`.)
**Reuse codebase scan if present:**

Extract the `Codebase Scan` section from `docs/artifacts/<ticket>/.state/artifact-digest.md`:
```bash
python3 claude-master-plugin/scripts/extract-sections.py \
  docs/artifacts/<ticket>/.state/artifact-digest.md \
  "Codebase Scan"
```
(See `claude-master-plugin/config/phase-artifact-map.json → Ph4_impl_planning`.)

If the section exists and lists files under **Files scanned:**:
- For each file entry: load `Purpose` and `Findings` into working memory — treat the file as already-read
- Do NOT re-read those files during step 2 (Build Ordered File List) — use `Findings` directly
- Read **Verified facts** — skip Glob existence checks for any path already confirmed there
- Read **Open questions** — these files still need reading; include them in step 2
- **Load `Repo Conventions` per affected repo** — capture each repo's test command, module structure, and naming. Used in steps 2 and 5.

If the section is absent: proceed with standard Glob-based file existence checks.

**Load affected repos:**
```bash
python3 -c "
import json
state = json.load(open('docs/artifacts/<ticket>/.state/pipeline_state_<ticket>.json'))
repos = state.get('affected_repos', {}).get('repos', [])
print(repos)
"
```
If `repos` has more than one entry: this is a **multi-repo plan**. Group implementation steps by repo (see Step 7 template). Each repo gets its own step group, pre-implementation baseline, and test command.

If any MD artifact is missing, HALT and report:

```
Missing artifact: <file> at docs/artifacts/<ticket>/
Cannot produce implementation plan without it. Run the preceding phase first.
```

### 2. Build Ordered File List

From `design_spec.implementation_guidelines.file_structure[]`:

1. Extract each file entry: path, purpose, component ID (from parent component)
2. Determine new-vs-modify status: use Glob to check if the file already exists on disk
3. Attach dependency info from the parent component's `dependencies[]`

### 3. Compute Dependency Graph and Wave Assignments

From `design_spec.components[]`:

1. Build adjacency list from each component's `dependencies[]`
2. Topological sort: Wave 0 = components with no dependencies, Wave N = components whose ALL dependencies are in waves 0..N-1
3. If circular dependency detected: HALT and report the cycle
4. Assign each file to the wave of its parent component

### 4. Map Acceptance Criteria to Files

From `problem_spec.requirements[]`:

- For each requirement's acceptance criteria (AC-###), determine which implementation file(s) satisfy it based on component mapping and file purposes
- Create a lookup: file path -> list of AC-### IDs

### 5. Map Test Strategy Per File

From `design_spec.testing_strategy` and `Repo Conventions` in artifact-digest.md:

- For each implementation file, determine the test approach (unit, integration, e2e)
- Use the **test command from `Repo Conventions`** for that file's repo (e.g., `pnpm test --filter=<repo-name>`)
- For multi-repo plans: each repo has its own test command — never use one repo's test command to verify another repo's files
- Note coverage targets per repo

### 6. Identify Risks and Backward-Compatibility Concerns

Aggregate from:

- `ph3_design_review.md` conditions and concerns
- `ph1_problem_spec.md` constraints and edge cases
- Any backward-compatibility implications from modifying existing files

### 7. Write Implementation Plan

Write `ph4_implementation_plan.md` using the template below.

### 8. Update Artifact Digest

Append an `## Implementation Plan` section to `docs/artifacts/<ticket>/.state/artifact-digest.md`:

```markdown
## Implementation Plan (ph4_implementation_plan.md)

- Steps: <N> files (<M> new, <K> modified)
- Waves: <W> (if >8 files or wave mode)
- Execution mode: <inline|waves>
- Key risks: <1-2 line summary>
- Design review conditions addressed: <yes/no + details>
```

## Implementation Plan Template

Write the following template to `docs/artifacts/<ticket>/ph4_implementation_plan.md`, filling in all placeholders from artifact data:

```markdown
# Implementation Plan: <TICKET-ID>

## Pipeline Context

- **Ticket:** <TICKET-ID>
- **Mode:** <auto|gates>
- **Pipeline state:** docs/artifacts/<ticket>/.state/pipeline_state_<ticket>.json
- **Artifacts:** docs/artifacts/<ticket>/ (ph1_problem_spec.md, ph2_design_spec.md, ph3_design_review.md)

## Problem Summary

<2-3 sentences from problem_spec.problem_statement — what we're solving and why>

## Key Requirements & Constraints

| ID      | Priority | Description         |
| ------- | -------- | ------------------- |
| REQ-001 | P0       | <from problem_spec> |
| REQ-002 | P1       | <from problem_spec> |

**Constraints (from problem_spec + design_review):**

- <technical constraint 1>
- <business constraint 1>
- <design review condition if any>

**Non-Goals:** <list from problem_spec.non_goals — what we are NOT doing>

## Figma Design Token Constraints

*(Include only when `pipeline_state_<ticket>.json figma.fetched == true`. Omit section entirely if no Figma link was fetched.)*

- **Viewport:** `<mobile/tablet/desktop — from ## Design Tokens § Viewport Context>`
- **Components with Figma specs:** `<list component names from ## Design Tokens that are NEW in this ticket>`
- **States specified:** `<e.g., PausedDeliveryBanner: default, :hover, :disabled>`
- **Critical values (implementor must NOT deviate):**
  - `<ComponentName>`: border-radius `<value>`, padding `<value>`, background `<value>`
  - `<ComponentName>`: font-size `<value>`, font-weight `<value>`
- **Full spec location:** `docs/artifacts/<ticket>/ph1_problem_spec.md § Design Tokens`

> Implementation MUST reference the full Design Tokens section in ph1_problem_spec.md when writing any CSS for these components. Do not invent or approximate values.

## Architecture Summary

<Key decisions from design_spec: patterns used, component structure, data flow summary>

## Design Review Conditions

<Any conditions or concerns from ph3_design_review.md that must be addressed during implementation>

## Affected Repos

<List each repo from pipeline_state_<ticket>.json affected_repos.repos[]>
- `<repo-name>`: <what changes in this repo — 1 line>
- `<repo-name>`: <what changes in this repo — 1 line>

*(Single-repo: write "Single-repo change — <repo-name> only")*

## Pre-Implementation Baseline

<For single-repo:>
- Run: `<test command from Repo Conventions>` and record pass/fail counts before ANY changes

<For multi-repo — one entry per repo:>
- `<repo-name>`: Run `<repo test command>` and record pass/fail counts
- `<repo-name>`: Run `<repo test command>` and record pass/fail counts

## Implementation Steps

### Execution Mode: <inline|waves>

<For single-repo: list steps in dependency order.>
<For multi-repo: group steps under a header per repo. Within each group, order by dependency. Implement repos in the order that satisfies cross-repo dependencies — upstream changes first.>

---
### Repo: `<repo-name>` *(omit this header for single-repo)*
---

### Step N: <file path> (<new|modify>) [COMP-###]

- **Repo:** `<repo-name>` *(omit for single-repo)*
- **Purpose:** <from file_structure[].purpose>
- **Dependencies:** <COMP-### IDs that must exist first>
- **Key notes:** <pattern, security consideration, design review condition>
- **Figma CSS spec:** <component name from ## Design Tokens this step implements — e.g., "PausedDeliveryBanner (default + :hover + :disabled states)". Write "N/A" if this file has no Figma spec. Write "See Design Tokens §ComponentName" if it does.>
- **Acceptance criteria:** <REQ-### AC-### mappings>
- **Verify:** `<repo-specific test command>`

## Wave Plan

<Include if >8 files or --waves flag. Otherwise write "N/A — inline execution (≤8 files)">

| Wave | Files                  | Dependencies Satisfied | Test Command |
| ---- | ---------------------- | ---------------------- | ------------ |
| 0    | types.ts, constants.ts | none                   | <test cmd>   |
| 1    | service.ts             | Wave 0                 | <test cmd>   |

## Risks

| Risk              | Impact        | Mitigation                           |
| ----------------- | ------------- | ------------------------------------ |
| <backward compat> | <what breaks> | <run tests first, preserve defaults> |

## Edge Cases (from problem_spec)

| ID     | Scenario   | Expected Behavior |
| ------ | ---------- | ----------------- |
| EC-001 | <scenario> | <behavior>        |

## Post-Implementation Checklist

- [ ] All tests pass (no regressions from baseline)
- [ ] ph5_6_impl_manifest.md written with accurate file lists
- [ ] Health check endpoints verified (if applicable)
- [ ] No PII in log statements

## Pipeline Continuation

**CRITICAL: This implementation is part of SDLC pipeline for <TICKET-ID>.**
After implementation completes, the pipeline MUST continue through:

- Phase 6: Simplify (simplify)
- Phase 7: Review (spec-reviewer + test-engineer + security-auditor)
- Phase 8: Verification (sdlc-verify --ticket=<TICKET-ID>)
- Phase 9: Risk Assessment (sdlc-risk --ticket=<TICKET-ID>)
- Phase 10: PR Creation (create-pr)

**DO NOT skip phases 6-10. DO NOT jump directly to PR creation.**

Resume command: `/client-master:00-sdlc-pipeline --ticket=<ticket> --resume`
```

## Validation

Before completing, verify:

1. `ph4_implementation_plan.md` exists and is non-empty
2. Plan contains `## Implementation Steps` with at least one step
3. Plan contains `## Pipeline Continuation` section
4. Plan contains `## Pre-Implementation Baseline` section
5. Each step has file path, new/modify status, component ID, and verify command
6. .state/artifact-digest.md has been updated with Implementation Plan section

## Error Handling

| Condition            | Behavior                                                                       |
| -------------------- | ------------------------------------------------------------------------------ |
| Missing artifact     | HALT with specific file path and which phase produces it                       |
| Empty file_structure | HALT — design_spec has no implementation files defined                         |
| Circular dependency  | HALT — report the cycle of component IDs                                       |
| No test strategy     | WARN — proceed but note "no test strategy defined" in each step's Verify field |

## Evaluation

| Scenario           | Input                                                  | Expected behavior                                  |
| ------------------ | ------------------------------------------------------ | -------------------------------------------------- |
| Trigger — positive | sdlc-pipeline invokes after design review approval     | Reads artifacts, produces ph4_implementation_plan.md   |
| Trigger — positive | "sdlc-impl-planning --ticket=TICKET-123"                  | Reads artifacts, produces plan                     |
| Trigger — negative | "plan my implementation" (no ticket context)           | Does NOT activate                                  |
| Missing artifact   | ph2_design_spec.md not found                               | HALTs with clear error                             |
| Circular deps      | COMP-001 depends on COMP-002 which depends on COMP-001 | HALTs with cycle report                            |
| Large file count   | 12 files in file_structure                             | Produces wave plan table                           |
| Small file count   | 4 files in file_structure                              | Sets execution mode to inline, wave plan shows N/A |
