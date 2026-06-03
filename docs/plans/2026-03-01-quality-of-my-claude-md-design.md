# Design: `quality-of-my-claude-md` Skill

**Date:** 2026-03-01
**Status:** Approved
**Research Basis:** [ETH Zurich — Evaluating AGENTS.md](https://arxiv.org/abs/2602.11988) | [AGENTBench](https://github.com/eth-sri/agentbench)

---

## Problem Statement

Context files (CLAUDE.md, agents.md, copilot-instructions.md) are intended to help AI coding agents understand a codebase. However, ETH Zurich research shows:

- **Auto-generated files reduce success rates ~2%** and increase inference costs 20%+
- **Developer-written files help ~4%** but still increase costs
- Agents follow instructions too literally — convention overload makes primary tasks harder
- Some models become "anxious," repeatedly re-reading context files
- Well-documented repos gain little; poorly documented repos gain a lot

**The best context file contains only information the agent cannot get elsewhere.**

This skill evaluates existing context files against these findings and produces actionable recommendations.

---

## Execution Modes

User selects at runtime via flag:

| Flag | Mode | Description | Time |
|------|------|-------------|------|
| `--quick` | Pattern Linter | Static anti-pattern detection only | ~30s |
| `--deep` | Multi-Phase Audit | Full codebase probing + scoring | ~3-5min |
| `--benchmark` | Comparative Benchmark | Run sample tasks with/without file, measure token/step delta | ~10-15min |
| *(default)* | Smart Hybrid | Quick scan first, then targeted deep probes for flagged items | ~2-3min |

---

## Architecture: 6-Phase Pipeline

```
┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  1. Discovery │───▶│ 2. Static Analysis│───▶│ 3. Active Probing│
│  Find & parse │    │  Anti-patterns    │    │  Codebase checks │
└──────────────┘    └──────────────────┘    └──────────────────┘
                                                      │
┌──────────────┐    ┌──────────────────┐    ┌─────────▼────────┐
│  6. Output    │◀───│  5. Scoring       │◀───│ 4. Benchmark     │
│  3 formats    │    │  6 dimensions     │    │  (optional)      │
└──────────────┘    └──────────────────┘    └──────────────────┘
```

### Phase 1: Discovery

- Locate all context files in the repo:
  - `CLAUDE.md` (any directory level)
  - `agents.md` / `AGENTS.md`
  - `.github/copilot-instructions.md`
  - `.cursorrules`, `.windsurfrules`
  - User home `~/.claude/CLAUDE.md` (global instructions)
- Parse each file into discrete **instruction blocks** (by heading section or bullet point)
- Classify each block by type:

| Type | Description | Example |
|------|-------------|---------|
| `convention` | Code style/formatting rule | "Use camelCase for variables" |
| `forbidden-action` | Something the agent must never do | "Never force-push to main" |
| `architecture` | System design / structure info | "Monorepo with 3 workspaces" |
| `tooling` | Tool/framework specifications | "Use Jest for testing" |
| `workflow` | Process/procedure instruction | "Run tests before committing" |
| `guardrail` | Safety/security boundary | "Never commit .env files" |
| `boilerplate` | Org identity, mission, filler | "We are a global QSR company" |

### Phase 2: Static Analysis (Anti-Pattern Detection)

Score each instruction block against research-backed anti-patterns:

| # | Anti-Pattern | Research Source | Detection Method |
|---|---|---|---|
| 1 | **Redundancy** | "restates what agent can see" | Check if instruction duplicates info in README, package.json, tsconfig, eslint, prettier configs |
| 2 | **Anxiety Induction** | GPT-5.1 Mini re-reads context obsessively | Detect overly broad rules, vague instructions, excessive "always"/"never" without specifics |
| 3 | **Convention Overload** | "Added overhead makes primary task harder" | Count total convention-type instructions; flag when >15 formatting/style rules |
| 4 | **Non-Actionable Boilerplate** | "Noise rather than signal" | Detect org mission statements, philosophy sections, history with no actionable content |
| 5 | **Discoverable Info** | "Well-documented repos don't need this" | Info already in config files, README, or standard tool output |
| 6 | **Verbose Instructions** | Cost finding: 20%+ inference increase | Measure word count per instruction; flag verbose blocks that could be terse |
| 7 | **Missing Guardrails** | "Focus on guardrails, not overviews" | Check for absence of critical guardrails (secrets, force-push, test requirements) |
| 8 | **Stale Instructions** | Practical addition | Instructions referencing files, tools, or deps that don't exist in the repo |

### Phase 3: Active Codebase Probing (Deep + Benchmark modes)

For each instruction block flagged as potentially redundant:

1. **Config file overlap** — grep tsconfig.json, .eslintrc, .prettierrc, package.json, pyproject.toml, pom.xml for the same setting
2. **README overlap** — compare instruction text against README.md content for duplication
3. **File existence check** — verify referenced files/paths actually exist in the repo
4. **Dependency verification** — verify mentioned packages exist in dependency manifests
5. **Test framework detection** — auto-detect test frameworks from config/deps vs what's specified in context file
6. **CI/CD overlap** — compare instructions against `.github/workflows/` for duplicated rules
7. **Linter/formatter config overlap** — check if style rules are already enforced by tooling config

### Phase 4: Comparative Benchmark (Benchmark mode only)

1. Identify a simple, self-contained task in the repo (e.g., "add a unit test for an existing function" or "fix a linting error")
2. **Run A:** Execute task WITH the full context file — capture token count, step count, success/failure
3. **Run B:** Execute task with minimal/stripped context file — capture same metrics
4. **Calculate delta:**
   - Token overhead % = `(A_tokens - B_tokens) / B_tokens * 100`
   - Step overhead % = `(A_steps - B_steps) / B_steps * 100`
   - Success rate change = `B_success - A_success`
5. Report whether the context file helped, hurt, or was neutral for the measured task

### Phase 5: Scoring (6 Dimensions)

| Dimension | Weight | Scale | What It Measures |
|---|---|---|---|
| **Signal-to-Noise Ratio** | 25% | 0-100 | % of instructions that provide unique, non-discoverable value |
| **Redundancy Score** | 20% | 0-100 | Inverse of % instructions duplicated in configs/README/CI |
| **Specificity** | 20% | 0-100 | How actionable and specific vs vague instructions are |
| **Guardrail Coverage** | 15% | 0-100 | Presence of critical safety guardrails |
| **Conciseness** | 10% | 0-100 | Word efficiency; penalizes verbose instruction blocks |
| **Freshness** | 10% | 0-100 | % of instructions referencing valid, existing entities |

**Overall Grade:** Weighted average mapped to letter grade:

| Range | Grade |
|-------|-------|
| 90-100 | A |
| 80-89 | B |
| 70-79 | C |
| 60-69 | D |
| <60 | F |

### Phase 6: Output (3 Formats)

All three formats are produced in sequence:

**Format 1: Score Card**

```
## CLAUDE.md Quality Report
Overall Grade: B+ (78/100)

| Dimension        | Score | Notes                           |
|------------------|-------|---------------------------------|
| Signal-to-Noise  | 65    | 12 of 34 instructions redundant |
| Redundancy       | 70    | 8 overlap with eslint/prettier  |
| Specificity      | 85    | Most rules are actionable       |
| Guardrails       | 90    | Good coverage                   |
| Conciseness      | 72    | 5 verbose sections              |
| Freshness        | 85    | 2 stale references              |

Key Findings:
- 35% of instructions are discoverable from existing config files
- 3 instructions reference files that no longer exist
- Missing guardrail: no mention of secrets/credential handling
```

**Format 2: Line-by-Line Audit**

Interactive walkthrough of each instruction block with:
- **Verdict:** `KEEP` | `REMOVE` | `REVISE` | `ADD`
- **Evidence:** Why (e.g., "Already in .prettierrc line 3", "References non-existent file X")
- **Confidence:** High / Medium / Low

**Format 3: Proposed Diff**

A clean diff of the optimized file with inline justification comments:

```diff
- ## Organization Identity
- You are assisting engineers at CLIENT_ORG...
+ # (REMOVED: Non-actionable boilerplate — agent doesn't need org identity to code)

  ## Forbidden Actions
  - Never force-push to main  # KEEP: Critical guardrail, not discoverable
- - Use camelCase for variables  # REMOVE: Already in .eslintrc naming-convention rule
```

---

## Supported Ecosystems

The skill works across these ecosystems by checking their respective config files:

| Ecosystem | Config Files Checked |
|---|---|
| **Node.js / TypeScript** | package.json, tsconfig.json, .eslintrc*, .prettierrc*, jest.config.*, .npmrc |
| **Python** | pyproject.toml, setup.cfg, setup.py, .flake8, .pylintrc, pytest.ini, tox.ini, requirements.txt |
| **Java** | pom.xml, build.gradle, checkstyle.xml, .editorconfig |
| **General** | README.md, .github/workflows/*, .editorconfig, .gitignore, Makefile, Dockerfile |

---

## Skill Metadata

- **Name:** `quality-of-my-claude-md`
- **Type:** Terminal (standalone, no chaining)
- **Allowed Tools:** Read, Grep, Glob, Bash, Write, AskUserQuestion, Agent
- **Trigger Phrases:** "evaluate claude.md", "audit my agents.md", "check claude.md quality", "is my CLAUDE.md helping", "optimize my context file"
- **Location:** `skills/quality-of-my-claude-md/SKILL.md`

---

## Key Design Decisions

1. **Standalone skill** — produces report but does not auto-apply changes. User applies manually or via `claude-md-improver`.
2. **All 3 modes combined** — user selects via flag at runtime; default is smart hybrid.
3. **Research-grounded scoring** — every anti-pattern maps to a finding from the ETH Zurich paper.
4. **Multi-ecosystem** — works for Node.js, Python, Java, and general repos by checking ecosystem-specific configs.
5. **Active probing** — doesn't just lint the text; actually checks the codebase to verify redundancy claims.
