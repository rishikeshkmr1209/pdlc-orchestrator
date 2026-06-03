# Claude Master Plugin — Solution Rationale & Developer Walkthrough

> This document explains the **why** behind every architectural decision in the Claude Master Plugin. Use it to onboard new developers, justify the approach to leadership, or as a reference when extending the system.

---

## Table of Contents

1. [The Problem](#1-the-problem)
2. [Solution Overview](#2-solution-overview)
3. [Architecture Principles](#3-architecture-principles)
4. [Layer 1: CLAUDE.md — The Behavioral Foundation](#4-layer-1-claudemd--the-behavioral-foundation)
5. [Layer 2: Hooks — Runtime Safety Net](#5-layer-2-hooks--runtime-safety-net)
6. [Layer 3: Skills — Methodology as Code](#6-layer-3-skills--methodology-as-code)
7. [Layer 4: Agents — Isolated Execution](#7-layer-4-agents--isolated-execution)
8. [Layer 5: SDLC Pipeline — Full Lifecycle Automation](#8-layer-5-sdlc-pipeline--full-lifecycle-automation)
9. [Layer 6: MCP Servers — External Tool Integration](#9-layer-6-mcp-servers--external-tool-integration)
10. [Distribution Model](#10-distribution-model)
11. [Context Window Management](#11-context-window-management)
12. [The Checkpoint System](#12-the-checkpoint-system)
13. [Testing Strategy](#13-testing-strategy)
14. [Key Design Decisions (ADR Summary)](#14-key-design-decisions-adr-summary)
15. [Evolution History](#15-evolution-history)

---

## 1. The Problem

CLIENT_ORG has 15+ engineering teams building on TypeScript/AWS. When Claude Code adoption started organically, we observed:

| Problem | Impact |
|---------|--------|
| **Inconsistent AI behavior** | Team A's Claude writes `console.log`, Team B's uses structured logger. Same org, different quality. |
| **Duplicated effort** | Every team independently wrote "don't commit .env files" rules. 15 teams × same instructions = waste. |
| **No security guardrails** | Engineers accidentally paste API keys in prompts. Claude happily reads `.env` files. No automated prevention. |
| **No shared methodology** | Some teams get excellent code reviews from Claude, others get rubber stamps. Quality depends on who wrote the prompts. |
| **No institutional memory | Lessons learned in one team (like the DI breakage incident)) never reach other teams. |

The root cause: **Claude Code has no native concept of org-wide configuration.** Each project is a silo. The master plugin solves this by creating a shared, version-controlled layer that every project inherits.

---

## 2. Solution Overview

The plugin is a **standalone Git repository** that projects install via Claude Code's native plugin system (`/plugin` commands). It provides six layers of functionality:

```
┌─────────────────────────────────────────────────────┐
│  Layer 6: MCP Servers (external tools)              │
│  Playwright                                         │
├─────────────────────────────────────────────────────┤
│  Layer 5: SDLC Pipeline (lifecycle orchestration)   │
│  10 phases · checkpoints · wave execution            │
├─────────────────────────────────────────────────────┤
│  Layer 4: Agents (isolated subprocesses)            │
│  Code Reviewer · Security Auditor · Test Engineer   │
├─────────────────────────────────────────────────────┤
│  Layer 3: Skills (methodology as code)              │
│  17 auto-invocable skills + 1 slash command         │
├─────────────────────────────────────────────────────┤
│  Layer 2: Hooks (runtime safety)                    │
│  7 hooks across 6 events · blocks before damage     │
├─────────────────────────────────────────────────────┤
│  Layer 1: CLAUDE.md (behavioral foundation)         │
│  Org identity · conventions · forbidden actions     │
└─────────────────────────────────────────────────────┘
```

Each layer is independent — you can use CLAUDE.md alone and get value. Each subsequent layer adds capability without requiring the ones above it (except the SDLC pipeline, which orchestrates skills and agents together).

---

## 3. Architecture Principles

### 3.1 Native plugin distribution

**Why:** Projects install the plugin via Claude Code's native plugin system (`/plugin marketplace add` + `/plugin install`). The plugin system resolves `${CLAUDE_PLUGIN_ROOT}` paths at runtime, delivering hooks, skills, agents, and commands without symlinks.

**Rationale:**
- **No symlinks.** Child repos keep their own `.claude/` directory, enabling project-local skills, agents, and commands alongside plugin-provided ones.
- **Namespaced.** Plugin skills appear as `client-master:*`, preventing conflicts with local skills.
- **Additive hooks.** Plugin hooks and project hooks both fire — no replacement or override.
- **Versioned.** Teams can pin to specific versions via git tags.

**History:** v1.x used symlinks (`ln -s ../claude-master-plugin/.claude .claude`) which replaced the child repo's entire `.claude/` directory, preventing any customization. v2.0 moved to the native plugin system to solve this. See [MIGRATION.md](MIGRATION.md) for the upgrade path.

### 3.2 Skills over agents for methodology

**Why:** The SDLC pipeline uses skills (inline, share context) rather than agents (isolated subprocess) for methodology phases.

**Rationale:** An early proposal used sequential agents (one per SDLC phase). Analysis revealed:
- **8× codebase re-exploration tax.** Each agent starts fresh and must re-read the same files (~40K tokens each = 320K wasted).
- **Lossy handoffs.** Cross-agent communication only happens via artifacts. Nuance gets lost.
- **No prompt caching.** Each agent is a new API call. Skills in the same session benefit from prompt caching.
- **3-4× total token cost.** Measured during design phase.

Skills preserve the deep methodology (500+ line SKILL.md files) while running in the main session's context window. Agents are reserved for genuinely isolated work (code review, security audit) where fresh context is an advantage.

### 3.3 Progressive disclosure for context

**Why:** SKILL.md files are kept under 300 lines. Detailed reference material lives in `references/` and `appendix/` subdirectories.

**Rationale:** Claude's context window is finite. Loading 18,000 tokens of scoring formulas when you only need the 3-line instruction "score from 0-100" is wasteful. Skills load their core logic first, then conditionally read references only when needed.

**Result:** Total static context dropped from ~505KB to ~120KB after optimization — enough to prevent mid-pipeline compaction.

### 3.4 Behavioral instructions, not encyclopedias

**Why:** CLAUDE.md is ~100 lines of behavioral rules, not a 300-line reference manual.

**Rationale:** Every token in CLAUDE.md is loaded into every single conversation. That means:
- 100 lines × 1000 conversations = 100K token-conversations of overhead
- Instructions that don't shape behavior (like listing available skills) waste context — Claude discovers skills automatically via frontmatter
- The CLAUDE.md should contain only rules that, if violated, would cause real damage (security breaches, broken DI, production incidents)

**What was removed in the trim:** Skill inventories (Claude discovers these), hook descriptions (Claude doesn't need to know hook internals), SDLC pipeline details (loaded on-demand by the skill), duplicate sections that restated the same rule in different words.

---

## 4. Layer 1: CLAUDE.md — The Behavioral Foundation

### What it is

A markdown file loaded at the start of every Claude Code conversation. It shapes all Claude behavior for the session.

### What's in it (and why)

| Section | Why it's there |
|---------|---------------|
| **Organization Identity** | Without this, Claude does not know it is working at your organization. It would suggest generic patterns instead of project-specific ones. |
| **Core Behavioral Principles** | 7 rules that prevent the most dangerous failure modes. Each rule was added because it was violated at least once. |
| **Forbidden Actions** | Hard blockers. These are things Claude should never do regardless of what the user asks. Security team requirement. |
| **JS/TS Conventions** | Prevents the #1 source of PR review comments: inconsistent style. |
| **Jira & Branch/PR Naming** | Security team requires traceability. Without this, Claude creates PRs without ticket IDs. |
| **PII & Data Privacy** | GDPR and privacy compliance. Logging PII is a legal risk. |
| **Implementation Safety Rules** | Extracted from a production incident. Prevents constructor default removal, DI breakage, and "test everything at the end" anti-patterns. |

### What's NOT in it (and why)

| Omitted content | Why it was removed |
|-----------------|-------------------|
| Skill/agent inventory | Claude auto-discovers these from `skills/` and `agents/` frontmatter. Listing them in CLAUDE.md wastes ~50 lines of context every conversation. |
| Hook descriptions | Claude doesn't invoke hooks — hooks invoke themselves. Claude doesn't need to know how they work. |
| SDLC pipeline phases | The `sdlc-pipeline` skill loads this when invoked. No need to carry it in every conversation. |
| MCP server details | Auto-loaded from `.mcp.json`. |

### How teams extend it

Each project creates its own `CLAUDE.md` that imports the master:

```markdown
@../claude-master-plugin/CLAUDE.md

## Project-Specific Context
- AWS Region: us-east-1
- Jira prefix: ILO
```

The `@import` pattern means project files inherit all master rules automatically. When the master updates, all projects get the update on next conversation start.

---

## 5. Layer 2: Hooks — Runtime Safety Net

### What they are

Python/Bash scripts that fire at specific Claude Code lifecycle events. They intercept actions before (or after) they happen.

### The 7 hooks

| Hook | Event | Why it exists |
|------|-------|--------------|
| **Prompt Scanner** | `UserPromptSubmit` | Engineers accidentally paste API keys, JWTs, and credentials into prompts. This hook blocks the prompt before it reaches the LLM. 70+ regex patterns cover AWS keys, Stripe tokens, PEM keys, credit card numbers (Luhn-validated), SSNs, and natural language disclosure ("my password is..."). |
| **Destructive Command Guard** | `PreToolUse` (Bash) | Claude sometimes generates `rm -rf /`, `mkfs`, or `dd` commands. This hook blocks them before execution. |
| **.env File Guard** | `PreToolUse` (Read, Edit, Write, Bash, Glob) | `.env` files contain secrets. This hook blocks all access — read, write, copy, pipe, source. Allows `.env.example` and existence checks (`ls`, `stat`). |
| **ESLint On-Save** | `PostToolUse` (Write, Edit) | Runs `eslint --fix` on every JS/TS file Claude writes. Remaining errors are fed back to Claude in the same turn for automatic correction. This means Claude's output is always lint-clean. |
| **Context Monitor** | `PostToolUse` | Parses the transcript JSONL to estimate context window consumption. Warns at 65% (consider compressing) and 75% (critical — compress immediately). Prevents quality degradation from context rot during long SDLC pipeline runs. |
| **Bell Notification** | `Stop` + `Notification` | Audio chime when Claude finishes or needs input. Quality of life for long-running tasks. |
| **Session Learnings** | `Stop` | Analyzes the session for repeated corrections ("I said X three times"), missed patterns, and behavioral gaps. Outputs a reminder to run `/learnings` to capture the improvement. |

### Why hooks instead of CLAUDE.md instructions?

CLAUDE.md instructions are **advisory** — Claude can ignore them under pressure or in edge cases. Hooks are **enforced** — they intercept at the tool level, before Claude's output reaches the filesystem or the user sees it. For security-critical behaviors (blocking secrets, preventing destructive commands), enforcement > advice.

### Architecture note: plugin-delivered hooks

Hooks are delivered via the plugin system through `hooks/hooks.json`. They apply to every project where the plugin is installed. This is intentional:
- A developer working on `project-service` and `whitelabel-app` gets the same security guardrails in both (assuming both install the plugin).
- Hooks use `${CLAUDE_PLUGIN_ROOT}` paths, so no manual copying to `~/hooks/` is needed.
- Plugin hooks are additive — projects can define their own hooks without conflict.

---

## 6. Layer 3: Skills — Methodology as Code

### What they are

Skills are markdown files (`skills/*/SKILL.md`) with YAML frontmatter that defines triggers, allowed tools, and context behavior. Claude auto-invokes them when conversation patterns match the `description:` field.

### Why 17 skills?

Each skill encodes a specific **methodology** that we've validated through multiple real projects:

**Core skills (5)** — Things every developer does daily:
- `code-review`: Ensures reviews check project-specific patterns (DynamoDB access, GraphQL resolvers, Capacitor plugins, theming) rather than generic "code looks good."
- `security-scan`: Goes beyond generic OWASP checks to include AWS IAM, Lambda, GraphQL-specific vulnerabilities.
- `generate-tests`: Supports both test-after and TDD modes. Generates from design specs (TDD) or existing code (test-after).
- `create-pr`: Enforces Jira ticket ID in branch, title, and body. Uses `gh` CLI. Follows standard PR template.
- `session-learnings`: Captures behavioral improvements (things Claude got wrong) and proposes CLAUDE.md updates.

**SDLC pipeline skills (8)** — Full feature lifecycle:
- See [Layer 5: SDLC Pipeline](#8-layer-5-sdlc-pipeline--full-lifecycle-automation).

**Supplementary skills (4)** — Specific workflows:
- `systematic-debugging`: Forces root cause investigation before fixes. Prevents the "change random things until it works" anti-pattern.
- `finishing-a-development-branch`: Pre-PR checklist — tests pass, no console.logs, no TODO comments, types complete.
- `writing-plans`: Structured planning for non-SDLC tasks (refactors, migrations, infra changes).
- `executing-plans`: Step-by-step plan execution with verification after each step.

### Skill architecture

```
skills/sdlc-requirements/
├── SKILL.md                       <- Core logic (~300 lines)
├── references/
│   └── interrogation-questions.md <- 115 questions across 15 categories
└── appendix/
    ├── evaluation.md              <- Self-evaluation criteria
    └── examples.md                <- Interaction flow examples
```

**Why this structure?**
- `SKILL.md` loads every time the skill is invoked. Must be concise.
- `references/` loads only when the skill needs specific data (e.g., "which questions should I ask about data privacy?").
- `appendix/` loads only for self-evaluation or when examples are needed.

This pattern reduced total skill context from ~505KB to ~120KB.

---

## 7. Layer 4: Agents — Isolated Execution

### What they are

Agent definitions (`agents/*.md`) configure Claude Code subagents — isolated processes with their own context windows and tool permissions.

### The 6 agents (and why each is an agent, not a skill)

| Agent | Why it needs isolation |
|-------|----------------------|
| **Code Reviewer** | Fresh context prevents confirmation bias. If the code reviewer shares context with the code writer, it's more likely to approve its own work. |
| **Security Auditor** | Same fresh-context rationale. Security review must be independent. |
| **Test Engineer** | Verbose output (generated test files) would pollute the main context. Isolation keeps the main session clean. |
| **PR Manager** | Runs `gh` CLI commands that produce large JSON output. Isolation prevents context bloat. |
| **Architect** | Read-only evaluation. Isolation ensures the architect can't accidentally modify code. |
| **DevOps Engineer** | CI/CD and infrastructure work often involves large YAML files. Isolation protects context. |

### Skills vs agents decision tree

```
Does it need fresh context (unbiased review)?     → Agent
Does it produce verbose output (tests, YAML)?     → Agent
Does it need conversation history?                → Skill
Does it need to share state with other phases?    → Skill
Is it a methodology (how to think)?               → Skill
Is it an execution task (do this specific thing)?  → Agent
```

---

## 8. Layer 5: SDLC Pipeline — Full Lifecycle Automation

### What it is

A 10-phase pipeline that takes a Jira ticket from requirements through PR creation:

```
[1] Requirements → [2] Architecture → [3] Design Review → [4] Impl Planning
     → [5] Implementation → [6] Simplify → [7] Review (parallel)
     → [8] Verification → [9] Risk → [10] PR Creation
```

### Why a pipeline?

Without it, developers use Claude for isolated tasks: "write this function," "add this test." The pipeline ensures:
1. **Requirements are captured** before code is written (prevents scope creep and rework).
2. **Architecture is designed** before implementation (prevents "refactor everything" PRs).
3. **Reviews happen automatically** (prevents "LGTM" rubber stamps).
4. **Verification is systematic** (prevents "it works on my machine").
5. **Risk is assessed** before merge (prevents "ship and pray").

### Operating model

| Mode | Use case |
|------|----------|
| Gated pipeline | The pipeline pauses after each phase for human approval. Engineer can redirect, modify artifacts, or abort. |
| Standalone (`/requirements`, `/architecture`, etc.) | Engineer only needs one specific phase. No orchestration needed. |

### Phase details

**Phase 1: Requirements (`sdlc-requirements`)**
- Uses plain text chat for structured interview (questions presented as formatted text, user types answers)
- 115 questions across 15 categories (functional, non-functional, security, backward compatibility...)
- Produces `problem_spec.md` (git-tracked, included in PR)
- Key innovation: **requires user confirmation** before writing the spec. Early versions auto-generated specs that didn't match user intent.

**Phase 2: Architecture (`sdlc-architecture`)**
- Reads the problem spec, explores the codebase
- Produces `design_spec.md` with component designs (COMP-###), ADRs, and data flows
- References project tech patterns (Lambda patterns, DynamoDB access patterns, GraphQL resolver patterns)

**Phase 3: Design Review (`sdlc-design-review`)**
- Scores the architecture across 6 dimensions (0-100)
- Gate decision: approve / approve_with_concerns / reject
- If rejected, loops back to Phase 2 with specific feedback

**Phase 4: Implementation Planning (`sdlc-impl-planning`)**
- Reads all prior artifacts and produces a self-contained `implementation_plan.md`
- Computes dependency graph, wave assignments, and file ordering
- Maps acceptance criteria to implementation files
- Provides enough context for a fresh session to execute without prior conversation history

**Phase 5: Implementation**
- Follows the implementation plan component-by-component
- **Wave-based execution** for 9+ files: topological sort by dependency, parallel Task tool dispatch per wave
- **Implementation safety rules**: test baseline first, test after each file change, never remove defaults
- **Mid-implementation resume**: `impl_state.json` tracks completion per file/wave

**Phase 6: Simplify (`simplify`)**
- Invokes the `/simplify` skill to auto-fix code quality, reuse, and efficiency issues
- Reviews all files changed during implementation
- Appends a `## Simplification` section to `impl_manifest.md`
- If nothing to fix, records "No issues found. Code was already clean."

**Phase 7: Review (parallel subagents)**
- Dispatches 3 subagents concurrently:
  - `spec-reviewer`: Spec compliance check (hard gate)
  - `test-engineer`: Test coverage and quality
  - `security-auditor`: Security vulnerabilities
- **Spec compliance gate**: First reviewer checks implementation against `problem_spec.md`. Hard blocker — 2-iteration loop-back cap.
- **Manifest validation**: Verifies all files from design spec exist and are non-empty.

**Phase 8: Verification (`sdlc-verify`)**
- Requirement coverage matrix: maps each requirement to implementation evidence
- **Wiring verification** (3-level): file exists → file has substantive content → code is actually wired/imported
- Quality findings (QF-###), security findings (SF-###)
- Weighted scoring (0-100)

**Phase 9: Risk Assessment (`sdlc-risk`)**
- Adversarial analysis: failure modes (FM-###), attack scenarios (ATK-###), blind spots (BS-###)
- Ship recommendation: `ship` / `ship_with_monitoring` / `no_ship`
- If `no_ship`, loops back to implementation with specific fixes

**Phase 10: PR Creation**
- Uses `create-pr` skill with Jira ticket ID enforcement
- Includes artifact digest in PR description
- Links to all spec artifacts in `docs/artifacts/<ticket>/`

### Loop-back logic

The pipeline isn't strictly linear. It has iteration loops:

- **Design review rejects** → Loop back to architecture (max 2 iterations)
- **Spec compliance fails** → Loop back to implementation (max 2 iterations)
- **Risk says no_ship** → Loop back to implementation (max 1 iteration)
- **Any phase exceeds max iterations** → HALT and ask user for guidance

---

## 9. Layer 6: MCP Servers — External Tool Integration

### What they are

Model Context Protocol servers that give Claude access to external tools. Defined in `.mcp.json` at the project root.

### The MCP server

| Server | Why we include it |
|--------|------------------|
| **Playwright** | Enables E2E test automation and browser interaction. Claude can take screenshots, fill forms, click elements — useful for the `generate-tests` skill in E2E mode. |

### Why just one?

Each MCP server adds startup latency and resource consumption. Playwright provides the highest value-to-cost ratio for E2E testing and browser automation. Sequential Thinking and Context7 were removed to reduce overhead — Claude's native reasoning and web search capabilities cover those use cases sufficiently.

### No auth required

Playwright runs locally via `npx` with no API keys or authentication. This is intentional — reducing onboarding friction. An engineer shouldn't need to register for a service to use the plugin.

---

## 10. Distribution Model

### Why native plugins?

We evaluated five distribution models:

| Model | Pros | Cons | Verdict |
|-------|------|------|---------|
| **Copy files into each project** | Simple, no external dependency | Stale copies everywhere, 95 files in every repo's Git history | Rejected |
| **Git submodule** | Pinned to commit, explicit update | Complex workflow, merge conflicts, most devs don't understand submodules | Rejected |
| **npm package** | Standard distribution, versioned | Requires a private registry, `node_modules` is the wrong location for `.claude/` | Rejected |
| **Symlink** (v1.x) | Instant updates, zero Git pollution | Replaces child repo's `.claude/`, preventing project-local customization | **Deprecated** |
| **Native plugin** (v2.0) | Namespaced, additive, versioned, no symlinks | Requires Claude Code plugin system support | **Default** |

### The plugin installation flow

```
/plugin marketplace add your-org/claude-master-plugin
/plugin install client-master@client-registry
```

What this does:
1. Registers the `client-registry` marketplace (GitHub-hosted)
2. Installs the `client-master` plugin, which delivers all hooks, skills, agents, commands, and MCP servers
3. Plugin skills are namespaced as `client-master:*` — no conflict with project-local skills
4. Hooks fire via `${CLAUDE_PLUGIN_ROOT}` paths — no machine-level installation needed

### Update model

```
/plugin update client-master@client-registry
```

Or teams can pin to a specific version via git tags in their project settings.

---

## 11. Context Window Management

### The problem

Claude Code has a finite context window (~200K tokens). A full SDLC pipeline run can consume 100K+ tokens across 10 phases. If context fills up, Claude's output quality degrades ("context rot") and eventually the session auto-compacts (losing earlier context).

### Our solution: 5 techniques

1. **LLM self-validation via Required Sections checklists.** Each artifact type has a checklist of required `##` headings. Skills validate artifacts by checking for these headings — no external scripts or JSON schemas needed. This keeps validation in-context and lightweight.

2. **Progressive disclosure.** SKILL.md files stay under 300 lines. Examples, scoring formulas, and evaluation criteria live in `appendix/` sub-files, loaded only when needed.

3. **Lazy reference loading.** Skills say "read `references/interrogation-questions.md` if you need more questions" instead of auto-loading all 115 questions upfront.

4. **Artifact digest.** After each pipeline phase, a compact `artifact-digest.md` is generated. Downstream phases read the digest first (~20 lines) and only load full artifacts when they need specific details.

5. **Subagent isolation.** Phases 6 (verification) and 7 (risk) run in Task tool subagents with their own context windows. This prevents verification's verbose output from consuming the main session's context.

### Context monitor hook

The `context-monitor.py` hook fires after every tool use, parses the transcript JSONL file, and estimates context consumption:
- **65% threshold (WARN):** "Consider compressing artifacts or delegating to subagents"
- **75% threshold (CRITICAL):** "Compress immediately or risk quality degradation"

This gives the pipeline (and the user) early warning before context rot sets in.

---

## 12. The Checkpoint System

### Two storage tiers

| Tier | Location | Git-tracked? | Purpose |
|------|----------|-------------|---------|
| **Spec artifacts** | `docs/artifacts/<ticket>/` | Yes | Included in PRs for human review. Contains problem_spec, design_spec, design_review. |
| **Execution artifacts** | `.claude/checkpoints/<ticket>/` | No (gitignored) | Ephemeral state: implementation manifest, verification report, risk assessment. |

### Why two tiers?

Spec artifacts are **documentation** — they explain what was designed and why. They belong in the PR for reviewer context.

Execution artifacts are **state** — they track what's been verified and what's at risk. They're session-specific and don't belong in Git history.

### Resume capability

```bash
/sdlc --ticket=TICKET-1234 --resume
```

The pipeline reads existing checkpoints and resumes from the last completed phase. This is critical for:
- **Session timeouts.** Long pipeline runs may exceed session limits.
- **Context compaction.** If the session compacts, a new session can resume with checkpoints as the starting context.
- **Mid-implementation crashes.** The `impl_state.json` tracks per-file completion within Phase 5.

### Artifact validation

All artifact types are Markdown files validated by **Required Sections checklists** — each skill checks that its output contains the expected `##` headings before saving. The `sdlc-checkpoint` skill holds the canonical checklist for all 7 artifact types and validates on save/load.

This lightweight approach replaces the previous JSON schema validation and catches missing sections early without loading external schema files into context.

---

## 13. Testing Strategy

### What's tested

| Component | Test type | Count | Framework |
|-----------|----------|-------|-----------|
| Prompt Scanner | Unit | 50+ | pytest |
| Destructive Command Guard | Unit | 40+ | pytest |
| .env File Guard | Unit | 50+ | pytest |
| ESLint On-Save | Unit | 30+ | pytest |
| Session Learnings | Unit | 30+ | pytest |
| Artifact Validator | Unit | 40+ | pytest |
| Skill Validator | Unit | 26 | pytest |
| **Total** | | **203+** | |

### What's NOT tested (and why)

- **Skills themselves.** Skills are markdown files — their correctness is validated by the SDLC pipeline's own design review and verification phases (dogfooding).
- **Agents.** Agent markdown is structural. Validated by the skill validator for frontmatter correctness.
- **MCP servers.** Third-party packages. We trust upstream testing. Our verification is "does it start without errors."
- **The pipeline end-to-end.** Tested via actual pipeline runs (e.g., the IMPROVEMENT-001 and TEST-001 artifacts in `docs/artifacts/`). E2E automation would require a Claude Code API that doesn't exist yet.

### Running tests

```bash
cd /path/to/claude-master-plugin
python3 -m pytest tests/ -v
```

---

## 14. Key Design Decisions (ADR Summary)

Full ADRs are in [docs/ARCHITECTURE.md](ARCHITECTURE.md). Summary:

| ADR | Decision | Key rationale |
|-----|----------|---------------|
| ADR-001 | Plugin as standalone Git repo | Centralized updates, no per-project duplication |
| ADR-002 | Skills over commands as primary extension | Auto-triggering reduces friction; `references/` structure enables rich context |
| ADR-003 | Least-privilege tool access | Explicit `allowed-tools:` lists; `Bash`/`Write` require security review |
| ADR-004 | `context: fork` for file-writing skills | Prevents generated code from polluting main conversation context |
| ADR-005 | No hardcoded org secrets | Project-level CLAUDE.md holds org-specific values; master is safe to share |
| ADR-006 | Progressive disclosure via `references/` | SKILL.md under 300 lines; detailed material loads on-demand |
| ADR-007 | Skills-based SDLC pipeline | 60-70% token reduction vs multi-agent; full prompt caching; deep methodology preserved |

---

## 15. Evolution History

### PR #1 — Foundation (Initial release)

- CLAUDE.md with org identity and conventions
- 5 hooks (prompt scanner, destructive guard, env guard, eslint-on-save, bell)
- 5 core skills (code-review, security-scan, generate-tests, create-pr, session-learnings)
- Plugin system (.claude-plugin/, marketplace.json)
- MCP servers (Sequential Thinking, Playwright, Context7)

### PR #2 — SDLC Pipeline

- 8 SDLC skills (requirements, architecture, design-review, impl-planning, verify, risk, checkpoint, pipeline)
- 8 JSON schemas for artifact validation
- 1 slash command (/sdlc)
- Checkpoint system (dual-tier storage)
- Bootstrap.sh and install-hooks.sh
- 203 unit tests

### PR #3 — Superpowers Integration

- 4 new skills (systematic-debugging, finishing-a-development-branch, writing-plans, executing-plans)
- TDD mode for generate-tests
- Progressive disclosure optimization (505KB → 120KB)
- Implementation safety rules from TICKET-3302
- Session learnings hook
- Backward compatibility checks in requirements phase

### PR #4 — Enforcement & Resilience

- **Spec compliance gate:** Hard blocker in Phase 6 review with 2-iteration loop-back
- **Manifest validation:** File existence + non-empty check post-implementation
- **Digest enforcement:** Staleness detection with auto-regeneration warning
- **Wiring verification:** 3-level check (existence → substantive → wired)
- **Context monitoring hook:** PostToolUse hook with 65%/75% threshold warnings
- **Wave-based parallel execution:** Topological sort + Task tool dispatch for 9+ files
- **Mid-implementation resume:** `impl_state.json` checkpoint per file/wave
- CLAUDE.md trimmed from 288 lines to ~100 lines (behavioral rules only)

### PR #5 — Native Plugin Distribution (v2.0, Current)

- **Removed symlink-based bootstrap** (`bootstrap.sh`, `install-hooks.sh`, `.claude/settings.json`)
- Moved `plugin.json` and `marketplace.json` to repo root (from `.claude-plugin/`)
- Added `context-monitor.py` to `hooks/hooks.json` (previously only via `install-hooks.sh`)
- New `scripts/setup-project.sh` replaces non-symlink parts of bootstrap
- New `CHANGELOG.md` with semver versioning, `docs/MIGRATION.md` for upgrade path
- All docs rewritten for `/plugin` commands — symlink references removed
- Plugin skills namespaced as `client-master:*`, enabling child repo customization

---

## Appendix: Walking Through a Pipeline Run

Here's what happens when an engineer runs `/sdlc --ticket=TICKET-5678`:

1. **Pipeline loads.** `sdlc-pipeline` SKILL.md activates. Reads `sdlc-checkpoint` for any existing state.

2. **Phase 1: Requirements.** Invokes `sdlc-requirements` via Skill tool. Claude asks structured questions via plain text chat. Engineer answers 8-15 questions by typing responses. Claude presents a draft summary. Engineer approves. `problem_spec.md` is written to `docs/artifacts/TICKET-5678/`.

3. **Gate pause.** Pipeline shows "Phase 1 complete. Approve to continue?" Engineer reviews the spec and approves.

4. **Phase 2: Architecture.** Invokes `sdlc-architecture`. Reads the problem spec, explores the codebase, designs components (COMP-001 through COMP-N). Writes `design_spec.md`.

5. **Gate pause.** Engineer reviews the architecture.

6. **Phase 3: Design Review.** Invokes `sdlc-design-review`. Scores the architecture. If < 60, rejects → loop back to Phase 2. If ≥ 60, approves.

7. **Gate pause.**

8. **Phase 4: Implementation Planning.** Invokes `sdlc-impl-planning`. Reads all prior artifacts, computes dependency graph and wave assignments, produces `implementation_plan.md`.

9. **Gate pause.**

10. **Phase 5: Implementation.** Reads implementation plan. For each component: creates/modifies files, runs tests after each change. For 9+ files: uses wave-based execution (topological sort, parallel dispatch). Tracks progress in `impl_state.json`.

11. **Gate pause.**

12. **Phase 6: Simplify.** Invokes `simplify` skill. Reviews all changed files for code quality, reuse, and efficiency issues. Auto-fixes what it finds. Appends results to `impl_manifest.md`.

13. **Gate pause.**

14. **Phase 7: Review.** Dispatches 3 parallel subagents. Spec compliance reviewer runs first (hard gate). Test engineer and security auditor run in parallel. Issues are aggregated.

15. **Gate pause.** Engineer reviews findings.

16. **Phase 8: Verification.** Runs in a Task tool subagent. Maps requirements to implementation. Checks wiring (3-level). Produces score.

17. **Phase 9: Risk.** Runs in a Task tool subagent. Adversarial analysis. Ship recommendation.

18. **Gate pause.** Final go/no-go from engineer.

19. **Phase 10: PR Creation.** Invokes `create-pr` skill. Branch name, PR title, and body all include `TICKET-5678`. Spec artifacts are committed to Git. PR is created via `gh`.

Total time: 15-45 minutes depending on feature complexity. Total token cost: ~100-200K (vs ~400-800K for multi-agent equivalent).
