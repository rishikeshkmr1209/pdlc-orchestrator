# Architecture Decision Record — Claude Master Plugin

## ADR-001: Plugin Repository Structure

**Date:** 2026-02-23
**Status:** Accepted
**Deciders:** Platform Engineering team

---

## Context

This organization has multiple development groups building on JS/TS + AWS stacks. Each team was independently configuring Claude Code, leading to:
- Inconsistent behavior across teams
- Duplicated effort writing the same prompts and skills
- No security review process for AI-powered code modifications
- No shared institutional knowledge about project-specific conventions

We needed a centralized, version-controlled repository that all teams could adopt with minimal friction while allowing team-specific customization.

---

## ADR-002: Skills Over Commands as the Primary Extension Point

**Date:** 2026-02-23
**Status:** Accepted

### Context

Claude Code supports two ways to add reusable behaviors:
1. **Slash commands** (`commands/*.md`) — manually invoked via `/command-name`
2. **Skills** (`skills/*/SKILL.md`) — auto-invoked based on frontmatter `description:`

### Decision

We will use **Skills as the primary extension point** for new functionality. Slash commands are retained only for backward compatibility and as thin wrappers that invoke skills.

### Considered Alternatives

**Option A: Commands only**
- Pros: Simple, users know exactly when they run; no auto-invocation surprises
- Cons: Requires users to remember command names; can't leverage auto-triggering; no supporting files structure

**Option B: Skills only**
- Pros: Auto-triggering improves developer experience; supporting `references/` structure allows rich context
- Cons: Auto-invocation can feel surprising to users unfamiliar with the system

**Option C: Skills + Commands (chosen)**
- Pros: Skills provide the rich feature set; Commands provide explicit fallback; backward-compatible
- Cons: Some redundancy in maintaining both

### Consequences

**Positive:**
- Skills auto-trigger on natural language, reducing friction
- `references/` and `templates/` subdirectories allow rich supporting context without bloating SKILL.md
- Frontmatter control over tools and context (`fork`) provides security and isolation

**Negative:**
- Learning curve: contributors must understand both mechanisms
- Auto-invocation requires careful `description:` wording to avoid false triggers

---

## ADR-003: Least-Privilege Tool Access

**Date:** 2026-02-23
**Status:** Accepted

### Context

Claude Code skills and agents can be granted access to a range of tools from read-only (`Read`, `Grep`, `Glob`) to write-capable (`Write`, `Edit`) to shell-execution (`Bash`). Granting too many tools increases the risk of unintended actions; granting too few limits usefulness.

### Decision

We will enforce **least-privilege tool access** via:
1. Explicit `allowed-tools:` / `tools:` lists in all frontmatter (no wildcard)
2. A documented tool least-privilege table in `docs/STANDARDS.md`
3. A mandatory security review for any skill/agent requesting `Bash` or `Write`

### Consequences

**Positive:**
- Reduces blast radius of a misconfigured or adversarially-triggered skill
- Clear audit trail of what each skill/agent can do
- Forces contributors to justify `Bash` access

**Negative:**
- Some legitimate skills require more permissive access and go through more review friction
- Cannot use `tools: ["*"]` as a quick default

---

## ADR-004: `context: fork` for File-Writing Skills

**Date:** 2026-02-23
**Status:** Accepted

### Context

Skills that write files (like `generate-tests`) can pollute the main conversation context if they run inline — intermediate reasoning steps, tool call outputs, and generated file contents all appear in context, potentially confusing subsequent prompts.

### Decision

Skills that write files will use `context: fork` in frontmatter, which runs the skill in an isolated subagent. The main conversation sees only the final output.

### Consequences

**Positive:**
- Main conversation context stays clean after file-writing operations
- Isolated context prevents generated test code from affecting subsequent code review quality

**Negative:**
- The isolated skill can't access conversation history from before invocation
- Requires the SKILL.md to be self-contained

---

## ADR-005: No Hardcoded Org Secrets in Shared Plugin

**Date:** 2026-02-23
**Status:** Accepted

### Context

Teams need org-specific values like AWS account IDs, internal service URLs, and deployment regions. If these were in the shared plugin, every team's changes would affect all other teams, and secrets could be accidentally shared.

### Decision

The shared plugin contains **no org-specific values**. These live exclusively in project-level `CLAUDE.md` files that extend the master via the `@import` pattern.

### Consequences

**Positive:**
- Shared plugin is safe to open-source within the org without leaking sensitive values
- Teams can customize independently without affecting others

**Negative:**
- Teams must maintain their own project-level `CLAUDE.md` files
- No central place to update a value across all projects (e.g., if a service URL changes)

---

## ADR-006: Progressive Disclosure via `references/` Directories

**Date:** 2026-02-23
**Status:** Accepted

### Context

Skills need detailed reference material (e.g., OWASP Top 10 remediation patterns, AWS security checklist) to produce high-quality output. Putting all this in SKILL.md would make it unwieldy (>1000 lines). Loading it all at invocation time would waste context.

### Decision

SKILL.md bodies stay under 300 lines. Detailed reference material lives in `references/` subdirectories and is loaded on-demand when the skill needs it.

### Consequences

**Positive:**
- SKILL.md files are readable and maintainable
- Reference material can be updated independently of the skill logic
- Claude loads only the context it needs

**Negative:**
- Skill must explicitly reference the `references/` files for Claude to load them
- More files to maintain

---

## System Architecture Diagram

```
Plugin Repository (claude-master-plugin/)
  ├── .claude-plugin/
  │    ├── marketplace.json   ← Marketplace catalog
  │    └── plugin.json        ← Plugin manifest
  ├── agents/                 ← 6 specialized subagents (plugin root)
  │    └── *.md               ← Auto-available via /agents command
  ├── skills/                 ← 17 auto-invocable skills (plugin root)
  │    └── */SKILL.md         ← Triggers based on description: frontmatter
  ├── commands/               ← 1 slash command (/sdlc) (plugin root)
  │    └── *.md
  ├── hooks/                  ← Hook wiring + scripts (plugin root)
  │    ├── hooks.json         ← ${CLAUDE_PLUGIN_ROOT} paths
  │    └── *.py / *.sh
  ├── .claude/
  │    ├── schemas/           ← JSON schemas for SDLC artifacts
  │    └── statusline-script.sh
  ├── .mcp.json               ← MCP server definitions
  └── CLAUDE.md               ← Master context (org identity, conventions)

Engineer's Project (child)
  └── CLAUDE.md (project-level, extends master)
       └── Loaded at every Claude session start
```

The plugin provides **passive context** (CLAUDE.md) and **active capabilities** (skills, agents, commands, hooks). The passive context shapes all Claude behavior; the active capabilities are invoked on demand or auto-triggered.

---

## ADR-007: Skills-Based SDLC Pipeline Over Multi-Agent Pipeline

**Date:** 2026-02-25
**Status:** Accepted

### Context

A team member proposed a multi-agent sequential pipeline for SDLC automation (one agent per phase). After analysis against Anthropic's published best practices, we identified four critical problems: codebase re-exploration tax per agent, sequential dependency negating parallelism benefits, lossy cross-phase context handoffs, and the category error of treating methodologies as execution agents.

### Decision

We adopt a **skills-based architecture with checkpoint artifacts** that preserves the deep methodology from the multi-agent approach while eliminating its architectural overhead:

1. **Phase skills** (not agents) for methodology: sdlc-requirements, sdlc-architecture, sdlc-design-review, sdlc-qa-test-generation (Phase 3b — runs in parallel with sdlc-design-review for Large Feature, sequentially after sdlc-architecture for Small Feature; informational, does not gate Phase 4), sdlc-impl-planning, sdlc-verify, sdlc-risk
2. **Checkpoint artifacts** at phase boundaries for compaction resilience and structured contracts
3. **Subagents** only for genuinely isolated execution: code-reviewer (fresh context), test-engineer (verbose output), security-auditor (fresh context)
4. **Thin orchestrator skill** (sdlc-pipeline) with auto/gates/resume modes

### Considered Alternatives

**Option A: Multi-Agent Pipeline (rejected)**
- Pros: Fresh context per phase (no compaction risk), independent validation, structured JSON contracts
- Cons: Nx codebase exploration (~320K tokens wasted), lossy handoffs, no prompt caching, manual copy-paste workflow, 3-4x total token cost

**Option B: Skills Only, No Checkpoints (rejected)**
- Pros: Simplest implementation, full context sharing
- Cons: Compaction risk for large features, no structured validation, no resume capability

**Option C: Skills + Checkpoints + Subagents (chosen)**
- Pros: Context continuity, prompt caching, structured contracts via schemas, compaction resilience via disk checkpoints, independent review via subagents, gated orchestration with standalone phase skills
- Cons: Single-session bias (mitigated by fresh-context subagents), compaction still possible (mitigated by checkpoint artifacts)

### Consequences

**Positive:**
- 60-70% token reduction vs multi-agent (one codebase exploration instead of eight)
- Full prompt caching benefits (single session)
- Deep methodology preserved (500+ line skills match agent prompt depth)
- Structured validation via JSON schemas at every phase boundary
- Developer-friendly (1 session, 3 modes, resume capability)

**Negative:**
- Compaction risk for very large features (mitigated by checkpoint artifacts on disk)
- Skills share context biases (mitigated by fresh-context subagents for review)

### References

- Design doc: `docs/plans/2026-02-25-sdlc-pipeline-design.md`
- Source analysis: [Original Author]'s agentic workflow at `github.com/your-org/dev-repo`

---

## SDLC Pipeline Architecture

```
+------------------------------------------------------------------------+
|  MAIN ORCHESTRATOR (single Claude Code session)                         |
|                                                                          |
|  Phase Skills (inline, share context):                                   |
|  [sdlc-requirements] -> [sdlc-architecture] -> [sdlc-design-review]    |
|       -> [sdlc-impl-planning] -> [implementation] -> [review]           |
|       -> [sdlc-verify] -> [sdlc-risk] -> [create-pr]                   |
|                                                                          |
|  Checkpoint Skill: [sdlc-checkpoint] save/load/validate/status          |
|  Existing Skills: [code-review] [security-scan] [generate-tests]        |
|  Orchestrator:    [sdlc-pipeline] --ticket=<ticket>                    |
+------------------------------------------------------------------------+
           |                    |                    |
  +--------v--------+  +-------v--------+  +--------v--------+
  | code-reviewer   |  | test-engineer  |  | security-auditor|
  | (subagent)      |  | (subagent)     |  | (subagent)      |
  | fresh context   |  | verbose output |  | fresh context   |
  | read-only       |  | bash access    |  | read-only       |
  +-----------------+  +----------------+  +-----------------+

Checkpoint Storage:
  docs/artifacts/<ticket>/          (git-tracked: problem_spec, design_spec, design_review)
  .claude/checkpoints/<ticket>/     (ephemeral: impl_manifest, verification, risk_assessment)
  .claude/schemas/                  (JSON schemas for validation)
```

## ADR-008: Phase 3b QA Test Generation (parallel with Design Review)

### Context

Until now, QA representation in the pipeline first appeared in Phase 7 (post-implementation review), where the `test-engineer` subagent inspected coverage. That is too late to: stage Jira Test issues for QA before development begins, populate Zephyr ahead of dev, or pre-stage automation work that targets `qa-automation`.

### Decision

Introduce a Phase 3b skill, `sdlc-qa-test-generation`, that:

1. Reads `ph1_problem_spec.md` and `ph2_design_spec.md` (and the `platform-knowledge` repo for service context).
2. Generates a test plan mapping every AC → test cases.
3. Creates Jira issues with `issuetype = Test`, linked to the parent story via the standard `Tests` / `is tested by` link type. Existing Zephyr tests matched against JQL filter `28319` are amended via comment rather than mutated.
4. Classifies a regression subset using a documented heuristic (`references/regression-rules.md`).
5. Autonomously opens a single PR in `qa-automation` for the regression subset, choosing update-vs-new per existing tests.

For a `Large Feature` phase set, Phase 3b runs **in parallel** with Phase 3 (design-review), dispatched as concurrent subagents in a single `Agent` tool-use block. For a `Small Feature` phase set (no design-review), Phase 3b runs sequentially after Phase 2.

### Considered Alternatives

- **Sequential after design-review approval (rejected):** would idle the pipeline while QA work that does not depend on the verdict could already run. Design review and QA generation read disjoint outputs and write disjoint artifacts.
- **Move Phase 7 test-engineer earlier (rejected):** test-engineer needs implemented code to verify; that is fundamentally a post-implementation role. Phase 3b is a *generation* role, not a *verification* role.
- **Bundle into Phase 2 architecture (rejected):** would grow Phase 2 scope and make architecture iteration slower. Keeping it separate preserves Phase 2's focus.

### Consequences

**Positive:**
- QA work starts in parallel with design review, compressing the wall-clock time of the gated pair.
- Jira Test issues exist before development begins, so QAs and devs share a contract from day 1.
- Regression automation lands in `qa-automation` ahead of code review of the implementation PR, so the gate the application PR has to pass is concrete.
- The skill is **informational only**: a failure or skipped automation does not gate Phase 4; only the design-review verdict gates.

**Negative:**
- On a `reject` design-review verdict that loops Phase 2, both Phase 3 and Phase 3b rerun. Mitigated by idempotency: the skill reads `.state/qa_jira_issues.json` and `.state/qa_automation.json` and skips already-created Jira issues / amends the same `qa-automation` branch instead of opening a duplicate PR.
- Adds a dependency on the user's Atlassian MCP being configured (per ADR-005, the plugin does not bake credentials).
- Adds two environment variables: `INTL_PLATFORM_KNOWLEDGE_PATH` (auto-clones if missing) and `INTL_QA_AUTOMATION_PATH` (must be a known checkout).

### Out of scope (deliberate follow-ups)

- Live Figma MCP integration (link is referenced from `pipeline_state` only).
- Native Zephyr Squad test-step / test-coverage API (we use the standard Jira `Tests` link type and put steps in the description).
- Editing existing Zephyr tests in place (we comment with deltas instead).
- Modifying `qa-automation`'s CircleCI workflows to wire new specs into a job.

### References

- Skill: `claude-master-plugin/skills/sdlc-qa-test-generation/`
- Bootstrap script: `claude-master-plugin/scripts/ensure-platform-knowledge.sh`
- Phase set wiring: `config/jira_execution_phases.json` (`Story` excluded — it has no `ph2_design_spec.md`)
- Section extraction: `config/phase-artifact-map.json → Ph3b_qa_test_plan`
