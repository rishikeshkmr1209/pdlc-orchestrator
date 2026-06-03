# Verify Skill — Evaluation Table

Use this table for testing skill trigger behavior. Not needed during normal operation.

| Scenario | Input | Expected Behavior |
|----------|-------|-------------------|
| Trigger -- positive | "verify implementation --ticket=TICKET-1234" | Skill activates, runs full verification |
| Trigger -- positive | "run verification --ticket=TICKET-567" | Skill activates |
| Trigger -- positive | "check implementation --ticket=TICKET-999" | Skill activates |
| Trigger -- negative | "review this code" | Skill does NOT activate (use code-review) |
| Trigger -- negative | "scan for security issues" | Skill does NOT activate (use security-scan) |
| Missing ticket | "verify implementation" | Prompts for --ticket argument |
| Missing artifacts | Checkpoint dir exists but ph1_problem_spec.md missing | Reports missing artifact, does not proceed |
| No tests | Implementation has zero test files | Score reflects 0/40 for test pass rate, recommendation to add tests |
| All passing | Full coverage, no findings, all tests pass | Status: passed, score near 100 |
| Edge case | Empty problem_spec (no requirements) | Awards full requirement coverage (nothing to cover), flags as unusual |
| Subagent results | test_report.json and security_audit.json present | Aggregates findings, deduplicates, attributes sources |
