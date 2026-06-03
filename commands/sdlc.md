Run the full SDLC multi-agent pipeline from requirements through PR creation.

Arguments: $ARGUMENTS

**IMPORTANT:** Do NOT attempt to read or locate skill files. Instead, use the `Skill` tool to invoke skills by name.

To run the pipeline, invoke the `sdlc-pipeline` skill using the Skill tool:

```
Skill: client-master:sdlc-pipeline
Args: $ARGUMENTS
```

The `sdlc-pipeline` skill accepts these arguments:
- `--ticket=TICKET-ID` — Jira ticket ID in `PREFIX-NUMBER` format (e.g., `TICKET-1234`, `TICKET-567`)
- `--resume` — reload the last checkpoint for the given ticket
- `--from=phase` — start from a specific phase (requirements, architecture, design-review, impl-planning, implementation, simplify, review, verification, risk, pr)
- `--waves` — force wave-based parallel execution for implementation regardless of file count
- `--rebuild-index` — force rebuild of the codebase index before exploration

The pipeline always runs in gated mode. Users should omit `--mode`.

Example: `--ticket=TICKET-1234`

The pipeline executes phases based on ticket classification. Phase 0 always runs first:
0. Classification (Jira ticket analysis — determines which phases run)
1. Requirements Analysis
2. Architecture Design
3. Design Review (quality gate)
4. Implementation Planning
5. Implementation Execution
6. Simplify (code cleanup via /simplify)
7. Review (parallel: spec-reviewer + test-engineer + security-auditor)
8. Verification
9. Risk Assessment
10. PR Creation

All artifacts are written to `docs/artifacts/<ticket>/` at the project root.
State files (`pipeline_state.json`, `artifact-digest.md`, `impl_state.json`) live in `docs/artifacts/<ticket>/.state/`.

Invoke the skill now with the arguments provided above.
