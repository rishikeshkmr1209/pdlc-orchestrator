# Risk Assessment Skill — Examples & Output Templates

This file contains Markdown output examples for the sdlc-risk skill steps.
Read this file only if you need format guidance for producing `ph9_risk_assessment.md`.

---

## Step 3: Failure Mode Structure

```markdown
### FM-001

- **Mode:** Description of what failure looks like
- **Trigger:** What causes this failure
- **Consequence:** Impact on user and business
- **Likelihood:** rare | unlikely | possible | likely | certain
- **Severity:** negligible | minor | moderate | major | catastrophic
- **Detection:** How would we know this happened
- **Prevention:** Strategy to prevent this failure
- **Recovery:** Plan to recover when it happens
- **Related Component:** COMP-### from design_spec
```

## Step 4: Attack Scenario Structure

```markdown
### ATK-001

- **Attacker Profile:** external_unauthenticated | authenticated_user | insider_threat
- **Goal:** What the attacker wants to achieve
- **Attack Vector:** How they attempt it
- **Steps:**
  1. Step 1
  2. Step 2
  3. Step 3
- **Likelihood:** rare | unlikely | possible | likely
- **Impact:** low | medium | high | critical
- **Current Mitigation:** What the design already addresses
- **Mitigation Gap:** What is missing or insufficient
- **Recommended Mitigation:** Specific fix or hardening measure
```

## Step 5: Blind Spot Structure

```markdown
### BS-001

- **Category:** scalability
- **Description:** What was overlooked
- **Example:** Concrete scenario demonstrating the blind spot
- **Questions to Answer:**
  1. Question 1
  2. Question 2
- **Impact:** What happens if this is not addressed
- **Recommendation:** Specific action to take
```

## Step 6: Stress Test Scenario Structure

```markdown
### Stress Test: Description of stress scenario

- **Expected Behavior:** What should happen (graceful degradation, etc.)
- **Actual Risk:** handled | degraded | unknown | will_fail
- **Recommendation:** Action to validate or improve resilience
```

## Step 7: Dependency Risk Structure

```markdown
### Dependency: Name of the dependency

- **Type:** npm_package | external_api | internal_service | infrastructure | human
- **Risk:** What could go wrong with this dependency
- **Likelihood:** low | medium | high
- **Mitigation:** How to reduce or handle this risk
```

## Output Format: ph9_risk_assessment.md

```markdown
## Meta

- **Feature ID:** FEAT-XXXX
- **Created At:** ISO-8601 timestamp
- **Agent Version:** 2.0
- **Artifacts Reviewed:**
  - ph1_problem_spec.md
  - ph2_design_spec.md
  - ph8_verification_report.md
  - list of implementation files reviewed

## Summary

- **Overall Risk Level:** low | medium | high | critical
- **Confidence Score:** 0-100
- **Ship Recommendation:** ship | ship_with_monitoring | fix_first | redesign
- **Key Concerns:**
  1. Top concern 1
  2. Top concern 2
  3. Top concern 3 (max 5)

## Assumption Challenges

(list here)

## Failure Modes

| ID | Mode | Severity | Probability | Mitigation |
|----|------|----------|-------------|------------|
| FM-001 | ... | ... | ... | ... |

## Attack Scenarios

(list here)

## Blind Spots

(list here)

## Stress Test Scenarios

(list here)

## Dependency Risks

(list here)

## Recommendations

(list here)

## Sign-Off

- **Ready for Production:** yes
- **Conditions:**
  - Conditions that must be met before production
- **Monitoring Required:**
  - Metrics and dashboards to watch post-launch
- **Rollback Triggers:**
  - Conditions that should trigger immediate rollback
```

## Step 9: Recommendation Structure

```markdown
### Recommendation 1

- **Priority:** 1
- **Category:** security | reliability | performance | compliance | observability | testing
- **Action:** Specific, actionable recommendation
- **Rationale:** Reference to finding (FM-001, ATK-002, BS-003, etc.)
- **Effort:** trivial | small | medium | large | epic
- **Blocking:** yes
```
