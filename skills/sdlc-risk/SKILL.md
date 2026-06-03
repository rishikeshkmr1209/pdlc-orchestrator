---
name: 09-sdlc-risk
description: >
  Use when user says "risk assessment", "adversarial review", "should we ship",
  "risk analysis", or when sdlc-pipeline invokes after verification phase.
allowed-tools:
  - Read
  - Grep
  - Glob
---

# SDLC Risk Assessment Skill

## Prime Directive

> **Your job is to BREAK things. Be the adversary the customer will be.**

You are the devil's advocate. Assume every component will fail, every assumption is wrong,
every input is malicious, and every dependency is unreliable. Your role is to find the risks
that optimistic engineers overlook. You do NOT fix anything -- you expose what is broken,
fragile, or dangerous.

Think like:
- A malicious user trying to steal data or get free items
- A competitor trying to disrupt service on Black Friday
- A disgruntled insider with production access
- A script kiddie scanning for OWASP Top 10
- An SRE paged at 3 AM during a cascading failure
- A power user who does things nobody anticipated

## What You DO NOT Do

- Fix issues (only identify them)
- Rewrite code
- Change the design
- Write files or execute commands
- Approve without critical analysis
- Be optimistic
- Assume things will work

This skill is **READ-ONLY**. It assesses risk. It does not remediate.

---

## Arguments

```
--ticket=TICKET-ID    (required) Jira ticket ID, e.g., TICKET-1234
```

The ticket ID is used to locate prior pipeline artifacts and to name the output checkpoint.

---

## Process

> **Before reading any files:** Read `skills/_shared/parallel-reads-rule.md` and follow it for all file reads in this phase.

### Step 0: Load Prior Artifacts

Extract only the required sections from each artifact using the extraction script:

```bash
python3 claude-master-plugin/scripts/extract-sections.py \
  docs/artifacts/<ticket>/ph1_problem_spec.md \
  "Requirements" "Constraints" "Assumptions" "Edge Cases" "Non-Goals"

python3 claude-master-plugin/scripts/extract-sections.py \
  docs/artifacts/<ticket>/ph2_design_spec.md \
  "Architecture" "API Contracts" "Decisions (ADRs)" "Security Considerations" "Implementation Guidelines"

python3 claude-master-plugin/scripts/extract-sections.py \
  docs/artifacts/<ticket>/ph5_6_impl_manifest.md \
  "Files Changed Summary" "Known Dependencies / Open Items" "Simplification"
```

(See `claude-master-plugin/config/phase-artifact-map.json → Ph9_risk`.)

Also read in full:
- `artifact-digest.md` (from `.state/`) — overall context (read in full; see `phase-artifact-map.json → Ph9_risk`)
- `ph8_verification_report.md` — full file (risk assessment builds on verification findings)

For Step 2 (assumption challenges), read the full `## Assumptions` section already extracted above — the ASM-### IDs and exact text are needed.

If any required artifact is missing, STOP and report which artifacts are absent.
Do not proceed with a partial assessment — all three core artifacts (problem_spec, design_spec, verification_report) are required.

Also read the actual implementation files referenced in the ph2_design_spec.md or
ph5_6_impl_manifest.md using absolute paths.

### Step 1: Enter Adversarial Mindset

Before analyzing anything, prime your thinking with these adversarial prompts:

1. "What would Murphy's Law say?" -- Anything that can go wrong, will.
2. "What would a malicious intern do?" -- Insider threat scenarios.
3. "What would happen at 3 AM on Black Friday?" -- Worst-case timing and load.
4. "What would a competitor with our source code do?" -- Targeted attacks.
5. "What would a user who reads nothing do?" -- UX edge cases.
6. "What if the third-party service has a bad day?" -- Dependency failures.
7. "What if this data is wrong?" -- Data integrity issues.
8. "What if two users do this simultaneously?" -- Concurrency.
9. "What if the network is terrible?" -- Degraded connectivity.
10. "What if someone has to debug this at 3 AM?" -- Operability and observability.

### Step 2: Challenge Assumptions

For each assumption (ASM-###) from the problem_spec:

| Question | Detail |
|----------|--------|
| What if this assumption is completely wrong? | Describe the scenario |
| Likelihood of being wrong | low / medium / high |
| Impact if wrong | low / medium / high / critical |
| Existing mitigation (from design) | Quote the relevant design decision |
| Is existing mitigation adequate? | yes / no / partial |
| Recommended additional mitigation | Specific, actionable recommendation |
| Monitoring suggestion | What metric or alert would detect this |

Do not skip any assumption. Every ASM-### must be challenged.

### Step 3: Identify Failure Modes (FM-###)

Systematically identify failure modes by category. Refer to
`references/risk-categories.md` for the full taxonomy.

Walk through every category:
- Network failures
- Data failures
- State failures
- Concurrency failures
- Dependency failures
- Configuration failures
- Human/operational failures

For each failure mode identified:

Each failure mode has: `id` (FM-###), `mode`, `trigger`, `consequence`, `likelihood`, `severity`, `detection`, `prevention`, `recovery`, `related_component`. For full structure, see `appendix/examples.md`.

Use the severity matrix to calculate risk:

|  | Negligible | Minor | Moderate | Severe | Catastrophic |
|--|------------|-------|----------|--------|--------------|
| **Certain** | Low | Medium | High | Critical | Critical |
| **Likely** | Low | Medium | High | High | Critical |
| **Possible** | Low | Low | Medium | High | High |
| **Unlikely** | Low | Low | Low | Medium | High |
| **Rare** | Low | Low | Low | Low | Medium |

### Step 4: Construct Attack Scenarios (ATK-###)

Consider three attacker profiles:

- **external_unauthenticated**: No credentials, scanning for open doors
- **authenticated_user**: Valid account, trying to escalate or abuse
- **insider_threat**: Has production access, internal knowledge

For each scenario:

Each scenario has: `id` (ATK-###), `attacker_profile`, `goal`, `attack_vector`, `steps`, `likelihood`, `impact`, `current_mitigation`, `mitigation_gap`, `recommended_mitigation`. For full structure, see `appendix/examples.md`.

Minimum attack scenarios to consider:
- Injection attacks (XSS, SQL injection, command injection)
- Authentication/authorization bypass
- Data exfiltration or PII exposure
- Denial of service (resource exhaustion)
- Price/quantity manipulation (QSR-specific)
- Replay attacks on sensitive operations
- IDOR (Insecure Direct Object References)

### Step 5: Scan for Blind Spots (BS-###)

Evaluate the implementation against all 10 blind spot categories:

1. **scalability** -- Horizontal scaling limits, database bottlenecks, cache capacity
2. **edge_cases** -- Timezone issues, Unicode handling, large payloads, empty states
3. **user_behavior** -- Rapid clicking, back button, multiple tabs, rage taps
4. **third_party_dependencies** -- Rate limits, API changes, outages, SDK deprecation
5. **data_consistency** -- Eventual consistency, replication lag, split-brain scenarios
6. **compliance** -- GDPR right to erasure, PCI scope, data residency, cookie consent
7. **accessibility** -- Screen reader support, keyboard navigation, color contrast
8. **performance** -- Cold start latency, bundle size, render blocking, memory leaks
9. **maintainability** -- Code complexity, documentation gaps, bus factor, tech debt
10. **observability** -- Missing metrics, insufficient logging, alert fatigue, debug difficulty

For each blind spot:

Each blind spot has: `id` (BS-###), `category`, `description`, `example`, `questions_to_answer`, `impact`, `recommendation`. For full structure, see `appendix/examples.md`.

Every category must be evaluated. If a category has no blind spots, explicitly
state that and explain why.

### Step 6: Design Stress Test Scenarios

Define scenarios that push the system to its limits:

| Scenario | Description |
|----------|-------------|
| 10x normal load | What happens when traffic spikes to 10x baseline |
| Concurrent users at peak | Maximum concurrent users for the feature |
| Data volume at maximum | Largest realistic dataset the feature must handle |
| Network degradation | 1000ms+ latency, packet loss, intermittent connectivity |
| Dependent service outage | Primary dependency returns 500s for 5+ minutes |
| Cascading failure | One failure triggers others across the system |
| Data corruption | Invalid or malformed data enters the pipeline |
| Resource exhaustion | Memory, CPU, connections, or storage at capacity |

For each:

Each entry has: `scenario`, `expected_behavior`, `actual_risk` (handled/degraded/unknown/will_fail), `recommendation`. For full structure, see `appendix/examples.md`.

### Step 7: Assess Dependency Risks

Catalog every dependency and its risk profile:

| Type | Examples |
|------|----------|
| npm_package | Third-party libraries, transitive dependencies |
| external_api | Payment providers, CDN, third-party services |
| internal_service | Other project microservices, shared infrastructure |
| infrastructure | AWS services, databases, message queues |
| human | Team knowledge, on-call availability, deployment process |

For each dependency:

Each entry has: `dependency`, `type`, `risk`, `likelihood`, `mitigation`. For full structure, see `appendix/examples.md`.

### Step 8: Make Ship Recommendation

Based on all findings, make ONE of these recommendations:

#### `ship`
- Overall risk level: **LOW**
- No critical or major failure modes identified
- All high-impact assumptions have adequate mitigation
- Attack surface is well-defended
- No blocking blind spots

#### `ship_with_monitoring`
- Overall risk level: **MEDIUM**
- Medium-severity risks exist but are mitigatable with monitoring
- Must specify:
  - **What to watch**: Specific metrics, logs, and dashboards
  - **Alert thresholds**: Concrete numbers that trigger alerts
  - **Rollback triggers**: Conditions that require immediate rollback
  - **Monitoring duration**: How long enhanced monitoring should last

#### `fix_first`
- Overall risk level: **HIGH**
- Specific blocking issues that must be resolved before shipping
- List each blocking issue with:
  - Issue reference (FM-###, ATK-###, or BS-###)
  - Why it blocks shipping
  - Suggested remediation (fed back to implementation phase)
  - Estimated effort

#### `redesign`
- Overall risk level: **CRITICAL**
- Fundamental architectural issues that cannot be patched
- Requires returning to the architecture/design phase
- List each architectural concern with:
  - What is fundamentally wrong
  - Why patching is insufficient
  - What a redesign should address

### Step 9: Document Rollback Plan

For every verdict (including `ship`), document:

| Field | Detail |
|-------|--------|
| **Rollback trigger** | Conditions that require immediate rollback (error rate threshold, user-facing breakage, data corruption) |
| **Rollback steps** | Ordered steps to revert — feature flag off, redeploy previous version, DB migration rollback if needed |
| **Estimated recovery time** | How long a full rollback takes |
| **Rollback owner** | Team or on-call responsible for executing rollback |
| **Rollback risk** | Any risk introduced by rolling back (e.g. data already written, external consumers notified) |

### Step 10: Compile Prioritized Recommendations

Consolidate all findings into a prioritized action list:

Each recommendation has: `priority` (1-5), `category`, `action`, `rationale`, `effort`, `blocking`. For full structure, see `appendix/examples.md`.

Priority scale:
- **1**: Must do before ship (blocking)
- **2**: Should do before ship (high value)
- **3**: Do within first sprint after ship
- **4**: Add to backlog
- **5**: Nice to have

### Step 10: Save Output

Save the complete risk assessment to:

```
ph9_risk_assessment.md
```

### LLM Self-Validation: Required Sections
Before saving ph9_risk_assessment.md, verify these sections exist and are non-empty:
- [ ] `## Meta` — ticket ID, date, assessor
- [ ] `## Summary` — overall risk level and recommendation
- [ ] `## Failure Modes` — identified failure modes with severity and mitigation
- [ ] `## Rollback Plan` — trigger conditions, steps, recovery time, owner, rollback risk
- [ ] `## Sign-Off` — final recommendation (ship/ship_with_monitoring/fix_first/redesign)

---

## Output Format

The `ph9_risk_assessment.md` file must contain these Markdown sections: `## Meta`, `## Summary`, `## Assumption Challenges`, `## Failure Modes`, `## Attack Scenarios`, `## Blind Spots`, `## Stress Test Scenarios`, `## Dependency Risks`, `## Rollback Plan`, `## Recommendations`, `## Sign-Off`. For examples, see `appendix/examples.md`.

---

## Confidence Score Guidelines

| Score | Meaning |
|-------|---------|
| 90-100 | All artifacts reviewed, codebase thoroughly analyzed, high confidence in findings |
| 70-89 | Good coverage but some areas could not be fully assessed |
| 50-69 | Partial assessment -- missing artifacts or limited codebase access |
| Below 50 | Incomplete assessment -- flag and explain what is missing |

---

## Project-Specific Risk Considerations

Always evaluate these project-specific risk areas (customize for the project domain):

- **Multi-brand/tenant configuration**: Could brand-specific config changes affect other brands/tenants?
- **Multi-region deployment**: Data residency violations, latency impact, deployment ordering
- **Payment scope**: Does this change expand PCI scope? Payment provider failover behavior?
- **CDN and edge**: Cache poisoning, stale content serving, purge delay impact
- **Mobile native**: App store review risk, native bridge failures, offline sync
- **Domain-specific business logic**: Race conditions or manipulation risks in core business flows (e.g., pricing, inventory, transactions)
- **Loyalty/rewards (if applicable)**: Point balance manipulation, double-earn exploits, redemption abuse
- **Feature flags**: Flag dependency risk, stale flag cleanup, flag interaction conflicts

---

## References

- Read `references/risk-categories.md` only to enumerate failure modes beyond those you identify from the artifacts
- `appendix/examples.md` — JSON templates for all steps and output format
- `appendix/evaluation.md` — Trigger testing table
