# SDLC Pipeline Implementation Plan

> **SUPERSEDED:** This implementation plan references the original 8-phase pipeline with 7 skills and old `.claude/skills/` paths. The implementation has since been updated to a **10-phase model** with 9 SDLC skills (including `sdlc-impl-planning` and `simplify`), and skills moved to repo-root `skills/`. See `skills/sdlc-pipeline/SKILL.md` for the current canonical pipeline definition.

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a modular SDLC pipeline with 7 phase skills, checkpoint system, schema validation, and 3-mode orchestrator (auto/gates/standalone).

**Architecture:** Individual deep skills (500+ lines) for each SDLC phase, connected by a thin orchestrator skill. Checkpoint artifacts save to disk at each phase boundary for compaction resilience. Subagents (code-reviewer, test-engineer, security-auditor) provide fresh-context independent validation during the review phase.

**Tech Stack:** Claude Code skills (SKILL.md), JSON schemas, slash commands, existing subagents

**Design Doc:** `docs/plans/2026-02-25-sdlc-pipeline-design.md`

---

## Phase 1: Foundation (Schemas + Checkpoint + Commands)

### Task 1: Port JSON Schemas

**Files:**
- Create: `.claude/schemas/problem_spec.schema.json`
- Create: `.claude/schemas/design_spec.schema.json`
- Create: `.claude/schemas/design_review.schema.json`
- Create: `.claude/schemas/implementation_manifest.schema.json`
- Create: `.claude/schemas/verification_report.schema.json`
- Create: `.claude/schemas/risk_assessment.schema.json`
- Create: `.claude/schemas/clarification_questions.schema.json`

**Step 1: Create schemas directory**

```bash
mkdir -p .claude/schemas
```

**Step 2: Port problem_spec.schema.json**

Port from `/Users/author/epam_development/rbi/dev-agentic-review/.github/agentic-workflow/agents/schemas/problem_spec.schema.json` with these adaptations:
- Add `ticket_id` as required field in `meta` (alongside `feature_id`)
- Add `brands` array field with enum `["BK", "PLK", "FHS", "TH"]` in `meta`
- Keep all existing fields: `meta`, `problem_statement`, `requirements`, `constraints`, `non_goals`, `assumptions`, `edge_cases`, `glossary`
- Keep all ID patterns: REQ-###, AC-###, NG-###, ASM-###, EC-###

**Step 3: Port design_spec.schema.json**

Port from [Original Author]'s with adaptations:
- Add `ticket_id` in `meta`
- Add `brands` enum in `meta`
- Keep: `current_architecture`, `architecture`, `api_contracts`, `data_models`, `decisions` (ADR-###), `implementation_guidelines`, `testing_strategy`, `security_considerations`

**Step 4: Port design_review.schema.json**

Port directly — no changes needed. Keep: `summary` (approve/approve_with_concerns/reject), `architectural_review`, `assumption_challenges`, `complexity_concerns`, `alternative_approaches`, `missing_considerations`, `design_quality_assessment`, `sign_off`

**Step 5: Port implementation_manifest.schema.json**

Port with adaptations:
- Add `git_branch` and `commit_sha` fields in `meta`
- Keep: `summary` (files created/modified/deleted/tests), `files` array

**Step 6: Port verification_report.schema.json**

Port directly — no changes needed. Keep: `summary` (status/score/blocking), `requirement_coverage`, `test_results`, `quality_findings` (QF-###), `security_findings` (SF-###), `edge_case_coverage`, `recommendations`

**Step 7: Port risk_assessment.schema.json**

Port directly — no changes needed. Keep: `summary` (risk_level/ship_recommendation), `assumption_challenges`, `failure_modes` (FM-###), `attack_scenarios` (ATK-###), `blind_spots` (BS-###), `stress_test_scenarios`, `dependency_risks`, `recommendations`, `sign_off`

**Step 8: Port clarification_questions.schema.json**

Port directly — no changes. Keep: `clarification_needed`, `questions` array, `notes`

**Step 9: Commit**

```bash
git add .claude/schemas/
git commit -m "feat: add SDLC pipeline JSON schemas ported from dev-repo agentic workflow"
```

---

### Task 2: Build sdlc-checkpoint Skill

**Files:**
- Create: `.claude/skills/sdlc-checkpoint/SKILL.md`

**Step 1: Write the skill file**

Create `.claude/skills/sdlc-checkpoint/SKILL.md` with this structure:

```yaml
---
name: sdlc-checkpoint
description: >
  Saves, loads, validates, and tracks SDLC pipeline checkpoint artifacts.
  Provides compaction insurance by persisting structured phase outputs to disk.
  Triggers on phrases like "save checkpoint", "load checkpoint", "checkpoint status",
  "validate artifacts", or auto-invoked by sdlc-pipeline skill at phase boundaries.
allowed-tools:
  - Read
  - Write
  - Glob
  - Bash
---
```

Content must cover:

1. **Operations:**
   - `save <phase> <ticket-id>` — write phase artifact to correct location, validate against schema
   - `load <phase> <ticket-id>` — read artifact from disk back into context
   - `status <ticket-id>` — show all phase completion status with timestamps
   - `validate <ticket-id>` — run schema validation on all saved artifacts

2. **Storage Rules:**
   - Spec artifacts → `docs/artifacts/<ticket-id>/` (git-tracked)
     - `problem_spec.json`, `design_spec.json`, `design_review.json`
   - Execution artifacts → `.claude/checkpoints/<ticket-id>/` (ephemeral)
     - `pipeline_state.json`, `impl_manifest.json`, `verification.json`, `risk_assessment.json`

3. **Pipeline State Schema:**
   ```json
   {
     "ticket_id": "string",
     "feature_name": "string",
     "mode": "auto|gates",
     "started_at": "ISO8601",
     "last_updated_at": "ISO8601",
     "phases": {
       "<phase_name>": {
         "status": "pending|in_progress|completed|failed",
         "completed_at": "ISO8601|null",
         "artifact_path": "string|null",
         "schema_valid": "boolean"
       }
     }
   }
   ```

4. **Schema Validation:**
   - Read the corresponding `.claude/schemas/<type>.schema.json`
   - Check all `required` fields are present in the artifact
   - Check enum values match allowed values
   - Report specific missing fields if validation fails
   - Halt pipeline on validation failure with actionable error message

5. **Directory Creation:**
   - Auto-create `docs/artifacts/<ticket-id>/` and `.claude/checkpoints/<ticket-id>/` if they don't exist
   - Ensure `.claude/checkpoints/` is in `.gitignore`

**Step 2: Commit**

```bash
git add .claude/skills/sdlc-checkpoint/SKILL.md
git commit -m "feat: add sdlc-checkpoint skill for compaction-resilient artifact management"
```

---

### Task 3: Add Slash Commands

**Files:**
- Create: `.claude/commands/sdlc.md`
- Create: `.claude/commands/requirements.md`
- Create: `.claude/commands/architecture.md`
- Create: `.claude/commands/design-review.md`
- Create: `.claude/commands/verify.md`
- Create: `.claude/commands/risk.md`
- Create: `.claude/commands/checkpoint.md`

**Step 1: Write each command file**

Follow the exact pattern from existing commands (e.g., `review.md`, `pr.md`).

`.claude/commands/sdlc.md`:
```markdown
Run the full SDLC pipeline for a feature using the specified mode.

Follow the `sdlc-pipeline` skill defined in `.claude/skills/sdlc-pipeline/SKILL.md`.

Arguments: $ARGUMENTS (expected: --mode=auto|gates --ticket=TICKET-ID [--resume] [--from=phase])

Steps:
1. Parse mode and ticket ID from arguments.
2. If --resume, load checkpoint state and continue from last completed phase.
3. If --from=phase, load all prior checkpoints and start from specified phase.
4. Execute the pipeline in the specified mode (auto or gates).
5. Save checkpoints at each phase boundary.
6. Use subagents for review phase (code-reviewer, test-engineer, security-auditor).
7. Create PR at completion.
```

`.claude/commands/requirements.md`:
```markdown
Run SDLC requirements analysis for a feature.

Follow the `sdlc-requirements` skill defined in `.claude/skills/sdlc-requirements/SKILL.md`.

Arguments: $ARGUMENTS (expected: --ticket=TICKET-ID [feature description])

Steps:
1. Extract ticket ID from arguments.
2. If a prior checkpoint exists for this ticket, load it for context.
3. Run the full requirements interrogation process.
4. Save problem_spec.json (or clarification_questions.json) to docs/artifacts/<ticket-id>/.
5. Validate output against schema.
```

`.claude/commands/architecture.md`:
```markdown
Run SDLC architecture design for a feature.

Follow the `sdlc-architecture` skill defined in `.claude/skills/sdlc-architecture/SKILL.md`.

Arguments: $ARGUMENTS (expected: --ticket=TICKET-ID)

Steps:
1. Extract ticket ID from arguments.
2. Load problem_spec.json from docs/artifacts/<ticket-id>/ (required input).
3. Analyze the current codebase for existing patterns.
4. Design architecture following the skill's methodology.
5. Save design_spec.json to docs/artifacts/<ticket-id>/.
6. Validate output against schema.
```

`.claude/commands/design-review.md`:
```markdown
Run SDLC design review for a feature.

Follow the `sdlc-design-review` skill defined in `.claude/skills/sdlc-design-review/SKILL.md`.

Arguments: $ARGUMENTS (expected: --ticket=TICKET-ID)

Steps:
1. Extract ticket ID from arguments.
2. Load problem_spec.json and design_spec.json from docs/artifacts/<ticket-id>/.
3. Run the design review methodology.
4. Save design_review.json to docs/artifacts/<ticket-id>/.
5. Report gate decision: approve / approve_with_concerns / reject.
```

`.claude/commands/verify.md`:
```markdown
Run SDLC verification for a feature.

Follow the `sdlc-verify` skill defined in `.claude/skills/sdlc-verify/SKILL.md`.

Arguments: $ARGUMENTS (expected: --ticket=TICKET-ID)

Steps:
1. Extract ticket ID from arguments.
2. Load all prior artifacts (problem_spec, design_spec, implementation manifest).
3. Aggregate results from subagent reviews if available.
4. Run verification checklist.
5. Save verification_report.json to .claude/checkpoints/<ticket-id>/.
6. Report pass/fail with score.
```

`.claude/commands/risk.md`:
```markdown
Run SDLC risk assessment for a feature.

Follow the `sdlc-risk` skill defined in `.claude/skills/sdlc-risk/SKILL.md`.

Arguments: $ARGUMENTS (expected: --ticket=TICKET-ID)

Steps:
1. Extract ticket ID from arguments.
2. Load all prior artifacts.
3. Run adversarial risk analysis.
4. Save risk_assessment.json to .claude/checkpoints/<ticket-id>/.
5. Report ship recommendation: ship / ship_with_monitoring / fix_first / redesign.
```

`.claude/commands/checkpoint.md`:
```markdown
Manage SDLC pipeline checkpoints.

Follow the `sdlc-checkpoint` skill defined in `.claude/skills/sdlc-checkpoint/SKILL.md`.

Arguments: $ARGUMENTS (expected: save|load|status|validate <ticket-id> [phase])

Steps:
1. Parse operation (save/load/status/validate) and ticket ID.
2. Execute the requested checkpoint operation.
3. Report results.
```

**Step 2: Commit**

```bash
git add .claude/commands/sdlc.md .claude/commands/requirements.md .claude/commands/architecture.md .claude/commands/design-review.md .claude/commands/verify.md .claude/commands/risk.md .claude/commands/checkpoint.md
git commit -m "feat: add SDLC pipeline slash commands for all phases"
```

---

### Task 4: Update .gitignore

**Files:**
- Modify: `.gitignore`

**Step 1: Add checkpoint exclusion**

Add these lines to `.gitignore`:

```
# SDLC pipeline ephemeral checkpoints
.claude/checkpoints/
```

**Step 2: Verify docs/artifacts/ is NOT ignored**

Confirm `docs/artifacts/` is not matched by any existing gitignore pattern.

**Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore: add .claude/checkpoints/ to gitignore for ephemeral SDLC artifacts"
```

---

## Phase 2: Phase Skills (Requirements + Architecture + Design Review)

### Task 5: Build sdlc-requirements Skill

**Files:**
- Create: `.claude/skills/sdlc-requirements/SKILL.md`
- Create: `.claude/skills/sdlc-requirements/references/interrogation-questions.md`

**Step 1: Write the SKILL.md**

```yaml
---
name: sdlc-requirements
description: >
  Deep requirements analysis through structured interrogation. Transforms vague
  feature requests into precise, schema-validated problem specifications.
  Triggers on "requirements", "analyze requirements", "what should we build",
  "decompose this feature", or auto-invoked by sdlc-pipeline.
allowed-tools:
  - Read
  - Grep
  - Glob
  - Write
  - Bash
---
```

Content (500-600 lines total) must include:

**Prime Directive:** "Ask 10 questions before writing 1 requirement."

**Process:**
1. Parse ticket ID from arguments
2. Read the feature request / user story
3. Enter interrogation phase — ask questions ONE AT A TIME using categories from `references/interrogation-questions.md`
4. Default output is `clarification_questions.json` unless requirements are crystal clear
5. Once all ambiguity is resolved, produce `problem_spec.json`
6. Save via sdlc-checkpoint

**Output format:** Must conform to `.claude/schemas/problem_spec.schema.json` with:
- `meta`: feature_id, ticket_id, brands, timestamps
- `problem_statement`: summary, user_problem, business_value
- `requirements[]`: REQ-### with priority (P0-P3), type (functional/non_functional/technical), acceptance_criteria[] with Given-When-Then format
- `constraints`: performance, security, compatibility, accessibility, localization
- `non_goals[]`: NG-### with rationale
- `assumptions[]`: ASM-### with risk_level (low/medium/high) and validation_needed
- `edge_cases[]`: EC-### with expected_behavior
- `glossary[]`: domain-specific terms

**Step 2: Write references/interrogation-questions.md**

Port ALL question categories from [Original Author]'s Problem Decomposer. This is the deep domain knowledge file (~300 lines). Categories:

- **Scope & Brand:** BK/PLK/FHS/TH applicability, platform scope (web/iOS/Android), device/OS versions
- **Offline & Connectivity:** offline behavior, network failure, local storage caching, sync strategy
- **Authentication & Authorization:** feature flags, login requirements, RBAC, session handling
- **Error States:** API failures (4xx, 5xx), timeout handling, graceful degradation, retry policies
- **Loading & Async:** loading states, skeleton screens, optimistic updates, timeout thresholds
- **Feature Flag & Rollout:** LaunchDarkly integration, percentage rollout, kill switch, A/B testing
- **Performance:** response time SLAs, data size limits, memory budget, network bandwidth
- **Security & Compliance:** GDPR, PCI-DSS, encryption at rest/transit, audit logging, PII handling (CLIENT_ORG IP library)
- **Data Model:** schema changes, migration strategy, backward compatibility, DynamoDB design
- **Observability:** metrics to emit, dashboard requirements, alert thresholds, structured logging
- **Accessibility:** WCAG 2.1 AA, screen reader support, keyboard navigation, color contrast
- **i18n & Localization:** translation requirements, RTL support, locale-specific formatting
- **Integration Points:** upstream/downstream services, API contracts, SDK dependencies
- **Migration & Rollback:** rollback plan, feature flag revert, data migration, zero-downtime deployment
- **Testing Strategy:** which types of tests needed, test data requirements, environment needs

Each category has 4-8 specific questions, exactly as ported from [Original Author]'s agent.

**Step 3: Commit**

```bash
git add .claude/skills/sdlc-requirements/
git commit -m "feat: add sdlc-requirements skill with deep interrogation methodology"
```

---

### Task 6: Build sdlc-architecture Skill

**Files:**
- Create: `.claude/skills/sdlc-architecture/SKILL.md`
- Create: `.claude/skills/sdlc-architecture/references/architecture-patterns.md`
- Create: `.claude/skills/sdlc-architecture/references/rbi-tech-patterns.md`

**Step 1: Write the SKILL.md**

```yaml
---
name: sdlc-architecture
description: >
  Designs technical architecture for features including component design,
  API contracts, data models, and Architecture Decision Records.
  Triggers on "design architecture", "architect this", "technical design",
  "create design spec", or auto-invoked by sdlc-pipeline.
allowed-tools:
  - Read
  - Grep
  - Glob
  - Write
  - Bash
---
```

Content (500-600 lines) must include:

**Prime Directive:** "Design everything. Code nothing."

**Process:**
1. Load `problem_spec.json` from `docs/artifacts/<ticket-id>/` (required input)
2. Codebase analysis phase:
   - Read existing architecture patterns in the target repo
   - Identify existing components, hooks, services, types
   - Map integration points (GraphQL, REST, Capacitor, MCP)
3. Architecture design:
   - Select architecture pattern (container_presenter, mvvm, clean_architecture, feature_sliced)
   - Design components with COMP-### identifiers
   - Define data flow between components
4. API contract design:
   - GraphQL queries/mutations with type signatures
   - Custom hooks with TypeScript signatures
   - Context APIs if needed
5. Data model design:
   - TypeScript interfaces and types
   - Enums
   - State shape (Redux/Context)
6. ADR generation:
   - ADR-### for each significant decision
   - Context, decision, alternatives considered, consequences
7. Implementation guidelines:
   - File structure with exact paths
   - Naming conventions
   - Patterns to use and patterns to avoid
   - Libraries to use
8. Testing strategy definition
9. Security considerations with OWASP mapping
10. Save via sdlc-checkpoint

**Output format:** Must conform to `.claude/schemas/design_spec.schema.json`

**Step 2: Write references/architecture-patterns.md**

Document the architecture pattern options with when to use each (~150 lines):
- Container/Presenter pattern (default for React components)
- Feature-sliced design (for complex features)
- Clean architecture (for service layers)
- MVVM (for state-heavy features)

**Step 3: Write references/rbi-tech-patterns.md**

project-specific technology patterns (~200 lines):
- Brand constants and theming patterns (BK/PLK/FHS/TH)
- LaunchDarkly feature flag integration patterns
- Sanity CMS content patterns
- Capacitor native plugin patterns
- Apollo GraphQL client patterns (queries, mutations, cache policies)
- styled-components theming
- Redux Toolkit state management
- project logger integration (`@client/logger`)
- DynamoDB table design patterns (single-table vs multi-table)
- Serverless Framework Lambda patterns

**Step 4: Commit**

```bash
git add .claude/skills/sdlc-architecture/
git commit -m "feat: add sdlc-architecture skill with design methodology and project patterns"
```

---

### Task 7: Build sdlc-design-review Skill

**Files:**
- Create: `.claude/skills/sdlc-design-review/SKILL.md`

**Step 1: Write the SKILL.md**

```yaml
---
name: sdlc-design-review
description: >
  Reviews architecture designs before implementation, evaluating quality,
  challenging assumptions, and making a gate decision (approve/reject).
  Triggers on "review design", "design review", "evaluate architecture",
  or auto-invoked by sdlc-pipeline after architecture phase.
allowed-tools:
  - Read
  - Grep
  - Glob
---
```

Content (300-400 lines) must include:

**Process:**
1. Load `problem_spec.json` and `design_spec.json` from `docs/artifacts/<ticket-id>/`
2. Codebase validation:
   - Verify referenced components actually exist in the codebase
   - Check that referenced patterns match actual codebase patterns
   - Identify discrepancies between design assumptions and codebase reality
3. Architectural review:
   - Evaluate each component design for soundness
   - Check for SOLID violations in the architecture
   - Verify data flow completeness
   - Assess API contract design
4. Assumption challenges:
   - For each ASM-### in problem_spec, evaluate likelihood and impact
   - Flag assumptions with high risk that lack mitigation
5. Complexity analysis:
   - Detect over-engineering
   - Propose simpler alternatives where applicable
6. Alternative approaches:
   - Evaluate at least 2 alternatives to the chosen architecture
   - Document tradeoffs
7. Missing considerations:
   - Check for gaps in error handling, observability, security, accessibility
8. Design quality scoring:
   - Clarity (0-100)
   - Completeness (0-100)
   - Soundness (0-100)
   - Simplicity (0-100)
   - Scalability (0-100)
   - Maintainability (0-100)
9. Gate decision:
   - `approve`: design is ready for implementation
   - `approve_with_concerns`: log concerns, proceed with awareness
   - `reject`: specific reasons provided, must revise architecture

**Output format:** Must conform to `.claude/schemas/design_review.schema.json`

**Step 2: Commit**

```bash
git add .claude/skills/sdlc-design-review/SKILL.md
git commit -m "feat: add sdlc-design-review skill with architecture quality gates"
```

---

## Phase 3: Verification Skills

### Task 8: Build sdlc-verify Skill

**Files:**
- Create: `.claude/skills/sdlc-verify/SKILL.md`
- Create: `.claude/skills/sdlc-verify/references/verification-checklist.md`

**Step 1: Write the SKILL.md**

```yaml
---
name: sdlc-verify
description: >
  Verifies implementation against requirements, aggregates review results,
  and produces a scored verification report. Triggers on "verify implementation",
  "run verification", "check implementation", or auto-invoked by sdlc-pipeline.
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
---
```

Content (400-500 lines) must include:

**Process:**
1. Load all prior artifacts (problem_spec, design_spec, implementation manifest)
2. Aggregate subagent results (code-reviewer, test-engineer, security-auditor findings)
3. Requirement coverage matrix:
   - For each REQ-### in problem_spec, trace to implementation files
   - For each AC-### in requirements, trace to test cases
   - Mark: covered / partially_covered / not_covered
4. Test results aggregation:
   - Unit test pass rate
   - Integration test pass rate
   - E2E test pass rate (if applicable)
   - Failure details for each failing test
5. Quality findings (QF-###):
   - Categories: code_smell, duplication, complexity, naming, SOLID_violation, pattern_violation, performance, accessibility, i18n, type_safety
   - Severity: critical, major, minor, info
   - File, line, description, recommendation
6. Security findings (SF-###):
   - OWASP category mapping
   - CVSS score estimation
   - CWE ID if applicable
   - PCI/GDPR/PII flags
7. Edge case coverage:
   - For each EC-### in problem_spec: tested / not_tested / failed
8. Recommendations:
   - Priority 1-5
   - Blocking flag (must-fix before PR)
   - Rationale
9. Overall score: 0-100
   - Pass threshold: 70 (configurable)
   - Status: passed / failed / passed_with_warnings

**Output format:** Must conform to `.claude/schemas/verification_report.schema.json`

**Step 2: Write references/verification-checklist.md**

Port the detailed checklist from [Original Author]'s Verifier agent (~200 lines):
- Requirement-to-test traceability matrix template
- Code quality checklist (SOLID, patterns, naming, complexity)
- Security verification checklist (OWASP Top 10 quick check)
- Performance verification checklist
- Accessibility verification checklist (WCAG 2.1 AA)
- Edge case coverage matrix template

**Step 3: Commit**

```bash
git add .claude/skills/sdlc-verify/
git commit -m "feat: add sdlc-verify skill with requirement coverage and quality verification"
```

---

### Task 9: Build sdlc-risk Skill

**Files:**
- Create: `.claude/skills/sdlc-risk/SKILL.md`
- Create: `.claude/skills/sdlc-risk/references/risk-categories.md`

**Step 1: Write the SKILL.md**

```yaml
---
name: sdlc-risk
description: >
  Adversarial risk assessment that challenges assumptions, identifies failure
  modes and attack scenarios, and makes a ship/no-ship recommendation.
  Triggers on "risk assessment", "adversarial review", "should we ship",
  or auto-invoked by sdlc-pipeline after verification.
allowed-tools:
  - Read
  - Grep
  - Glob
---
```

Content (300-400 lines) must include:

**Prime Directive:** "Your job is to BREAK things. Be the adversary."

**Process:**
1. Load all prior artifacts
2. Assumption challenges:
   - For each ASM-### from problem_spec, evaluate:
   - Likelihood of assumption being wrong (low/medium/high)
   - Impact if wrong (low/medium/high/critical)
   - Mitigation strategy (or flag as unmitigated)
3. Failure modes (FM-###):
   - Systematic identification: what can go wrong?
   - Trigger, consequence, likelihood, severity
   - Detection method (how would we know?)
   - Prevention and recovery strategies
4. Attack scenarios (ATK-###):
   - Attacker profiles: external unauthenticated, authenticated user, insider
   - Goal, attack vector, likelihood, impact
   - Mitigation gap analysis
5. Blind spots (BS-###):
   - Categories: scalability, edge cases, user behavior, third-party dependencies, data consistency, compliance, accessibility, performance, maintainability, observability
   - What hasn't been considered?
6. Stress test scenarios:
   - 10x load, concurrent users, data volume extremes
7. Dependency risks:
   - npm packages, external APIs, internal services, infrastructure, human dependencies
8. Ship recommendation:
   - `ship`: no blocking concerns
   - `ship_with_monitoring`: list specific monitoring requirements
   - `fix_first`: list blocking issues (loops to implementation)
   - `redesign`: fundamental issues (loops to architecture)

**Output format:** Must conform to `.claude/schemas/risk_assessment.schema.json`

**Step 2: Write references/risk-categories.md**

Comprehensive risk category reference (~150 lines):
- Failure mode taxonomy (network, data, state, concurrency, dependency)
- Attack vector taxonomy (injection, auth bypass, data exposure, config)
- Blind spot checklist by domain
- project-specific risks (multi-brand, multi-region, CDN, payment processing)

**Step 3: Commit**

```bash
git add .claude/skills/sdlc-risk/
git commit -m "feat: add sdlc-risk skill with adversarial risk assessment methodology"
```

---

## Phase 4: Orchestrator + Integration

### Task 10: Build sdlc-pipeline Skill (Orchestrator)

**Files:**
- Create: `.claude/skills/sdlc-pipeline/SKILL.md`

**Step 1: Write the SKILL.md**

```yaml
---
name: sdlc-pipeline
description: >
  Orchestrates the full SDLC pipeline through all phases with checkpoint
  management and mode control. Supports auto (full automation), gates
  (interactive approval), and resume (restart from checkpoint).
  Triggers on "run sdlc pipeline", "start pipeline", "/sdlc",
  or "full feature workflow".
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
  - Bash
---
```

Content (200-300 lines) must include:

**Arguments:**
- `--mode=auto|gates` (required)
- `--ticket=TICKET-ID` (required)
- `--resume` (optional — restart from last checkpoint)
- `--from=<phase>` (optional — start from specific phase)

**Auto Mode Pipeline:**

```
[1] REQUIREMENTS PHASE
    - Invoke sdlc-requirements skill
    - Save checkpoint: docs/artifacts/<ticket>/problem_spec.json
    - Validate against schema
    - If clarification needed: present questions, gather answers, re-run

[2] ARCHITECTURE PHASE
    - Invoke sdlc-architecture skill
    - Input: problem_spec.json
    - Save checkpoint: docs/artifacts/<ticket>/design_spec.json
    - Validate against schema

[3] DESIGN REVIEW PHASE
    - Invoke sdlc-design-review skill
    - Input: problem_spec.json + design_spec.json
    - Save checkpoint: docs/artifacts/<ticket>/design_review.json
    - GATE: If reject -> feed reasons to [2], re-run architecture
    - GATE: If approve_with_concerns -> log concerns, continue
    - GATE: If approve -> continue

[4] IMPLEMENTATION PHASE
    - Implementation is inline (main agent writes code)
    - Follow design_spec implementation guidelines
    - Write tests following generate-tests skill patterns
    - Save checkpoint: .claude/checkpoints/<ticket>/impl_manifest.json

[5] REVIEW PHASE (parallel subagents)
    - Launch in parallel:
      a) code-reviewer subagent (fresh context, read-only)
      b) test-engineer subagent (run tests, verbose output)
      c) security-auditor subagent (fresh context, read-only)
    - Collect results from all three

[6] VERIFICATION PHASE
    - Invoke sdlc-verify skill
    - Aggregate subagent results
    - Save checkpoint: .claude/checkpoints/<ticket>/verification.json
    - If score < 70: flag issues

[7] RISK ASSESSMENT PHASE
    - Invoke sdlc-risk skill
    - Input: all prior artifacts
    - Save checkpoint: .claude/checkpoints/<ticket>/risk_assessment.json
    - GATE: If fix_first -> loop to [4] with fix requirements
    - GATE: If redesign -> loop to [2] with feedback
    - GATE: If ship_with_monitoring -> log monitoring requirements
    - GATE: If ship -> continue

[8] PR CREATION PHASE
    - Invoke create-pr skill
    - Include references to docs/artifacts/<ticket>/ in PR description
    - Link Jira ticket (required)
```

**Gates Mode:**
Same as auto but pause after steps [1], [2], [3], [4], [6], [7] with:
```
Phase [N] complete.
Summary: [key outputs from this phase]
Artifacts saved to: [paths]

Approve and continue? (y/n/revise)
- y: proceed to next phase
- n: stop pipeline, save state
- revise: provide feedback, re-run this phase
```

**Resume Logic:**
1. Read `.claude/checkpoints/<ticket>/pipeline_state.json`
2. Find last completed phase
3. Load all checkpoint artifacts for completed phases into context
4. Continue from next pending phase

**Error Handling:**
- Schema validation failure: halt with specific missing-field errors
- Subagent failure: report which subagent failed, continue with partial results
- Compaction detected: reload checkpoint artifacts from disk, continue

**Step 2: Commit**

```bash
git add .claude/skills/sdlc-pipeline/SKILL.md
git commit -m "feat: add sdlc-pipeline orchestrator skill with auto/gates/resume modes"
```

---

### Task 11: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Add SDLC pipeline section**

Add after the existing "Skills & Agents Available" section:

```markdown
### SDLC Pipeline

Full-lifecycle feature development pipeline with three operating modes:

**Slash Commands:**
- `/sdlc --mode=auto --ticket=X` — full automated pipeline
- `/sdlc --mode=gates --ticket=X` — interactive approval at each phase
- `/requirements --ticket=X` — standalone requirements analysis
- `/architecture --ticket=X` — standalone architecture design
- `/design-review --ticket=X` — standalone design review
- `/verify --ticket=X` — standalone verification
- `/risk --ticket=X` — standalone risk assessment
- `/checkpoint status X` — check pipeline progress

**Pipeline Phases:**
1. Requirements (sdlc-requirements skill) → `docs/artifacts/<ticket>/problem_spec.json`
2. Architecture (sdlc-architecture skill) → `docs/artifacts/<ticket>/design_spec.json`
3. Design Review (sdlc-design-review skill) → `docs/artifacts/<ticket>/design_review.json`
4. Implementation (inline)
5. Review (parallel subagents: code-reviewer + test-engineer + security-auditor)
6. Verification (sdlc-verify skill) → `.claude/checkpoints/<ticket>/verification.json`
7. Risk Assessment (sdlc-risk skill) → `.claude/checkpoints/<ticket>/risk_assessment.json`
8. PR Creation (create-pr skill)

**Checkpoint System:**
- Spec artifacts are git-tracked in `docs/artifacts/` (included in PRs)
- Execution artifacts are ephemeral in `.claude/checkpoints/` (gitignored)
- All artifacts are schema-validated against `.claude/schemas/`
- Resume from any checkpoint: `/sdlc --mode=auto --ticket=X --resume`
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add SDLC pipeline documentation to CLAUDE.md"
```

---

### Task 12: Update docs/ARCHITECTURE.md

**Files:**
- Modify: `docs/ARCHITECTURE.md`

**Step 1: Read the existing file**

Read `docs/ARCHITECTURE.md` to understand the current structure.

**Step 2: Add SDLC pipeline section**

Add a new section documenting the pipeline architecture, component relationships, and data flow. Reference the design doc at `docs/plans/2026-02-25-sdlc-pipeline-design.md` for full details.

**Step 3: Commit**

```bash
git add docs/ARCHITECTURE.md
git commit -m "docs: add SDLC pipeline architecture to ARCHITECTURE.md"
```

---

### Task 13: End-to-End Smoke Test

**No files created — validation only.**

**Step 1: Verify all files exist**

```bash
ls -la .claude/schemas/*.schema.json
ls -la .claude/skills/sdlc-*/SKILL.md
ls -la .claude/commands/sdlc.md .claude/commands/requirements.md .claude/commands/architecture.md .claude/commands/design-review.md .claude/commands/verify.md .claude/commands/risk.md .claude/commands/checkpoint.md
```

Expected: 7 schemas, 7 skills (including checkpoint and pipeline), 7 commands.

**Step 2: Verify skill descriptions load**

Open a new Claude Code session in the project and run:
```
/requirements --ticket=TEST-001 (describe a simple feature)
```

Verify:
- Skill loads and begins interrogation
- Questions are asked one at a time
- Output is saved to `docs/artifacts/TEST-001/problem_spec.json`

**Step 3: Verify checkpoint system**

```
/checkpoint status TEST-001
```

Verify it shows requirements phase as completed.

**Step 4: Verify standalone mode (Option C)**

```
/architecture --ticket=TEST-001
```

Verify it loads `problem_spec.json` from disk and proceeds with architecture design.

**Step 5: Clean up test artifacts**

```bash
trash docs/artifacts/TEST-001
trash .claude/checkpoints/TEST-001
```

**Step 6: Final commit**

```bash
git add -A
git commit -m "feat: complete SDLC pipeline v1.0 — skills, schemas, commands, checkpoint system"
```

---

## Summary: File Creation Inventory

| # | Path | Type | Task |
|---|---|---|---|
| 1 | `.claude/schemas/problem_spec.schema.json` | Schema | Task 1 |
| 2 | `.claude/schemas/design_spec.schema.json` | Schema | Task 1 |
| 3 | `.claude/schemas/design_review.schema.json` | Schema | Task 1 |
| 4 | `.claude/schemas/implementation_manifest.schema.json` | Schema | Task 1 |
| 5 | `.claude/schemas/verification_report.schema.json` | Schema | Task 1 |
| 6 | `.claude/schemas/risk_assessment.schema.json` | Schema | Task 1 |
| 7 | `.claude/schemas/clarification_questions.schema.json` | Schema | Task 1 |
| 8 | `.claude/skills/sdlc-checkpoint/SKILL.md` | Skill | Task 2 |
| 9 | `.claude/commands/sdlc.md` | Command | Task 3 |
| 10 | `.claude/commands/requirements.md` | Command | Task 3 |
| 11 | `.claude/commands/architecture.md` | Command | Task 3 |
| 12 | `.claude/commands/design-review.md` | Command | Task 3 |
| 13 | `.claude/commands/verify.md` | Command | Task 3 |
| 14 | `.claude/commands/risk.md` | Command | Task 3 |
| 15 | `.claude/commands/checkpoint.md` | Command | Task 3 |
| 16 | `.gitignore` (modify) | Config | Task 4 |
| 17 | `.claude/skills/sdlc-requirements/SKILL.md` | Skill | Task 5 |
| 18 | `.claude/skills/sdlc-requirements/references/interrogation-questions.md` | Reference | Task 5 |
| 19 | `.claude/skills/sdlc-architecture/SKILL.md` | Skill | Task 6 |
| 20 | `.claude/skills/sdlc-architecture/references/architecture-patterns.md` | Reference | Task 6 |
| 21 | `.claude/skills/sdlc-architecture/references/rbi-tech-patterns.md` | Reference | Task 6 |
| 22 | `.claude/skills/sdlc-design-review/SKILL.md` | Skill | Task 7 |
| 23 | `.claude/skills/sdlc-verify/SKILL.md` | Skill | Task 8 |
| 24 | `.claude/skills/sdlc-verify/references/verification-checklist.md` | Reference | Task 8 |
| 25 | `.claude/skills/sdlc-risk/SKILL.md` | Skill | Task 9 |
| 26 | `.claude/skills/sdlc-risk/references/risk-categories.md` | Reference | Task 9 |
| 27 | `.claude/skills/sdlc-pipeline/SKILL.md` | Skill | Task 10 |
| 28 | `CLAUDE.md` (modify) | Docs | Task 11 |
| 29 | `docs/ARCHITECTURE.md` (modify) | Docs | Task 12 |

**Total: 27 new files + 2 modified files = 29 file operations across 13 tasks**
