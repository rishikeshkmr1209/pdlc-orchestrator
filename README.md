# CLIENT_ORG — Claude Master Plugin

A centralized, version-controlled Claude Code plugin for all CLIENT_ORG engineering teams. Ships security guardrails, specialized agents, auto-invocable skills, a full SDLC pipeline, and MCP servers — all installable with two commands.

**Maintained by:** Platform Engineering team
**Stack:** TypeScript / JavaScript, Node.js, GitHub Actions, AWS

---

## Quick Start (2 commands)

Inside a Claude Code session:

```
/plugin marketplace add your-org/claude-master-plugin
/plugin install client-master@client-registry
```

That's it. Restart Claude Code. Everything is ready — hooks, agents, skills, MCP servers, SDLC pipeline.

> **New to this plugin?** Read the full [Onboarding Guide](docs/ONBOARDING.md) for prerequisites, edge cases, and verification steps.

### Alternative: Team-wide Auto-Discovery

Add to your project's `.claude/settings.json` so all engineers are prompted to install on first open:

```json
{
  "extraKnownMarketplaces": {
    "client-registry": {
      "source": { "source": "github", "repo": "your-org/claude-master-plugin" }
    }
  },
  "enabledPlugins": { "client-master@client-registry": true }
}
```

### Project Setup

After installing the plugin, run the setup script to create a CLAUDE.md template and SDLC directories:

```bash
bash <plugin-path>/scripts/setup-project.sh
```

---

## What's Included

### Hooks (7 scripts across 6 events)

Hooks fire automatically via the plugin system — no manual installation needed.

| Hook | Event | What it does |
|------|-------|-------------|
| **Prompt Scanner** | `UserPromptSubmit` | Blocks prompts containing API keys, credentials, credit cards (Luhn), SSNs, JWTs, PEM keys before they reach the LLM |
| **Destructive Command Guard** | `PreToolUse` (Bash) | Blocks `rm -rf /`, `mkfs`, `dd` on block devices, fork bombs, and other irreversible commands |
| **.env File Guard** | `PreToolUse` (Read, Edit, Write, Bash, Glob) | Blocks all access to `.env` files; allows `.env.example/.sample/.template` |
| **ESLint On-Save** | `PostToolUse` (Write, Edit) | Runs `eslint --fix` on every JS/TS file written; feeds errors back for auto-correction |
| **Context Monitor** | `PostToolUse` | Tracks context window consumption; warns at 65% (compress) and 75% (critical) thresholds |
| **Bell Notification** | `Stop` + `Notification` | Audio chime when Claude finishes or needs input |
| **Session Learnings** | `Stop` | Detects repeated corrections and suggests CLAUDE.md updates |

### Agents (6 specialized subagents)

Claude invokes these automatically based on task context, or you can request them directly.

| Agent | Specialization |
|-------|---------------|
| **Code Reviewer** | JS/TS code quality, types, patterns, project conventions |
| **Security Auditor** | OWASP Top 10, secrets detection, AWS IAM hardening |
| **Test Engineer** | Jest unit tests, Playwright E2E, coverage strategy |
| **PR Manager** | PR lifecycle via `gh` CLI — create, update, merge |
| **Architect** | Architecture review, ADR writing, design evaluation |
| **DevOps Engineer** | GitHub Actions, CDK/SAM, AWS infrastructure |

### Skills (17 auto-invocable)

Skills activate automatically when trigger phrases match. No slash command needed.

**Core Skills:**

| Skill | Triggers | What it does |
|-------|----------|-------------|
| `code-review` | "review this code", "check my code" | JS/TS quality against project standards |
| `security-scan` | "security scan", "check for vulnerabilities" | OWASP Top 10, secrets, AWS IAM |
| `generate-tests` | "write tests", "add unit tests", "TDD" | Jest unit + Playwright E2E (test-after and TDD modes) |
| `create-pr` | "create a PR", "open pull request" | project-standard PR via `gh` CLI |
| `session-learnings` | "capture learnings", `/learnings` | Captures session patterns for CLAUDE.md updates |

**SDLC Pipeline Skills (full feature lifecycle):**

| Skill | Triggers | What it does |
|-------|----------|-------------|
| `sdlc-pipeline` | "run sdlc pipeline", `/sdlc` | Orchestrates all 10 phases end-to-end |
| `sdlc-requirements` | "analyze requirements", `/requirements` | Deep requirements interrogation with 40+ question categories |
| `sdlc-architecture` | "design architecture", `/architecture` | Architecture design with ADR generation |
| `sdlc-design-review` | "review design", `/design-review` | Quality gate with approve/reject scoring |
| `sdlc-qa-test-generation` | "generate qa tests", "phase 3b qa", `/qa-test-generation` | Phase 3b: generates QA test plan, creates Jira Test issues linked to ACs, opens regression-automation PR in `qa-automation`. Runs in parallel with `sdlc-design-review` for Large Feature; runs after `sdlc-architecture` for Small Feature. Requires the user's globally-configured Atlassian MCP and a local checkout of `qa-automation` (path via `QA_AUTOMATION_PATH`). Auto-clones `platform-knowledge` if missing (path via `PLATFORM_KNOWLEDGE_PATH`). |
| `sdlc-impl-planning` | "plan implementation", `/impl-planning` | Implementation planning with wave/dependency graph |
| `sdlc-verify` | "verify implementation", `/verify` | Verification with requirement coverage matrix and wiring checks |
| `sdlc-risk` | "risk assessment", `/risk` | Adversarial risk analysis with ship/no-ship recommendation |
| `sdlc-checkpoint` | "save checkpoint", `/checkpoint` | Manage pipeline checkpoints |

**Supplementary Skills:**

| Skill | Triggers | What it does |
|-------|----------|-------------|
| `systematic-debugging` | "debug this", "why is this failing" | Root cause investigation before fixes (4-phase process) |
| `finishing-a-development-branch` | "ready to create PR", "feature complete" | Pre-PR quality gate with project checklist |
| `writing-plans` | "plan this", "break this down" | Structured planning for non-SDLC multi-step tasks |
| `executing-plans` | "execute the plan", "start the plan" | Step-by-step plan execution with verification |

### Slash Command (pipeline entry point)

The plugin provides **1 slash command** (`/client-master:sdlc`) as the pipeline entry point. All other features are **auto-invocable skills** triggered by natural language or via `/skill-name` in autocomplete:

```
/client-master:sdlc --ticket=X   Run full SDLC pipeline
```

### MCP Servers (1 project-scoped, no auth required)

Auto-loaded when the plugin is enabled. Runs locally via `npx`.

| Server | Package | What it does |
|--------|---------|-------------|
| **Playwright** | `@playwright/mcp` | Browser automation via accessibility snapshots |

---

## SDLC Pipeline

Full-lifecycle feature development automation: requirements through PR creation in 10 phases.

```
[1] Requirements → [2] Architecture → [3] Design Review → [4] Impl Planning
     → [5] Implementation → [6] Simplify → [7] Review (parallel)
     → [8] Verification → [9] Risk → [10] PR Creation
```

**Controls:**
- Gated execution is the default behavior; approvals happen after each phase
- `--resume` — Restart from last saved checkpoint
- `--from=<phase>` — Start from a specific phase

**Artifacts:**
- `docs/artifacts/<ticket>/` — Git-tracked specs (problem_spec, design_spec, design_review) — included in PRs
- `.claude/checkpoints/<ticket>/` — Ephemeral execution artifacts (gitignored)

---

## Repository Structure

```
claude-master-plugin/
├── .claude-plugin/
│   ├── plugin.json               <- Plugin manifest (name, version, author)
│   └── marketplace.json          <- Marketplace catalog ($schema, plugins list)
├── agents/                       <- 6 specialized subagents
├── commands/                     <- 1 slash command (/sdlc)
├── skills/                       <- 17 auto-invocable skills
├── hooks/
│   ├── hooks.json                <- Plugin hook wiring (${CLAUDE_PLUGIN_ROOT})
│   ├── scan-prompt.py            <- Prompt scanner (secrets, PII, IP)
│   ├── guard-destructive-commands.py
│   ├── guard-env-files.py
│   ├── eslint-on-save.py
│   ├── context-monitor.py
│   ├── session-learnings-check.py
│   └── notify-bell.sh
├── .claude/
│   ├── checkpoints/              <- Execution artifacts (gitignored)
│   ├── statusline-script.sh     <- Status bar customization
│   ├── commands -> ../commands   <- Symlink (local dev only)
│   ├── agents -> ../agents       <- Symlink (local dev only)
│   └── skills -> ../skills       <- Symlink (local dev only)
├── .mcp.json                     <- MCP server definitions
├── scripts/
│   ├── setup-project.sh          <- Project setup (CLAUDE.md + SDLC dirs)
│   └── validate-skills.py        <- Skill/agent YAML validator
├── docs/
│   ├── ONBOARDING.md             <- Step-by-step setup guide
│   ├── MIGRATION.md              <- v1.x → v2.0 migration guide
│   ├── HOOKS.md                  <- Hook documentation and troubleshooting
│   ├── STANDARDS.md              <- Naming and coding conventions
│   ├── ARCHITECTURE.md           <- Architecture overview and ADRs
│   ├── SECURITY-REVIEW.md        <- Security review process
│   └── WIKI.md                   <- Full solution rationale and walkthrough
├── templates/
│   ├── skill-template/SKILL.md   <- Template for new skills
│   └── agent-template.md         <- Template for new agents
├── CLAUDE.md                     <- Master context (org identity, conventions, rules)
├── CHANGELOG.md                  <- Release notes with semver versioning
└── CONTRIBUTING.md               <- Contribution process
```

---

## Project-Level Customization

After plugin installation, run `setup-project.sh` and customize the generated `CLAUDE.md`:

```markdown
# My Service — Claude Project Context

## Project-Specific Context
- Service: my-ordering-service
- AWS Region: us-east-1
- Jira prefix: TICKET
- Key dependencies: Express 4, Zod, Prisma
```

---

## Updating

```bash
# Plugin updates are managed via Claude Code:
/plugin update client-master@client-registry

# Or pin to a specific version via git tag in your settings
```

---

## Migrating from v1.x (symlink bootstrap)

If you previously used `bootstrap.sh` or `install-hooks.sh`, see [docs/MIGRATION.md](docs/MIGRATION.md) for the step-by-step upgrade guide.

---

## Contributing

All teams are welcome to contribute. See [CONTRIBUTING.md](CONTRIBUTING.md) for the full process.

**Quick summary:**
1. Use templates in `templates/`
2. Follow conventions in `docs/STANDARDS.md`
3. Open a PR with 2 approvals (1 from a core maintainer)
4. Skills with `Bash` or `Write` access require security review

---

## Support

- **Onboarding guide:** [docs/ONBOARDING.md](docs/ONBOARDING.md)
- **Migration guide:** [docs/MIGRATION.md](docs/MIGRATION.md)
- **Hook docs:** [docs/HOOKS.md](docs/HOOKS.md)
- **Solution rationale:** [docs/WIKI.md](docs/WIKI.md)
- **Issues:** open a GitHub issue in this repo
- **Slack:** `#platform-claude-plugin` (internal)
- **Maintainers:** Platform Engineering team
