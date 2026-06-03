# Regression classification rules

Applied autonomously in Step 6. Mark a test case `regression: true` if **any**
rule fires. Record the rule id in `regression_reason` so the classification is
auditable later.

| Rule | Fires when | Why |
|------|-----------|-----|
| **R1: Existing-surface modification** | The AC modifies an existing endpoint, function, page, or component listed in `artifact-digest.md ## Codebase Scan` (rather than introducing a new isolated module). | A change to an in-use surface needs guard rails so the next release does not regress it. |
| **R2: Critical-path / must-pass AC** | The AC is tagged `critical`, `must-pass`, `P0`, or appears in the story's "Definition of Done" / "Release blocker" subsection of ph1. | Failure on this AC blocks release — automation prevents silent regressions. |
| **R3: Backward-compat invariant** | ph1 has a `## Backward Compatibility` section listing invariants that must hold (e.g. "old payload shape still accepted"). The test asserts one of those invariants. | Backward-compat invariants tend to silently break — automated coverage is the only durable safeguard. |
| **R4: Cross-service contract** | Test type is `integration` and ACs touch ≥2 services from `services-detailed/` (e.g. orders + loyalty). | Inter-service contracts are exactly where regressions hurt most and surface latest. |
| **R5: Security-relevant** | The AC implements an auth, authz, PII, or rate-limit behaviour from `ph2_design_spec.md ## Security Considerations`. | Regressions here become incidents. |

## Tests excluded from regression (even if a rule fires)

- `type: accessibility` cases that need a human review pass — keep manual.
- Exploratory / UAT-only cases (rare from this skill, but possible if ph1
  flags them).
- Tests that require live third-party sandboxes we do not have stable
  fixtures for (callouts, third-party analytics).

When excluding, set `regression: false` and `regression_reason: "excluded:
<reason>"` so the artifact is auditable.

## Tie-breakers

- If R1 and R2 both fire, prefer the more specific (R2).
- If only R3 fires and the test is purely additive (new field, new endpoint),
  treat as regression: false — there is nothing to regress yet.
