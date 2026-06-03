# Pipeline Orchestrator — Evaluation Table

Use this table for testing skill trigger behavior. Not needed during normal operation.

| Scenario | Input | Expected behavior |
|----------|-------|-------------------|
| Trigger -- positive | "run sdlc pipeline --ticket=TICKET-1234" | Activates, starts full pipeline in gated mode |
| Trigger -- positive | "/client-master:00-sdlc-pipeline --ticket=TICKET-999" | Activates in gated mode |
| Trigger -- positive | "start pipeline for TICKET-500" | Activates and parses the ticket |
| Trigger -- negative | "review this code" | Does NOT activate (use code-review) |
| Argument validation | "--ticket=ilo-1" | Rejects invalid ticket format |
| Argument validation | "--resume" (no ticket) | Rejects missing ticket |
| Resume | "--ticket=TICKET-1 --resume" | Loads state, resumes from checkpoint |
| Resume with --from | "--ticket=TICKET-1 --resume --from=implementation" | Loads artifacts, starts from implementation |
| Iteration limit | Design review rejects 3 times | Halts, reports manual intervention needed |
| Missing artifact | Phase 2 runs without ph1_problem_spec.md | Halts, reports missing artifact |
| Subagent failure | security-auditor crashes in phase 6 | Warns, continues with partial results |
| Default gate pause | Phase 1 completes | Displays summary, waits for input |
| Phase 4 planning | Design approved | Invokes sdlc-impl-planning, writes ph4_implementation_plan.md, proceeds to the Phase 4 gate |
| Phase 4 resume | --resume with impl-planning=completed | Skips planning, goes directly to Phase 5 (implementation) |
| Context clear gate | After Phase 4 completes | Offers 3 options: continue, clear context and resume, revise plan |
| --from=impl-planning | Explicit re-plan request | Re-runs Phase 4 (planning), then proceeds to Phase 5 |
