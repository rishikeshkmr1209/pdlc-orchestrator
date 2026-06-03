# Onboarding Guide — Claude Master Plugin

This guide gets the plugin working in your project in under 5 minutes, covers every edge case, and ensures nothing breaks.

---

## Prerequisites Checklist

Run these checks before starting. Every item must pass.

```bash
# 1. Claude Code installed (v2.0+ required for plugin support)
claude --version
# Expected: claude 2.x.x or higher

# 2. Node.js 22+ (required by projects, also needed for MCP servers)
node --version
# Expected: v22.x.x

# 3. npx available (required for MCP server — Playwright)
npx --version
# Expected: any version

# 4. Python 3 (required for hook scripts — prompt scanner, env guard, eslint-on-save)
python3 --version
# Expected: Python 3.8+

# 5. gh CLI installed and authenticated (required for create-pr skill)
gh auth status
# Expected: "Logged in to github.com"

# 6. Git access to your organization
gh repo view your-org/claude-master-plugin --json name -q .name
# Expected: "claude-master-plugin"

# 7. ESLint in your project (optional — eslint-on-save hook auto-skips if not present)
npx eslint --version 2>/dev/null || echo "ESLint not found — eslint-on-save hook will be a no-op"
```

**If any check fails**, see [Troubleshooting](#troubleshooting) at the bottom.

---

## Installation

There are **three ways** to install the plugin. Choose based on your situation.

### Option A: Marketplace Install (after merge to `main`)

> **Use this when** the plugin has been merged to `main` on GitHub.

Inside a Claude Code session in your project:

```
/plugin marketplace add your-org/claude-master-plugin
/plugin install client-master@client-registry
```

Then restart Claude Code. Done.

**How it works:** Claude Code clones the **default branch** (`main`) from GitHub. If the plugin changes haven't been merged to `main` yet, this will fail or install an older version.

### Option B: Marketplace Install from Local Path

> **Use this when** the plugin is on a feature branch you've cloned locally but not yet merged to `main`.

```bash
# 1. Clone the repo and checkout the branch with plugin changes
git clone https://github.com/your-org/claude-master-plugin.git
cd claude-master-plugin
git checkout PLUGIN-001-native-plugin-refactor

# 2. Inside a Claude Code session, register the local path as marketplace source
claude plugin marketplace add /path/to/claude-master-plugin

# 3. Install the plugin
claude plugin install client-master@client-registry
```

Then restart Claude Code.

**How it works:** Instead of cloning from GitHub, Claude Code reads the marketplace from your local checkout. This lets you test plugin changes before merging.

### Option C: `--plugin-dir` Flag (quickest for testing)

> **Use this when** you want to test the plugin without installing it permanently.

```bash
# Launch Claude Code with the plugin loaded from a local directory
claude --plugin-dir /path/to/claude-master-plugin
```

**How it works:** The plugin is loaded for this session only. Nothing is cached or installed. Great for development and validation. You can point `--plugin-dir` at the branch checkout directly.

---

### What gets installed

Regardless of which option you choose, the plugin provides:

- **7 security hooks** (fire automatically on every prompt/tool call)
- **6 specialized agents** (code-reviewer, security-auditor, test-engineer, PR manager, architect, DevOps)
- **17 auto-invocable skills** (triggered by natural language or via `/skill-name`)
- **1 slash command** (`/client-master:sdlc`) — the SDLC pipeline entry point
- **1 MCP server** (Playwright)

### Team-wide Auto-Discovery

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

Commit this file. When a teammate opens Claude Code in the project, they'll be prompted to install the plugin.

> **Note:** This only works after the plugin is merged to `main` (Option A). For pre-merge testing, teammates should use Option B or C.

---

## Understanding Commands vs Skills

This is the most important concept to understand:

### Commands (slash commands)

- Invoked explicitly by typing `/command-name`
- Plugin commands are **namespaced**: `/client-master:sdlc`
- There is **1 command** in this plugin: `/client-master:sdlc`
- This is the entry point for the full SDLC pipeline

### Skills (auto-invocable)

- Triggered **automatically** when you describe what you want in natural language
- Also invocable explicitly via `/skill-name` in the autocomplete
- There are **17 skills** in this plugin
- Plugin skills show with `(client-master)` tag in autocomplete

### What you'll see in autocomplete

When you type `/sd` you'll see something like:

```
/sdlc-architecture           (client-master) Use when user says "design architecture"...
/sdlc-checkpoint             (client-master) Use when user says "save checkpoint"...
/sdlc-design-review          (client-master) Use when user says "review design"...
/sdlc-impl-planning          (client-master) Use when user says "plan implementation"...
/sdlc-pipeline               (client-master) Use when user says "run sdlc pipeline"...
/sdlc-requirements           (client-master) Use when user says "analyze requirements"...
/sdlc-risk                   (client-master) Use when user says "risk assessment"...
/sdlc-verify                 (client-master) Use when user says "verify implementation"...
/client-master:sdlc             (client-master) Run the full SDLC multi-agent pipeline...
```

- The first 8 are **skills** — individually invocable phases
- The last one (`/client-master:sdlc`) is the **command** — invokes the full pipeline orchestrator

### How to use them

**Run the full pipeline (recommended):**
```
/client-master:sdlc --ticket=TICKET-1234
```
This runs all 10 phases in sequence: Requirements → Architecture → Design Review → Impl Planning → Implementation → Simplify → Review → Verification → Risk Assessment → PR Creation.

**Run a single phase (standalone):**
```
# Just type naturally — the skill auto-triggers:
"analyze requirements for TICKET-1234"
"design architecture for TICKET-1234"
"review the design for TICKET-1234"

# Or invoke explicitly via autocomplete:
/sdlc-requirements
/sdlc-architecture
/sdlc-design-review
```

**Run non-SDLC skills:**
```
# These trigger on natural language:
"review this code"          → code-review skill
"security scan"             → security-scan skill
"write tests for this"      → generate-tests skill
"create a PR"               → create-pr skill
"capture learnings"         → session-learnings skill
```

---

## Project Setup

After installing the plugin, set up your project for the SDLC pipeline:

```bash
# Option A: Run the setup script (creates CLAUDE.md template + docs/artifacts/)
bash <plugin-path>/scripts/setup-project.sh

# Option B: Manual setup
mkdir -p docs/artifacts
echo '.claude/checkpoints/' >> .gitignore
```

Then customize the generated `CLAUDE.md`:

```markdown
# My Project — Claude Project Context

## Project Identity

**Repository:** my-project
**Jira prefix:** ILO

## Project-Specific Context

- **Primary stack:** TypeScript / Node.js
- **AWS region:** us-east-1
- **Key services:** ordering-service, payment-service
- **Team lead:** @your-github-handle

## SDLC Pipeline Usage

Run the full pipeline:
  /client-master:sdlc --ticket=TICKET-1234

Or use individual phase skills:
  "analyze requirements for TICKET-1234"
  "design architecture for TICKET-1234"
```

---

## Verify Everything Works

Run these checks in a Claude Code session to confirm the setup:

| # | Test | What to type | Expected result |
|---|------|-------------|-----------------|
| 1 | CLAUDE.md loaded | "What organization are you working for?" | Mentions CLIENT_ORG |
| 2 | Skills available | "review this file" (with a TS file open) | Runs code-review skill |
| 3 | Pipeline command | `/client-master:sdlc --ticket=TEST-001` | Starts pipeline orchestrator |
| 4 | Agents listed | "What agents do you have?" | Lists 6 agents (code-reviewer, security-auditor, etc.) |
| 5 | Schemas present | "list files in .claude/schemas/" | Shows 8 JSON schema files |
| 6 | MCP servers | "Use Playwright to take a screenshot" | Uses the MCP server |
| 7 | Hooks active | Paste a fake API key: `sk-test123abc` | Prompt scanner blocks it |

If any test fails, see [Troubleshooting](#troubleshooting).

---

## Updating the Plugin

```bash
# Inside a Claude Code session:
/plugin update client-master@client-registry

# Or check for updates:
/plugin list
```

Plugin updates are versioned with semver. See [CHANGELOG.md](../CHANGELOG.md) for release notes.

**Stale cache issue:** If you see outdated commands/skills after updating, clear the cache manually:

```bash
# Remove the cached plugin files
trash ~/.claude/plugins/cache/client-registry/client-master/

# Then uninstall and reinstall:
claude plugin uninstall client-master@client-registry
claude plugin marketplace update client-registry
claude plugin install client-master@client-registry
```

---

## How It Works

```
Your Project                          Plugin (installed by Claude Code)
============                          ==================================
.claude/settings.json                 claude-master-plugin/
  └── enabledPlugins:                   ├── .claude-plugin/
       client-master@client-registry = true       │   ├── marketplace.json (catalog)
                                        │   └── plugin.json      (manifest)
                                        ├── skills/     (17 skills)
                                        ├── agents/     (6 agents)
                                        ├── commands/   (1 command: sdlc.md)
                                        ├── hooks/
                                        │   ├── hooks.json  (hook wiring)
                                        │   └── *.py / *.sh (7 hook scripts)
                                        ├── .claude/
                                        │   └── schemas/    (8 JSON schemas)
                                        └── .mcp.json       (1 MCP server)

CLAUDE.md (committed — your project context)
docs/artifacts/<ticket>/  (committed — specs for PR review)
.claude/checkpoints/<ticket>/  (gitignored — ephemeral state)
```

**Key design:** Plugin skills are namespaced as `client-master:*` (e.g., `client-master:code-review`). Your project can have its own `.claude/skills/` without conflict.

---

## Available Skills Reference

### Core Skills (auto-trigger on natural language)

| Natural language trigger | Skill name | What it does |
|---------|-------------|-------------|
| "review this code" | `code-review` | JS/TS quality review against project standards |
| "security scan" | `security-scan` | OWASP + AWS + PII security check |
| "write tests" | `generate-tests` | Jest unit + Playwright E2E |
| "create a PR" | `create-pr` | Standard PR via `gh` CLI |
| "capture learnings" | `session-learnings` | Captures session patterns for CLAUDE.md updates |
| "plan this" | `writing-plans` | Multi-step implementation plan |
| "execute the plan" | `executing-plans` | Execute a written plan from `.claude/plans/` |
| "debug this" | `systematic-debugging` | Structured debugging workflow |
| "I'm done, ready for PR" | `finishing-a-development-branch` | Pre-PR readiness check |

### SDLC Pipeline Skills

| Natural language trigger | Skill name | What it does |
|---------|-------------|-------------|
| "run sdlc pipeline" | `sdlc-pipeline` | Full 10-phase pipeline orchestrator |
| "analyze requirements" | `sdlc-requirements` | Deep requirements interrogation |
| "design architecture" | `sdlc-architecture` | Technical design with ADRs |
| "review design" | `sdlc-design-review` | Quality gate (approve/reject) |
| "plan implementation" | `sdlc-impl-planning` | Implementation planning with wave/dependency graph |
| "verify implementation" | `sdlc-verify` | Verification with coverage matrix |
| "risk assessment" | `sdlc-risk` | Adversarial risk analysis |
| "save checkpoint" | `sdlc-checkpoint` | Manage pipeline state |

### SDLC Pipeline Command

```
/client-master:sdlc --ticket=TICKET-ID [--resume] [--from=phase]
```

| Flag | Description |
|------|-------------|
| `--ticket=TICKET-1234` | Jira ticket ID (required) |
| `--resume` | Resume from last checkpoint |
| `--from=phase` | Start from specific phase (requirements, architecture, design-review, impl-planning, implementation, simplify, review, verification, risk, pr) |

The pipeline runs in gated mode and does not accept a `--mode` flag.

---

## Migrating from v1.x (symlink bootstrap)

If you previously used `bootstrap.sh` or `install-hooks.sh`, see [MIGRATION.md](MIGRATION.md) for the step-by-step upgrade guide.

---

## Troubleshooting

### Prerequisites

**"claude: command not found"**
```bash
npm install -g @anthropic/claude-code
```

**"node: command not found" or wrong version**
```bash
nvm install 22
nvm use 22
```

**"python3: command not found"**
```bash
# macOS (usually pre-installed)
xcode-select --install
# Or via Homebrew
brew install python@3
```

Hooks require Python 3. Without it: prompt scanner, env guard, eslint-on-save, and session learnings won't work. Bell notification (Bash-based) still works.

**"gh: command not found"**
```bash
brew install gh
gh auth login
```

Without `gh`: `create-pr` skill fails. Everything else works.

### Plugin Issues

**"Plugin not found" or "marketplace not registered"**
```bash
# Re-register the marketplace:
/plugin marketplace add your-org/claude-master-plugin
# Then install:
/plugin install client-master@client-registry
```

**"Marketplace file not found" when using GitHub source**

This means the plugin hasn't been merged to `main` yet. Use Option B (local path) or Option C (`--plugin-dir`) instead:
```bash
# Option B:
git clone https://github.com/your-org/claude-master-plugin.git
cd claude-master-plugin && git checkout PLUGIN-001-native-plugin-refactor
claude plugin marketplace add /path/to/claude-master-plugin
claude plugin install client-master@client-registry

# Option C (simplest):
claude --plugin-dir /path/to/claude-master-plugin
```

**Skills not triggering**
- Restart Claude Code after plugin installation
- Verify the plugin is enabled: `/plugin list`

**Stale commands/skills after update**
- Clear the plugin cache: `trash ~/.claude/plugins/cache/client-registry/`
- Uninstall and reinstall the plugin

**MCP server failed to start**
```bash
# Ensure npx is in PATH
which npx
# Test MCP server manually:
npx -y @playwright/mcp
```

**Hooks not firing**
- Restart Claude Code after plugin installation
- Verify the plugin is listed and enabled: `/plugin list`
- Hooks fire from `${CLAUDE_PLUGIN_ROOT}` paths — they don't need manual path configuration

**ESLint On-Save errors**
The hook auto-skips if ESLint isn't installed in the project. This is expected for non-JS projects.

### Platform-Specific Issues

**macOS: Port 5000 conflict**
AirPlay Receiver uses port 5000. Disable in System Preferences > General > AirDrop & Handoff.

**Windows / WSL**
Ensure Python 3 is available: `sudo apt install python3`

**Corporate Proxy / VPN**
```bash
npm config set proxy http://your-proxy:port
npm config set https-proxy http://your-proxy:port
```

---

## Uninstalling

```bash
# Inside a Claude Code session:
/plugin uninstall client-master@client-registry

# Remove auto-discovery from .claude/settings.json (if added)
# Remove SDLC directories if no longer needed
```

---

## Getting Help

- **Slack:** `#platform-claude-plugin` (internal)
- **GitHub Issues:** open an issue in `claude-master-plugin`
- **Docs:** [HOOKS.md](HOOKS.md), [STANDARDS.md](STANDARDS.md), [ARCHITECTURE.md](ARCHITECTURE.md)
- **Migration:** [MIGRATION.md](MIGRATION.md)
- **Contributing:** see [CONTRIBUTING.md](../CONTRIBUTING.md)
