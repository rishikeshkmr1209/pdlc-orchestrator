---
name: sdlc-checkpoint
user-invocable: false
description: >
  Use when user says "save checkpoint", "load checkpoint", "checkpoint status",
  "validate artifacts", or when sdlc-pipeline invokes at phase boundaries.
  All artifacts are Markdown files validated by required section headers.
allowed-tools:
  - Read
  - Write
  - Glob
  - Bash
---

# SDLC Checkpoint Skill

You are managing SDLC pipeline checkpoint artifacts. Your role is to persist, retrieve, validate, and track structured phase outputs so the pipeline is resumable across context boundaries.

## Operations

### 1. save <phase> <ticket-id>

Save a structured artifact for the given phase and ticket.

1. **Determine storage location** using the Storage Rules table below.
2. **Create directories** by running from the project root (replace `<ticket-id>` with the actual ticket ID):
   ```bash
   mkdir -p docs/artifacts/<ticket-id>/.state
   ```
   This creates both `docs/artifacts/<ticket-id>/` and `.state/` in one step.
3. **Write the structured artifact** to the resolved path with the filename from the Storage Rules table.
4. **Validate the artifact** using the rules in the Required Sections Validation section below.
   - Report any validation failures but still save the artifact.
5. **Update pipeline_state_<ticket>.json** in `docs/artifacts/<ticket-id>/.state/`:
   - Set the phase status to `completed`.
   - Set `completed_at` to the current ISO 8601 timestamp.
   - Set `artifact_path` to the written file path.
   - Set `schema_valid` to the validation result.
   - Update `updated_at` on the root object.
   - Preserve `current_phase` — this field is managed by the pipeline orchestrator, not the checkpoint skill.
6. **Report** the saved path and schema validity.

### 2. load <phase> <ticket-id>

Load a previously saved artifact back into context.

1. **Determine artifact path** by reading `docs/artifacts/<ticket-id>/.state/pipeline_state_<ticket>.json` for the phase's `artifact_path`. If pipeline_state_<ticket>.json does not exist, fall back to the default path from the Storage Rules table.
2. **Read the artifact file** into context.
3. **Validate** using the rules in the Required Sections Validation section below.
4. **Report** what was loaded, its timestamp, and schema validity status.

### 3. status <ticket-id>

Display the current pipeline state for a ticket.

1. **Read** `docs/artifacts/<ticket-id>/.state/pipeline_state_<ticket>.json`.
2. If it does not exist, **scan for artifacts** in `docs/artifacts/<ticket-id>/` using Glob.
3. **Display a table** with the following columns:

```
| Phase          | Status      | Artifact Path                          | Timestamp           |
|----------------|-------------|----------------------------------------|---------------------|
| requirements   | completed   | docs/artifacts/TICKET-123/problem_spec... | 2026-02-25T10:00:00 |
| architecture   | pending     | —                                      | —                   |
| ...            | ...         | ...                                    | ...                 |
```

4. Include a summary line: `X of 10 phases completed. Current phase: <phase_name>.`

### 4. validate <ticket-id>

Validate all artifacts for a ticket against their schemas.

1. **Find all artifacts** for the ticket in both storage locations using Glob.
2. **For each artifact found**, validate using the rules in the Required Sections Validation section below.
3. **Report a validation table:**

```
| File                | Status  | Issues              |
|---------------------|---------|---------------------|
| ph1_problem_spec.md     | valid   | —                   |
| ph2_design_spec.md      | invalid | missing: components |
```

4. **Update pipeline_state_<ticket>.json** with the `schema_valid` result for each validated phase.

## Storage Rules

| Phase          | Artifact File          | Location                            | Git-tracked? |
| -------------- | ---------------------- | ----------------------------------- | ------------ |
| requirements   | ph1_problem_spec.md        | docs/artifacts/&lt;ticket&gt;/        | Yes          |
| architecture   | ph2_design_spec.md         | docs/artifacts/&lt;ticket&gt;/        | Yes          |
| design-review  | ph3_design_review.md       | docs/artifacts/&lt;ticket&gt;/        | Yes          |
| impl-planning  | ph4_implementation_plan.md | docs/artifacts/&lt;ticket&gt;/        | Yes          |
| implementation | ph5_6_impl_manifest.md     | docs/artifacts/&lt;ticket&gt;/        | Yes          |
| implementation | impl_state.json            | docs/artifacts/&lt;ticket&gt;/.state/ | No           |
| verification   | ph8_verification_report.md | docs/artifacts/&lt;ticket&gt;/        | Yes          |
| risk           | ph9_risk_assessment.md     | docs/artifacts/&lt;ticket&gt;/        | Yes          |

**Rationale:** All artifacts live in `docs/artifacts/<ticket>/` so they are version-controlled and reviewable in PRs. Runtime state (pipeline_state_<ticket>.json, impl_state.json, artifact-digest.md) lives in the `.state/` subdirectory and should be gitignored.

**Note on impl_state.json:** This is a mid-implementation checkpoint written after each file (inline mode) or wave (wave mode). It tracks per-file progress and enables `--resume` to skip already-completed files. It is optional — the pipeline functions without it (it just can't resume mid-implementation).

## Pipeline State Schema

The file `docs/artifacts/<ticket-id>/.state/pipeline_state_<ticket>.json` tracks overall progress. This schema is the **canonical source of truth** — it matches identically with the schema defined in `sdlc-pipeline/SKILL.md`.

```json
{
  "ticket": "string",
  "mode": "gates",
  "started_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "current_phase": "<phase-name>",
  "phases": {
    "<phase_name>": { "status": "pending|in_progress|completed|failed", "model": "<model>", "started_at": "ISO-8601|null", "completed_at": "ISO-8601|null", "duration_ms": null, "user_wait_ms": 0, "active_duration_ms": null, "active_wallclock_time_taken": null, "iterations": 0, "tokens_used": { "cache_creation": null, "cache_read": null, "input": null, "output": null, "total": null, "cost_usd": null } }
  },
  "tokens_summary": { "total_cache_creation": 0, "total_cache_read": 0, "total_input": 0, "total_output": 0, "total": 0, "total_cost_usd": 0 },
  "model_transitions": {}
}
```

> See `sdlc-pipeline/SKILL.md` → Pipeline State Schema for the full authoritative schema.

### Field Definitions

- **ticket** — Jira ticket identifier (e.g., `TICKET-1234`).
- **mode** — Always `"gates"`.
- **started_at** — ISO 8601 timestamp when the pipeline was first invoked.
- **updated_at** — ISO 8601 timestamp of the most recent phase completion or state change.
- **current_phase** — Name of the currently active phase. Managed by the pipeline orchestrator.
- **phases** — Map of phase name → phase state. Only phases in the confirmed phase set are present.

### Per-Phase Fields

- **status** — `pending`, `in_progress`, `completed`, or `failed`.
- **started_at / completed_at** — ISO 8601 IST timestamps.
- **duration_ms / active_duration_ms** — wall-clock and active (minus user wait) durations.
- **iterations** — Number of times this phase has run.
- **tokens_used** — All 6 fields required: `cache_creation`, `cache_read`, `input`, `output`, `total`, `cost_usd`.

### Field Ownership

The pipeline orchestrator and checkpoint skill both read/write `pipeline_state_<ticket>.json`. To avoid conflicts:

- **Pipeline orchestrator manages:** `current_phase`, `model_transitions`, per-phase `iterations`, `tokens_used`, `tokens_summary`
- **Checkpoint skill manages:** per-phase `status`, `completed_at`, `updated_at`
- **Both may update:** `status`, `updated_at`

### Initializing Pipeline State

When creating a new pipeline_state_<ticket>.json, initialize all ten phases:

```json
{
  "ticket": "<ticket-id>",
  "mode": "gates",
  "started_at": "<now>",
  "updated_at": "<now>",
  "current_phase": "<first phase in phase_set>",
  "phases": {
    "requirements":   { "status": "pending", "model": "<model>", "started_at": null, "completed_at": null, "duration_ms": null, "user_wait_ms": 0, "active_duration_ms": null, "active_wallclock_time_taken": null, "iterations": 0, "tokens_used": { "cache_creation": null, "cache_read": null, "input": null, "output": null, "total": null, "cost_usd": null } },
    "impl-planning":  { "status": "pending", "model": "<model>", "started_at": null, "completed_at": null, "duration_ms": null, "user_wait_ms": 0, "active_duration_ms": null, "active_wallclock_time_taken": null, "iterations": 0, "tokens_used": { "cache_creation": null, "cache_read": null, "input": null, "output": null, "total": null, "cost_usd": null } },
    "implementation": { "status": "pending", "model": "<model>", "started_at": null, "completed_at": null, "duration_ms": null, "user_wait_ms": 0, "active_duration_ms": null, "active_wallclock_time_taken": null, "iterations": 0, "tokens_used": { "cache_creation": null, "cache_read": null, "input": null, "output": null, "total": null, "cost_usd": null } },
    "pr":             { "status": "pending", "model": "<model>", "started_at": null, "completed_at": null, "duration_ms": null, "user_wait_ms": 0, "active_duration_ms": null, "active_wallclock_time_taken": null, "iterations": 0, "tokens_used": { "cache_creation": null, "cache_read": null, "input": null, "output": null, "total": null, "cost_usd": null } }
  },
  "tokens_summary": { "total_cache_creation": 0, "total_cache_read": 0, "total_input": 0, "total_output": 0, "total": 0, "total_cost_usd": 0 },
  "model_transitions": {}
}
```

> Only include the phases from the confirmed `phase_set` — not all phases for every ticket type.

### Incompatible Checkpoint Detection

When loading a pipeline_state_<ticket>.json, check that the expected phases from `classification.phase_set` are present. If phases are missing, report:

```
Incompatible checkpoint: pipeline_state_<ticket>.json is missing phases: <list>. Re-run the pipeline: /client-master:00-sdlc-pipeline --ticket=<ticket>
```

## Required Sections Validation

All artifacts are Markdown files. Validate each artifact by checking for required section headers based on the artifact type:

1. **ph1_problem_spec.md** — Required headers: `## Meta`, `## Problem Statement`, `## Requirements`, `## Acceptance Criteria`, `## Constraints`, `## Non-Goals`, `## Assumptions`, `## Edge Cases`, `## Backward Compatibility`, `## Glossary`
2. **ph2_design_spec.md** — Required headers: `## Meta`, `## Problem Spec Reference`, `## Current Architecture`, `## Architecture`, `## API Contracts`, `## Data Models`, `## Decisions (ADRs)`, `## Implementation Guidelines`, `## Testing Strategy`, `## Security Considerations`
3. **ph3_design_review.md** — Required headers: `## Meta`, `## Summary`, `## Findings`, `## Sign-Off`
4. **ph4_implementation_plan.md** — Required headers: `## Implementation Steps`, `## Pipeline Continuation`, `## Pre-Implementation Baseline`
5. **ph5_6_impl_manifest.md** — Required headers: `## Summary`, `## Baseline Test Counts`, `## Final Test Counts`, `## Files Created`, `## Files Modified`, `## Test Files`, `## Simplification`
6. **ph8_verification_report.md** — Required headers: `## Meta`, `## Summary`, `## Requirement Coverage`, `## Test Results`, `## Recommendations`
7. **ph9_risk_assessment.md** — Required headers: `## Meta`, `## Summary`, `## Failure Modes`, `## Sign-Off`

**Validation rules:**

- If any required header is missing, mark `schema_valid: false` and report the missing sections.
- If all required headers are present, mark `schema_valid: true`.
- On validation failure, do NOT block the save operation — save the artifact and mark `schema_valid: false`.
- On validation success, update `pipeline_state_<ticket>.json` with `schema_valid: true` for that phase.

## Error Handling

| Condition                      | Behavior                                                                                                                                                                          |
| ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Missing artifact file**      | Report: `No artifact found for phase '<phase>' on ticket '<ticket-id>'. Run the phase first or check the ticket ID.`                                                              |
| **Missing required headers**   | Report which headers are missing. Save proceeds; mark `schema_valid: false`.                                                                                                      |
| **Pipeline state corruption**  | Rebuild pipeline_state_<ticket>.json by scanning both artifact directories for existing files. Set status to `completed` for any phase with a valid artifact file, `pending` for the rest. |
| **Ticket directory not found** | For `load`/`status`/`validate`: report that no artifacts exist yet for the ticket. For `save`: create the directory.                                                              |

## Evaluation

| Scenario                     | Input                                        | Expected behavior                                                   |
| ---------------------------- | -------------------------------------------- | ------------------------------------------------------------------- |
| Trigger — positive           | "save checkpoint for requirements TICKET-123"   | Skill activates, saves artifact, validates required sections        |
| Trigger — positive           | "checkpoint status TICKET-456"                  | Skill activates, displays phase table                               |
| Trigger — positive           | "load the architecture artifact for TICKET-789" | Skill activates, reads and reports artifact                         |
| Trigger — positive           | "validate artifacts for TICKET-123"             | Skill activates, validates all found artifacts                      |
| Trigger — negative           | "what is a checkpoint in racing?"            | Skill does NOT activate                                             |
| Edge case — no artifacts     | "status TICKET-999" (no artifacts exist)        | Reports no artifacts found, all phases pending                      |
| Edge case — corrupt state    | pipeline_state_<ticket>.json has invalid JSON         | Rebuilds from artifact scan, warns user                             |
| Edge case — missing sections | Required section headers missing             | Saves artifact, reports missing sections, marks schema_valid: false |
