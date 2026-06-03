# SDLC Pipeline Architecture Design

> **SUPERSEDED:** This design document describes the original 8-phase pipeline model. The implementation has since been updated to a **10-phase model** with `impl-planning` as Phase 4 and `simplify` as Phase 6. The `sub_phase` field was removed, and phase state keys changed (e.g., `risk` not `risk_assessment`, `pr` not `pr_creation`). See `skills/sdlc-pipeline/SKILL.md` for the current canonical pipeline definition.

**Date:** 2026-02-25
**Status:** Superseded (see note above)
**Branch:** `add-sdlc-multi-agent`
**Author:** [Author] + Claude Code

---

## 1. Executive Summary

This design merges the best of two approaches:

- **[Original Author]'s 8-agent pipeline** (the dev repo) — deep specialist prompts, structured JSON contracts, schema validation
- **Claude Master Plugin** (this repo) — skills for methodology, subagents for isolated execution, hooks for safety, single-session context efficiency

The result: **Modular phase skills + checkpoint artifacts + subagents for isolated review**. Three operating modes (auto pipeline, interactive gates, standalone phase) give developers flexibility from full automation to surgical recovery.

### Key Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Phase methodology | Skills (not agents) | Shares context, avoids 8x re-exploration tax |
| Structured contracts | JSON schemas at checkpoints | Ported from [Original Author]'s system for programmatic validation |
| Independent review | Subagents with fresh context | Avoids "grading your own exam" bias |
| Compaction insurance | Checkpoint artifacts on disk | Git-tracked specs + ephemeral execution artifacts |
| Prompt depth | 500+ lines per phase skill | Matches [Original Author]'s agent depth, not shallow 50-line skills |
| Automation | 3 modes (auto/gates/standalone) | Flexibility for greenfield, day-to-day, and recovery workflows |

---

## 2. Architecture Overview

```
+------------------------------------------------------------------------+
|  MAIN ORCHESTRATOR (single Claude Code session)                         |
|                                                                          |
|  Phase Skills (inline, share context):                                   |
|  [sdlc-requirements] -> [sdlc-architecture] -> [sdlc-design-review]    |
|       -> [implementation] -> [sdlc-verify] -> [sdlc-risk]              |
|                                                                          |
|  Checkpoint Skill (compaction insurance):                                |
|  [sdlc-checkpoint] save/load/validate/status                            |
|                                                                          |
|  Existing Skills (reused):                                               |
|  [code-review] [security-scan] [generate-tests] [create-pr]            |
|                                                                          |
|  Orchestrator Skill:                                                     |
|  [sdlc-pipeline] --mode=auto|gates  --ticket=TICKET-ID                  |
+------------------------------------------------------------------------+
           |                    |                    |
  +--------v--------+  +-------v--------+  +--------v--------+
  | code-reviewer   |  | test-engineer  |  | security-auditor|
  | (subagent)      |  | (subagent)     |  | (subagent)      |
  | fresh context   |  | verbose output |  | fresh context   |
  | read-only       |  | bash access    |  | read-only       |
  +-----------------+  +----------------+  +-----------------+
```

### Operating Modes

| Mode | Trigger | Behavior | Use Case |
|---|---|---|---|
| **Auto** | `/sdlc-pipeline --mode=auto --ticket=X` | All phases, checkpoint at each boundary, parallel subagents for review | Greenfield features, 1M context |
| **Gates** | `/sdlc-pipeline --mode=gates --ticket=X` | Pauses after each phase for human approval | Day-to-day development |
| **Standalone** | `/sdlc-requirements --ticket=X` | Single phase, loads previous checkpoint | Recovery, debugging, mid-flight entry |

---

## 3. Component Inventory

### 3.1 Existing Components (reused, no changes)

| Component | Type | Role in Pipeline |
|---|---|---|
| `code-review` skill | Skill | Called during review phase |
| `security-scan` skill | Skill | Called during security phase |
| `generate-tests` skill | Skill | Called during test phase |
| `create-pr` skill | Skill | Called at pipeline end |
| `session-learnings` skill | Skill | Called at session end |
| `code-reviewer` agent | Subagent | Fresh-context code review at step [5] |
| `security-auditor` agent | Subagent | Fresh-context security audit at step [5] |
| `test-engineer` agent | Subagent | Test generation/execution at step [5] |
| `pr-manager` agent | Subagent | PR lifecycle at step [8] |
| `architect` agent | Subagent | Architecture review (on demand) |
| `devops-engineer` agent | Subagent | CI/CD review (on demand) |
| All hooks | Hooks | Continue to fire across entire pipeline |
| All MCP servers | MCP | Available throughout pipeline |

### 3.2 New Components (to build)

| Component | Type | Est. Lines | Source |
|---|---|---|---|
| `sdlc-requirements` | Skill | 500-600 | Ported from [Original Author]'s Agent 1 (Problem Decomposer) |
| `sdlc-architecture` | Skill | 500-600 | Ported from [Original Author]'s Agent 2 (Design Architect) |
| `sdlc-design-review` | Skill | 300-400 | Ported from [Original Author]'s Agent 5a (Design Critic) |
| `sdlc-verify` | Skill | 400-500 | Ported from [Original Author]'s Agent 4 (Verifier) |
| `sdlc-risk` | Skill | 300-400 | Ported from [Original Author]'s Agent 5 (Critic) |
| `sdlc-checkpoint` | Skill | 150-200 | New (compaction insurance + schema validation) |
| `sdlc-pipeline` | Skill | 200-300 | New (orchestrator with mode control) |
| `schemas/*.schema.json` | JSON schemas | ~2000 total | Ported from [Original Author]'s schemas (10 files) |
| `/sdlc` command | Command | 5-10 | Slash command wiring |
| `/requirements` command | Command | 5-10 | Slash command wiring |
| `/architecture` command | Command | 5-10 | Slash command wiring |

### 3.3 Eliminated (from [Original Author]'s system)

| Component | Why |
|---|---|
| Agent 3a (Scaffolder) | Normal Claude Code behavior |
| Agent 3b (Builder) | Normal Claude Code behavior |
| Agent 3c (Fixer) | Normal Claude Code behavior |
| `workflow.py` | Replaced by skill orchestration |
| `validate.py` | Replaced by sdlc-checkpoint schema validation |
| Manual copy-paste workflow | Replaced by shared context + checkpoints |

---

## 4. Skill Specifications

### 4.1 sdlc-requirements

**File:** `.claude/skills/sdlc-requirements/SKILL.md`
**Trigger:** `/requirements --ticket=X` or auto-invoked by pipeline
**Depth:** 500-600 lines

**Methodology (ported from [Original Author]'s Problem Decomposer):**

Prime directive: "Ask 10 questions before writing 1 requirement."

Interrogation categories (40+):
- Scope & Brand: BK/PLK/FHS applicability, platform specifics, device scope
- Offline & Connectivity: offline behavior, network failure, caching needs
- Authentication & Authorization: feature flags, login requirements, RBAC
- Error States: API failures, timeout handling, graceful degradation
- Loading & Async: loading states, fetch/sync behavior, timeouts
- Feature Flag & Rollout: LaunchDarkly integration, rollout strategy, kill switch
- Performance: response time, data size, memory, bandwidth
- Security & Compliance: GDPR, PCI, encryption, audit logging, PII handling
- Data Model: schema changes, migration strategy, backward compatibility
- Observability: metrics, dashboards, alerts, structured logging
- Accessibility: WCAG compliance, screen reader support, keyboard navigation
- i18n: translation requirements, RTL support, locale-specific behavior

Default output: `clarification_questions.json` (unless requirements are crystal clear)
Final output: `problem_spec.json` with REQ-###, AC-### (Given-When-Then), NG-###, ASM-###, EC-###

**Checkpoint:** Saves to `docs/artifacts/<ticket-id>/problem_spec.json` (git-tracked)
**Schema validation:** `schemas/problem_spec.schema.json`

### 4.2 sdlc-architecture

**File:** `.claude/skills/sdlc-architecture/SKILL.md`
**Trigger:** `/architecture --ticket=X` or auto-invoked by pipeline
**Depth:** 500-600 lines

**Methodology (ported from [Original Author]'s Design Architect):**

Prime directive: "Design everything. Code nothing."

Phases:
1. Codebase analysis — read existing patterns, components, conventions before designing
2. Architecture pattern selection (container_presenter, mvvm, mvc, clean_architecture, feature_sliced)
3. Component design with COMP-### identifiers (type, responsibility, dependencies, file paths)
4. Data flow definition
5. API contract design (GraphQL queries/mutations, custom hooks with TypeScript signatures)
6. Data model design (TypeScript interfaces, enums, state shape)
7. ADR generation (ADR-### with context, decision, alternatives, consequences)
8. Implementation guidelines (file structure, naming, patterns to use/avoid, libraries)
9. Testing strategy (unit/integration/E2E targets, coverage target)
10. Security considerations with OWASP mapping

project-specific patterns:
- Brand constants and theming
- LaunchDarkly feature flag integration
- Sanity CMS content patterns
- Capacitor native plugin patterns
- Apollo GraphQL client patterns
- styled-components theming

**Checkpoint:** Saves to `docs/artifacts/<ticket-id>/design_spec.json` (git-tracked)
**Schema validation:** `schemas/design_spec.schema.json`

### 4.3 sdlc-design-review

**File:** `.claude/skills/sdlc-design-review/SKILL.md`
**Trigger:** Auto-invoked by pipeline after architecture, or standalone `/design-review --ticket=X`
**Depth:** 300-400 lines

**Methodology (ported from [Original Author]'s Design Critic):**

Review dimensions:
- Codebase validation: verify referenced components actually exist
- Architectural findings: severity (critical/major/minor), risk, recommendation, effort
- Assumption challenges: challenge each ASM-### with likelihood + impact assessment
- Complexity concerns: detect over-engineering, propose simpler alternatives
- Alternative approaches: evaluate at least 2 alternatives with tradeoffs
- Missing considerations: gaps in design with examples and impact
- Design quality scoring: clarity, completeness, soundness, simplicity, scalability, maintainability (0-100 each)

Gate decision: approve / approve_with_concerns / reject
- approve: continue to implementation
- approve_with_concerns: log concerns, continue
- reject: feed rejection reasons back to sdlc-architecture for revision

**Checkpoint:** Saves to `docs/artifacts/<ticket-id>/design_review.json` (git-tracked)
**Schema validation:** `schemas/design_review.schema.json`

### 4.4 sdlc-verify

**File:** `.claude/skills/sdlc-verify/SKILL.md`
**Trigger:** Auto-invoked after implementation + subagent review, or standalone
**Depth:** 400-500 lines

**Methodology (ported from [Original Author]'s Verifier):**

Verification dimensions:
- Requirement coverage: REQ-### -> AC-### -> test mapping (every AC must have a test)
- Test results: unit/integration/E2E pass rates with failure details
- Quality findings (QF-###): code_smell, duplication, complexity, naming, SOLID_violation, pattern_violation, performance, accessibility, i18n, type_safety
- Security findings (SF-###): OWASP categories, CVSS scores, CWE IDs, PCI/GDPR/PII flags
- Edge case coverage: EC-### tested/not_tested/failed
- Recommendations: priority 1-5, blocking flags

Aggregation: Combines results from parallel subagents (code-reviewer + test-engineer + security-auditor) into a unified verification report.

Score: 0-100 with configurable pass threshold (default: 70)
Status: passed / failed / passed_with_warnings

**Checkpoint:** Saves to `.claude/checkpoints/<ticket-id>/verification_report.json` (ephemeral)
**Schema validation:** `schemas/verification_report.schema.json`

### 4.5 sdlc-risk

**File:** `.claude/skills/sdlc-risk/SKILL.md`
**Trigger:** Auto-invoked after verification, or standalone
**Depth:** 300-400 lines

**Methodology (ported from [Original Author]'s Critic):**

Adversarial mindset: "Your job is to BREAK things."

Analysis dimensions:
- Assumption challenges: challenge each ASM-### with likelihood + impact + mitigation
- Failure modes (FM-###): trigger, consequence, likelihood, severity, detection, prevention, recovery
- Attack scenarios (ATK-###): attacker profile, goal, attack vector, likelihood, impact, mitigation gap
- Blind spots (BS-###): scalability, edge cases, user behavior, third-party deps, data consistency, compliance, accessibility, performance, maintainability, observability
- Stress test scenarios: extreme load, concurrent users, data volume
- Dependency risks: npm packages, APIs, services, infrastructure, human dependencies

Ship recommendation:
- **ship**: no blocking concerns
- **ship_with_monitoring**: acceptable risk with monitoring requirements listed
- **fix_first**: blocking issues that must be resolved (loops back to implementation)
- **redesign**: fundamental architectural issues (loops back to architecture)

**Checkpoint:** Saves to `.claude/checkpoints/<ticket-id>/risk_assessment.json` (ephemeral)
**Schema validation:** `schemas/risk_assessment.schema.json`

### 4.6 sdlc-checkpoint

**File:** `.claude/skills/sdlc-checkpoint/SKILL.md`
**Trigger:** Auto-invoked at phase boundaries, or manual `/checkpoint status TICKET-1234`
**Depth:** 150-200 lines

**Operations:**
- `save <phase> <ticket-id>`: Serialize phase output to appropriate location (git-tracked or ephemeral), validate against schema
- `load <phase> <ticket-id>`: Reload checkpoint artifact into context (for Option C standalone or compaction recovery)
- `status <ticket-id>`: Display which phases have completed checkpoints with timestamps
- `validate <ticket-id>`: Run schema validation against all saved artifacts, report missing required fields

**Storage rules:**
- Spec artifacts (problem_spec, design_spec, design_review) -> `docs/artifacts/<ticket-id>/` (git-tracked)
- Execution artifacts (impl_manifest, verification, risk) -> `.claude/checkpoints/<ticket-id>/` (ephemeral)
- Pipeline state -> `.claude/checkpoints/<ticket-id>/pipeline_state.json`

**Schema validation:** Uses ported JSON schemas to programmatically verify artifact completeness before allowing the pipeline to proceed. If validation fails, the pipeline halts with specific missing-field errors.

### 4.7 sdlc-pipeline

**File:** `.claude/skills/sdlc-pipeline/SKILL.md`
**Trigger:** `/sdlc --mode=auto --ticket=X` or `/sdlc --mode=gates --ticket=X`
**Depth:** 200-300 lines

**Arguments:**
- `--mode=auto|gates` (required)
- `--ticket=TICKET-ID` (required, enforces Jira traceability)
- `--resume` (optional, restart from last checkpoint)
- `--from=<phase>` (optional, start from specific phase)

**Auto mode pipeline:**

```
[1] Invoke sdlc-requirements skill
    -> sdlc-checkpoint save requirements <ticket>
    -> Schema validates problem_spec.json

[2] Invoke sdlc-architecture skill
    -> sdlc-checkpoint save architecture <ticket>
    -> Schema validates design_spec.json

[3] Invoke sdlc-design-review skill
    -> If reject: feed reasons back to [2], re-run architecture
    -> If approve_with_concerns: log, continue
    -> If approve: continue
    -> sdlc-checkpoint save design-review <ticket>

[4] Implementation phase (inline, main agent writes code)
    -> Use existing codebase patterns
    -> Follow design_spec implementation guidelines
    -> sdlc-checkpoint save implementation <ticket>

[5] Parallel subagents (launched concurrently):
    -> code-reviewer subagent (fresh context, read-only)
    -> test-engineer subagent (verbose output, bash)
    -> security-auditor subagent (fresh context, read-only)

[6] Invoke sdlc-verify skill (aggregates subagent results)
    -> sdlc-checkpoint save verification <ticket>

[7] Invoke sdlc-risk skill (adversarial analysis)
    -> If ship: continue
    -> If ship_with_monitoring: log monitoring requirements, continue
    -> If fix_first: loop to [4] with fix requirements
    -> If redesign: loop to [2] with feedback

[8] Invoke create-pr skill
    -> References docs/artifacts/<ticket>/ in PR description
    -> Links Jira ticket (required)
```

**Gates mode:** Same flow but pauses after steps [1], [2], [3], [4], [6], [7] with:
```
Phase complete. Summary: [key outputs]
Approve and continue? (y/n/revise)
```

**Resume logic:**
1. Read `.claude/checkpoints/<ticket>/pipeline_state.json`
2. Identify last completed phase
3. Load checkpoint artifacts for all completed phases
4. Continue from next phase

---

## 5. Checkpoint System

### 5.1 Directory Structure

```
project-root/
|-- docs/
|   |-- artifacts/                       # Git-tracked (spec artifacts)
|   |   |-- TICKET-1234/
|   |   |   |-- problem_spec.json        # Requirements
|   |   |   |-- design_spec.json         # Architecture
|   |   |   |-- design_review.json       # Design review
|   |   |
|   |   |-- TICKET-5678/
|   |       |-- ...
|   |
|   |-- plans/
|       |-- 2026-02-25-sdlc-pipeline-design.md  # This document
|
|-- .claude/
|   |-- checkpoints/                     # Ephemeral (execution artifacts)
|   |   |-- TICKET-1234/
|   |   |   |-- pipeline_state.json      # Current phase, mode, timestamps
|   |   |   |-- impl_manifest.json       # Implementation tracking
|   |   |   |-- verification.json        # Verification results
|   |   |   |-- risk_assessment.json     # Risk analysis
|   |
|   |-- skills/
|   |   |-- sdlc-requirements/SKILL.md
|   |   |-- sdlc-architecture/SKILL.md
|   |   |-- sdlc-design-review/SKILL.md
|   |   |-- sdlc-verify/SKILL.md
|   |   |-- sdlc-risk/SKILL.md
|   |   |-- sdlc-checkpoint/SKILL.md
|   |   |-- sdlc-pipeline/SKILL.md
|   |
|   |-- schemas/                         # JSON schemas for validation
|       |-- problem_spec.schema.json
|       |-- design_spec.schema.json
|       |-- design_review.schema.json
|       |-- implementation_manifest.schema.json
|       |-- verification_report.schema.json
|       |-- risk_assessment.schema.json
|       |-- clarification_questions.schema.json
```

### 5.2 Pipeline State Schema

```json
{
  "ticket_id": "TICKET-1234",
  "feature_name": "parallel-amplitude-cdp-migration",
  "mode": "auto",
  "started_at": "2026-02-25T10:00:00Z",
  "last_updated_at": "2026-02-25T12:30:00Z",
  "phases": {
    "requirements": {
      "status": "completed",
      "completed_at": "2026-02-25T10:15:00Z",
      "artifact_path": "docs/artifacts/TICKET-1234/problem_spec.json",
      "schema_valid": true
    },
    "architecture": {
      "status": "completed",
      "completed_at": "2026-02-25T10:45:00Z",
      "artifact_path": "docs/artifacts/TICKET-1234/design_spec.json",
      "schema_valid": true,
      "iterations": 1
    },
    "design_review": {
      "status": "completed",
      "completed_at": "2026-02-25T11:00:00Z",
      "artifact_path": "docs/artifacts/TICKET-1234/design_review.json",
      "decision": "approve_with_concerns"
    },
    "implementation": {
      "status": "in_progress",
      "started_at": "2026-02-25T11:05:00Z",
      "artifact_path": null
    },
    "review": {
      "status": "pending"
    },
    "verification": {
      "status": "pending"
    },
    "risk_assessment": {
      "status": "pending"
    },
    "pr_creation": {
      "status": "pending"
    }
  }
}
```

### 5.3 Gitignore Additions

Add to `.gitignore`:
```
# SDLC pipeline ephemeral checkpoints
.claude/checkpoints/
```

The `docs/artifacts/` directory is intentionally NOT gitignored — those files are meant to be reviewed in PRs.

---

## 6. Schema Adaptation

[Original Author]'s 10 JSON schemas are ported with minimal changes:

| Schema | Changes from [Original Author]'s Version |
|---|---|
| `problem_spec.schema.json` | Add `ticket_id` field alongside `feature_id` |
| `design_spec.schema.json` | Add project-specific `brands enum (BR1, BR2, BR3, BR4)) |
| `design_review.schema.json` | No changes |
| `implementation_manifest.schema.json` | Add `git_branch` and `commit_sha` fields |
| `verification_report.schema.json` | No changes |
| `risk_assessment.schema.json` | No changes |
| `clarification_questions.schema.json` | No changes |
| `scaffold_manifest.schema.json` | Eliminated (no separate scaffolder) |
| `fix_manifest.schema.json` | Eliminated (fixer is inline Claude behavior) |
| `fix_request.schema.json` | Eliminated (fix requirements embedded in pipeline loop-back) |

Net: 7 schemas ported, 3 eliminated.

---

## 7. Slash Command Wiring

New commands to add:

| Command | File | Invokes |
|---|---|---|
| `/sdlc` | `.claude/commands/sdlc.md` | `sdlc-pipeline` skill |
| `/requirements` | `.claude/commands/requirements.md` | `sdlc-requirements` skill |
| `/architecture` | `.claude/commands/architecture.md` | `sdlc-architecture` skill |
| `/design-review` | `.claude/commands/design-review.md` | `sdlc-design-review` skill |
| `/verify` | `.claude/commands/verify.md` | `sdlc-verify` skill |
| `/risk` | `.claude/commands/risk.md` | `sdlc-risk` skill |
| `/checkpoint` | `.claude/commands/checkpoint.md` | `sdlc-checkpoint` skill |

---

## 8. Risk Mitigation

| Risk | Mitigation |
|---|---|
| Context compaction loses phase data | Checkpoint artifacts on disk survive compaction; resume logic reloads them |
| Single-session bias in review | Subagents (code-reviewer, security-auditor) run in fresh context |
| Skill files too large (500+ lines) | Use `references/` subdirectories for detailed checklists (like existing code-review skill) |
| Schema validation overhead | Validation is lightweight — JSON parse + field presence check, not ajv |
| Pipeline mode complexity | Three modes share the same phase skills; orchestrator is thin (200 lines) |
| Prompt depth regression | Each skill carries deep methodology ported from [Original Author]'s 1500-line agents |
| Team iterability | Each skill is a separate file — independent PRs, no coupling |

---

## 9. What We Gain Over Both Systems

| Capability | [Original Author]'s 8-Agent | Current Plugin | New Hybrid |
|---|---|---|---|
| Context continuity | No (8 cold starts) | Yes | Yes |
| Prompt caching | No (8 sessions) | Yes | Yes |
| Structured contracts | Yes (JSON schemas) | No | Yes |
| Independent review | Yes (fresh agents) | Partial | Yes (subagents) |
| Prompt depth | Yes (1500-line agents) | No (50-100 lines) | Yes (500+ lines) |
| Compaction resilience | Yes (no compaction) | No | Yes (checkpoints) |
| Programmatic validation | Yes (ajv) | No | Yes (schema check) |
| Human review gates | Manual (copy-paste) | No | Optional (gates mode) |
| Full automation | No | No | Yes (auto mode) |
| Recovery/resume | No | No | Yes (checkpoint reload) |
| Token efficiency | ~1M tokens/feature | ~300K | ~300-500K |
| Developer workflow | 8 sessions, 7 pastes | 1 session, manual | 1 session, 3 modes |
| Parallelism | Theoretical | Yes (subagents) | Yes (step 5) |

---

## 10. Implementation Order

Phase 1 — Foundation:
1. Port JSON schemas (7 files)
2. Build sdlc-checkpoint skill
3. Build sdlc-pipeline skill (orchestrator)
4. Add slash commands (7 files)
5. Update .gitignore

Phase 2 — Phase Skills:
6. Build sdlc-requirements skill (port from Problem Decomposer)
7. Build sdlc-architecture skill (port from Design Architect)
8. Build sdlc-design-review skill (port from Design Critic)

Phase 3 — Verification Skills:
9. Build sdlc-verify skill (port from Verifier)
10. Build sdlc-risk skill (port from Critic)

Phase 4 — Integration:
11. Wire pipeline orchestration (auto + gates + resume)
12. Test end-to-end with a real feature
13. Update CLAUDE.md with new skills documentation
14. Update docs/ARCHITECTURE.md

---

## 11. References

- [Original Author]'s agentic workflow: `github.com/your-org/dev-repo` commit `78f258df`
- Anthropic Skills docs: `code.claude.com/docs/en/skills`
- Anthropic Subagents docs: `code.claude.com/docs/en/sub-agents`
- Anthropic Agent Teams docs: `code.claude.com/docs/en/agent-teams`
- Anthropic Multi-Agent Research: `anthropic.com/engineering/multi-agent-research-system`
- Anthropic Best Practices: `code.claude.com/docs/en/best-practices`
