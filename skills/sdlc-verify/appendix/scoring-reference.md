# Verification Scoring Reference

This file contains the detailed scoring formulas and category tables for the sdlc-verify skill.
Read this file only when you need the exact math or category descriptions during scoring.

---

## Scoring Formulas

### Requirement Coverage (60 points max)

```
covered_acs = count of ACs with status "passed"
total_acs = count of all ACs in problem_spec
wiring_deductions = sum of wiring finding deductions (Step 2.5):
  not_found:         -3 per component
  stub:              -2 per component
  imported_not_used: -1 per component
  not_imported:      -2 per component
requirement_score = max(0, (covered_acs / total_acs) * 60 - wiring_deductions)
```

Round to nearest integer. If `total_acs` is 0, award full 60 points (nothing to cover).

### Test Pass Rate (40 points max)

```
total_tests = unit.total + integration.total + e2e.total
passed_tests = unit.passed + integration.passed + e2e.passed
test_score = (passed_tests / total_tests) * 40
```

Round to nearest integer. If `total_tests` is 0, award 0 points (no tests is a problem).

### Final Score

```
score = requirement_score + test_score
```

Clamp to [0, 100].

---

## Terminal Output Format

After saving the report, display this human-readable summary:

```
## Verification Report: <TICKET-ID>

### Status: <PASSED/PASSED_WITH_WARNINGS/FAILED>
### Score: <score>/100

### Score Breakdown
| Dimension            | Score | Max | Details                    |
|----------------------|-------|-----|----------------------------|
| Requirement Coverage | XX    | 60  | X/Y ACs covered, X wiring deductions |
| Test Pass Rate       | XX    | 40  | X/Y tests passing          |

### Requirement Coverage
| REQ     | Priority | Status           | ACs Covered |
|---------|----------|------------------|-------------|
| REQ-001 | P0       | fully_covered    | 3/3         |
| REQ-002 | P1       | partially_covered| 1/2         |

### Blocking Issues (must fix)
1. [REQ-001] P0 requirement has uncovered ACs
2. [WIRING] Component COMP-003 not found at expected path

### Edge Cases: X/Y tested

### Top Recommendations
1. (P1, blocking) Implement missing acceptance criteria for REQ-001
2. (P2, blocking) Create missing component COMP-003
3. (P3) Add unit test for empty cart edge case — EC-001

Report saved to: docs/artifacts/<TICKET>/ph8_verification_report.md
```
