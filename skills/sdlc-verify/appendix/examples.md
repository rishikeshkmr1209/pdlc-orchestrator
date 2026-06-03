# Verify Skill — Examples & Output Templates

This file contains Markdown output examples for the sdlc-verify skill steps.
Read this file only if you need format guidance for producing `ph8_verification_report.md`.

---

## Step 3: Requirement Coverage Output Format

```markdown
## Requirement Coverage

### REQ-001
- **Status:** partially_covered
- **Implementation files:** `src/features/cart/cart-service.ts`, `src/features/cart/cart.tsx`

| AC ID  | Status          | Test IDs       | Notes                                       |
|--------|-----------------|----------------|---------------------------------------------|
| AC-001 | passed          | UT-001, UT-002 | Both unit tests validate add-to-cart flow   |
| AC-002 | not_implemented |                | No test for empty cart edge case            |
```

## Step 4: Test Results Output Format

```markdown
## Test Results

### Unit
- **Total:** 42
- **Passed:** 38
- **Failed:** 3
- **Skipped:** 1
- **Coverage:** 82.5%
- **Duration:** 8500ms

#### Failures

| Test Name                          | File                                                   | Error                            | Expected | Actual |
|------------------------------------|--------------------------------------------------------|----------------------------------|----------|--------|
| CartService should apply discount  | src/features/cart/__tests__/cart-service.test.ts        | Expected 9.99 but received 10.00 | 9.99     | 10.00  |

### Integration
- **Total:** 0 | **Passed:** 0 | **Failed:** 0 | **Skipped:** 0 | **Duration:** 0ms

### E2E
- **Total:** 0 | **Passed:** 0 | **Failed:** 0 | **Skipped:** 0 | **Duration:** 0ms
```

## Step 5: Quality Finding Structure

```markdown
## Quality Findings

### QF-001
- **Category:** complexity
- **Severity:** high
- **File:** `src/features/cart/hooks/use-cart.ts`
- **Line:** 45
- **Description:** useEffect contains 4 levels of nesting with async operations. Race condition likely if component unmounts during fetch.
- **Suggestion:** Extract async logic into a custom hook with AbortController cleanup. Use early returns to reduce nesting.
- **Effort:** 2 hours
```

## Step 6: Security Finding Structure

```markdown
## Security Findings

### SF-001
- **Category:** owasp_a01_broken_access_control
- **Severity:** critical
- **CVSS Score:** 8.5
- **CWE ID:** CWE-639
- **File:** `src/features/orders/mutations/update-order.ts`
- **Line:** 23
- **Description:** Mutation accepts userId from client input without verifying against the authenticated session. An attacker can modify any user's order by supplying a different userId.
- **Attack Vector:** Authenticated user modifies the userId parameter in the GraphQL mutation to target another user's order.
- **Remediation:** Extract userId from the JWT token in the request context. Ignore any client-supplied userId. Add server-side ownership validation before mutation execution.
- **Blocking:** yes
```

## Step 7: Edge Case Coverage Output Format

```markdown
## Edge Case Coverage

### EC-001
- **Status:** not_tested
- **Test ID:** —
- **Notes:** No test for empty cart submission. Implementation has a guard clause at cart-service.ts:78 but it is not tested.
```

## Step 8: Recommendation Structure

```markdown
## Recommendations

1. **Priority 1 — blocking — security**
   Add server-side ownership validation to update-order mutation.
   _Rationale:_ SF-001: Broken access control allows any authenticated user to modify another user's order. OWASP A01 critical finding.
```

## Step 11: Report Schema — Required Top-Level Sections

```markdown
## Meta
- **Feature ID:** <TICKET-ID>
- **Created at:** <ISO 8601 UTC timestamp>
- **Agent version:** 2.0
- **Design spec ref:** docs/artifacts/<TICKET>/ph2_design_spec.md
- **Implementation ref:** <git SHA or branch name>

## Summary
- **Status:** passed | passed_with_warnings | failed | blocked
- **Score:** 0-100
- **Blocking issues:** <count of blocking recommendations>
- **Total issues:** <count of all findings>
- **Test pass rate:** 0-100
- **Coverage percentage:** 0-100

## Requirement Coverage

| REQ | Priority | Status | ACs Covered |
|-----|----------|--------|-------------|
| ... | ...      | ...    | ...         |

## Test Results

### Unit
_(metrics)_

### Integration
_(metrics)_

### E2E
_(metrics)_

## Quality Findings
_(list of findings)_

## Security Findings
_(list of findings)_

## Edge Case Coverage
_(list of edge cases)_

## Recommendations
_(prioritized list)_
```
