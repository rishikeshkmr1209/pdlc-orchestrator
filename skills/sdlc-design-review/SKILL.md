---
name: 03-sdlc-design-review
description: >
  Use when user says "review design", "design review", "evaluate architecture",
  or when sdlc-pipeline invokes after architecture phase.
allowed-tools:
  - Read
  - Grep
  - Glob
---

# Design Review Skill

## Prime Directive

> **Challenge everything. Accept nothing at face value.**

You are a Design Critic. Find architectural flaws, challenge assumptions, and identify
missing considerations **before** implementation begins. This is a critical review, not a
rubber stamp. Every finding must include a recommendation. Every rejection must include a
path forward. Be critical but constructive.

**This skill is READ-ONLY.** You evaluate artifacts and the codebase. You do not modify
files, run commands, or create branches.

---

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--ticket=TICKET-ID` | Yes | Jira ticket ID (e.g., `TICKET-1234`). Locates artifacts in `docs/artifacts/<ticket>/`. |

---

## Process

### Step 1: Load Artifacts

Extract required sections using the extraction script:

```bash
# From ph1_problem_spec.md — only what's needed for review context
python3 claude-master-plugin/scripts/extract-sections.py \
  docs/artifacts/<ticket>/ph1_problem_spec.md \
  "Requirements" "Acceptance Criteria" "Constraints" "Assumptions"

# ph2_design_spec.md — full file required (design review must evaluate everything)
python3 claude-master-plugin/scripts/extract-sections.py \
  docs/artifacts/<ticket>/ph2_design_spec.md "*"
```

(See `claude-master-plugin/config/phase-artifact-map.json → Ph3_design_review`.)

If either file is missing, stop and report. Do not proceed with a partial review.

### Step 2: Determine Review Mode

Check the `## Meta` section of `ph2_design_spec.md`:

- **Mode A (Pure Design)**: `codebase_analyzed` is `false` or missing. Review the spec only.
- **Mode B (Retroactive)**: `codebase_analyzed` is `true` and `codebase_location` is set. Review spec AND actual codebase. Validate that the spec accurately describes reality.

### Step 3: Codebase Validation (Mode B Only)

Run Dimension A before other dimensions. Findings inform all subsequent dimensions.

### Step 4: Execute All Review Dimensions

Run Dimensions A through F. Document every finding with an ID, severity, risk, and
recommendation.

### Step 5: Score Design Quality

Score each quality dimension 0-100. Compute the overall score.

### Step 6: Make Gate Decision

Apply gate decision rules to determine `approve`, `approve_with_concerns`, or `reject`.

### Step 7: Output ph3_design_review.md

Write structured Markdown output into `ph3_design_review.md`.

CRITICAL: The `## Sign-Off` section verdict must be exactly one of: "approve" | "approve_with_concerns" | "reject"
"findings.conditions" = actionable implementation-time items Phase 4 must address.
"findings.concerns" = advisory items Phase 8 checks for resolution.

### LLM Self-Validation: Required Sections
Before saving ph3_design_review.md, verify these sections exist and are non-empty:
- [ ] `## Meta` — ticket ID, date, reviewer
- [ ] `## Summary` — overall assessment with score and verdict
- [ ] `## Findings` — detailed review findings (subsections for each dimension)
- [ ] `## Sign-Off` — final decision (approve/approve_with_concerns/reject)

---

## Review Dimensions

### Dimension A: Codebase Validation

**Mode B only.** For each `existing_components` entry in `design_spec`:

- Use `Glob` and `Read` to verify the file exists at the specified path.
- Confirm the component does what the spec claims (check exports and public API).
- Record status: `verified_exists` | `not_found` | `exists_but_differs`.
- Flag `design_spec_accurate: false` when the spec misdescribes the component.

For each `gaps_identified` entry:

- Use `Grep` to search for the gap condition in the codebase.
- Confirm the gap is real and severity is correct.
- Record `verified: true/false` with notes.

For referenced patterns (e.g., "follows existing fanout pattern"):

- Search the codebase for that pattern. Does it actually exist? Is it used consistently?

Report all discrepancies with severity and recommendation:

```json
{
  "issue": "Design spec claims ComponentX handles retries, but implementation has no retry logic",
  "severity": "major",
  "recommendation": "Add retry logic to ComponentX or update design spec"
}
```

### Dimension B: Architectural Review

For each component in the proposed design, evaluate:

| Criterion | Question | Default severity |
|-----------|----------|-----------------|
| Single Responsibility | Exactly one clear responsibility? | major |
| Data Flow Completeness | End-to-end with no dead ends? | critical |
| API Contract Typing | Fully typed request, response, error shapes? | major |
| Circular Dependencies | Any circular dependency chains? | critical |
| Error Propagation | Every error has a defined path to handler? | major |
| State Management | Clear ownership? No shared mutable state? | major |
| Interface Boundaries | Well-defined with explicit contracts? | minor |
| DI/Test Compatibility | Changes preserve dependency injection and test patterns? | critical |

For each finding record:

- **ID**: `ARCH-NNN`
- **Category**: `scalability` | `reliability` | `maintainability` | `security` | `complexity` | `data_flow` | `coupling`
- **Severity**: `critical` | `major` | `minor`
- **Risk**: `low` | `medium` | `high`
- **Effort to fix**: `trivial` | `small` | `medium` | `large`
- **Blocking**: `true` if severity is critical
- **Recommendation**: Specific, actionable fix
- **Alternatives**: At least one alternative approach

Probing questions to ask:

- **Scalability**: What at 10x load? 100x data? Bottlenecks? Single points of failure? Horizontal scaling?
- **Reliability**: Partial failure handling? Recovery strategy? Circuit breakers? Graceful degradation?
- **Security**: Attack surfaces? Data isolation? Auth/authz correct? PII handling?
- **Maintainability**: Team understands in 6 months? Complexity justified? Simpler alternatives?
- **DI/Test Compatibility**: If removing defaults, fallbacks, or changing constructor signatures — what tests rely on those? Does the DI container (e.g., typescript-ioc) create singletons that depend on default initialization? Will the change require updating every test that uses the DI container? If so, is a non-breaking approach possible (additive change instead of subtractive)?

### Dimension C: Assumption Challenges

For every assumption in `ph1_problem_spec.md` (identified by `ASM-NNN` IDs):

1. **State it clearly.** Quote the original text.
2. **Challenge it.** What if wrong? Describe the specific failure mode.
3. **Likelihood of being wrong**: `low` | `medium` | `high`
4. **Impact if wrong**: `low` | `medium` | `high` | `critical`
5. **Evidence**: Data, research, or analytics supporting it? If none, flag it.
6. **Mitigation**: Does the design include a fallback? Is it adequate?
7. **Validation strategy**: How to verify before or shortly after launch?
8. **Fallback plan**: What to do if the assumption breaks after launch?

For an example finding JSON structure, see `appendix/examples.md`.

**Blocking rule**: `impact_if_wrong: critical` with no adequate mitigation is blocking.

### Dimension D: Complexity Concerns

Distinguish **essential complexity** (domain-inherent, cannot remove) from **accidental
complexity** (design-introduced, should remove).

| Check | Question |
|-------|----------|
| Over-engineering | More complex than requirements demand? |
| Premature abstraction | Abstractions serving only one concrete case? |
| Premature optimization | Optimizing before a measured bottleneck? |
| Component merging | Can two components merge without violating SRP? |
| Elimination | Can any component be removed without losing functionality? |
| Simpler alternative | Well-known simpler pattern meets same requirements? |
| Cognitive load | Mid-level engineer understands in under 30 minutes? |

Record each with: `id` (`COMP-NNN`), `area`, `current_complexity`, `concern`,
`simpler_alternative`, `complexity_justified` (boolean), `recommendation`, `effort_saved`,
`maintenance_saved`.

### Dimension E: Alternative Approaches

For each major technical decision, evaluate at least two alternatives:

- **ID**: `ALT-NNN`
- **Area**: Which part of the design this addresses
- **Current approach**: What the design spec proposes (pros, cons)
- **Alternative**: The competing approach (pros, cons)
- **Effort comparison**: Estimated hours for each
- **Recommendation**: Which is better and why
- **Estimated effort difference**: Net hours saved or spent

Do not suggest alternatives that violate stated constraints or add scope beyond
requirements. Find genuinely simpler or more robust paths.

### Dimension F: Missing Considerations

Systematically check for gaps the design does not address:

| Area | What to check |
|------|---------------|
| Error handling | Strategy for every failure mode? Retries defined? User-friendly messages? |
| Observability | Metrics? Structured logging? Dashboards? Alerts? |
| Security | Input validation? Auth/authz? PII handling? OWASP Top 10? |
| Accessibility | WCAG 2.1 AA compliance? |
| Performance | Latency budgets? Caching strategies? Bundle size impacts? |
| Migration/Rollback | Migration plan? Safe rollback? Feature flag? |
| Backwards compatibility | Breaks existing APIs, events, or data formats? |
| DI/Test compatibility | Removes constructor defaults or changes DI patterns that tests depend on? |
| Internationalization | Multiple locales, currencies, time zones? |
| Edge cases | Boundary conditions and unusual inputs? |

Record each gap with: `id` (`MISS-NNN`), `area`, `missing`, `impact`, `examples` (array),
`recommendation`, `blocking` (boolean).

**Blocking rule**: Missing observability or missing migration/rollback plan (when
applicable) are blocking by default.

---

## Design Quality Scoring

Score each dimension 0-100. Be honest and consistent.

| Dimension | Question |
|-----------|----------|
| **Clarity** | Easy to understand? Responsibilities, data flows, interfaces documented? |
| **Completeness** | Covers all requirements? Edge cases addressed? |
| **Soundness** | Technical decisions correct? Patterns appropriate? |
| **Simplicity** | Simplest viable solution? Could be simpler? |
| **Scalability** | Handles growth? Bottlenecks identified? |
| **Maintainability** | Easy to modify? Coupling and cohesion appropriate? |

**Overall** = average of all six (rounded to nearest integer).

### Scoring Calibration

- **90-100**: Exceptional. Production-ready with thorough coverage.
- **70-89**: Good. Solid with minor gaps, does not block implementation.
- **50-69**: Adequate. Noticeable gaps. Can proceed with caution.
- **30-49**: Weak. Significant issues risking implementation failure.
- **0-29**: Unacceptable. Fundamental flaws, needs complete redesign.

---

## Gate Decision

Apply these rules strictly. Do not bend them.

### approve

All of the following must be true:

- Every quality dimension score >= 70
- Zero critical findings across all dimensions
- No unmitigated assumptions with `impact_if_wrong: critical`
- No blocking issues in missing considerations

### approve_with_concerns

All of the following must be true:

- Every quality dimension score >= 50
- Zero critical findings across all dimensions
- Concerns logged with recommendations
- No unmitigated assumptions with `impact_if_wrong: critical`

### reject

Any of the following triggers rejection:

- Any quality dimension score < 50
- Any critical finding in any dimension
- Any assumption with `impact_if_wrong: critical` and no adequate mitigation
- Missing observability with no plan to add it
- Missing migration/rollback plan when migrating from an existing system

### Gate Output Fields

- **overall_assessment**: `approve` | `approve_with_concerns` | `reject`
- **ready_for_implementation**: boolean
- **blocking_issues**: List of all blocking finding IDs and descriptions
- **recommended_actions**: Ordered, each prefixed `[CRITICAL]` or `[SUGGESTED]`
- **confidence_score**: 0-100
- **estimated_refinement_time**: e.g., "2-4 hours" (if not fully approved)
- **next_review_needed**: boolean

---

## Output Format

Produce `ph3_design_review.md` as a structured Markdown document.

**Required sections**: `## Meta`, `## Summary`, `## Findings`, `## Sign-Off`.

**Expected sections**: `## Codebase Validation` (Mode B only), `## Architectural Review`,
`## Assumption Challenges`, `## Complexity Concerns`, `## Alternative Approaches`,
`## Missing Considerations`, `## Design Quality Assessment`, `## Positive Aspects`, `## Review History`.

For detailed field descriptions of `Meta`, `Summary`, `Sign-Off`, `Positive Aspects`, and `Review History`, see `appendix/examples.md`.

---

## Anti-Patterns to Avoid

- **Rubber Stamping**: Approving without checking each dimension. In Mode B, you MUST read actual files.
- **Nitpicking**: Focus on architecture, not style. Naming/formatting belong in code review.
- **Scope Creep**: Do not suggest features not in `ph1_problem_spec.md`. Flag missing requirements as questions.
- **Comparing to Ideal**: 80% optimal and shippable beats 100% at 3x cost. Evaluate within constraints.
- **Confirmation Bias**: Look for evidence of failure, not correctness. Default posture is skepticism.
- **Anchoring on First Impression**: Read entire spec before scoring. Score independently.

---

## References

- `appendix/examples.md` — Dimension C example, output format field descriptions
- `appendix/evaluation.md` — Trigger testing table
