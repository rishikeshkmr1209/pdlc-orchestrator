# Claude Code Hooks — Claude Master Plugin

Claude Code hooks are shell commands that fire automatically in response to
specific events during a Claude session. This plugin ships seven hooks:

| Hook | Event | Purpose |
|---|---|---|
| Prompt Scanner | `UserPromptSubmit` | Blocks prompts containing secrets, credentials, or PII before they reach the LLM |
| Destructive Command Guard | `PreToolUse` (Bash) | Blocks irreversible shell commands before execution |
| .env File Guard | `PreToolUse` (Read, Edit, Write, Bash, Glob) | Blocks access to `.env` files containing secrets |
| ESLint On-Save | `PostToolUse` (Write + Edit) | Auto-fixes lint errors; feeds remaining errors back to Claude |
| Context Monitor | `PostToolUse` | Tracks context window consumption; warns at 65%/75% thresholds |
| Bell Notification | `Stop` + `Notification` | Audio cue when Claude finishes or needs input |
| Session Learnings | `Stop` | Detects repeated corrections and suggests CLAUDE.md updates |

---

## Installation

Hooks are delivered automatically via the plugin system. Install the plugin:

```
/plugin marketplace add your-org/claude-master-plugin
/plugin install client-master@client-registry
```

Then **restart Claude Code**. Hooks fire automatically from `${CLAUDE_PLUGIN_ROOT}` paths.

---

## How the Hooks Work

### Prompt Scanner (`UserPromptSubmit`)

Fires on **every user prompt, before it is dispatched to the LLM** — this is
the only hook event that intercepts the prompt at the pre-LLM stage.

**Why here and not in the LLM system prompt?** A system prompt instruction
("don't log PII") runs *after* the data has already been sent. This hook runs
*before* — the data never reaches the network if it's blocked.

**Zero dependencies.** The script is pure Python 3 with no pip installs,
so it works in any environment without setup.

**The two-level response:**

| Severity | Action | Exit code | Use case |
|---|---|---|---|
| `BLOCK` | Prompt suppressed, error shown to user | `2` | High-confidence credentials and PII |
| `WARN` | Prompt sent, warning shown | `0` | Ambiguous PII that may be intentional (e.g., test emails) |

**What is detected:**

| Category | Examples |
|---|---|
| AWS credentials | Access Key IDs (`AKIA*`), Secret Access Keys (contextual) |
| Azure credentials | Storage Account Keys (`AccountKey=…`), SAS tokens |
| Google / GCP | API Keys (`AIza…`), OAuth client secrets |
| GitHub / GitLab tokens | Classic PATs (`ghp_…`), fine-grained PATs, GitLab (`glpat-…`) |
| AI platform keys | Anthropic (`sk-ant-…`), OpenAI (`sk-…`) |
| Payment credentials | Stripe live/test keys, Square, PayPal/Braintree |
| Messaging / Comms | Slack tokens + webhooks, SendGrid, Mailgun, Mailchimp |
| Package registry | npm (`npm_…`), PyPI (`pypi-…`), Docker Hub (`dckr_pat_…`) |
| Cryptographic keys | PEM private key blocks |
| Auth tokens | JWTs (3-part base64url), Bearer tokens in Authorization headers |
| Database URLs | Connection strings with embedded passwords |
| PII — Identity | US SSN, ITIN (Luhn-validated credit cards handled separately) |
| PII — Payment | Credit card numbers (all major networks, Luhn-validated) |
| PII — Contact (warn) | Email addresses, US/intl phone numbers |
| Network (warn) | IPv4 addresses (policy: use project IP library) |
| Weak assignments (warn) | Hardcoded `password=`, `secret=`, `api_key=` (non-placeholder values) |

**Configuration via `PROMPT_SCANNER_MODE` environment variable:**

```bash
# Standard (default): block credentials + CC/SSN; warn for emails/phones/IPs
export PROMPT_SCANNER_MODE=standard

# Strict: block everything including warn-level findings
export PROMPT_SCANNER_MODE=strict

# Audit: log all findings to stderr but never block (useful for tuning)
export PROMPT_SCANNER_MODE=audit
```

Set this in your shell profile (`~/.zshrc`) or in a project `.env`.

**Sample blocked output:**

```
────────────────────────────────────────────────────────────────────
  Prompt Scanner — BLOCKED
────────────────────────────────────────────────────────────────────

Your prompt was NOT sent to the model because it appears to contain
sensitive data. Review and redact before retrying.

  [BLOCK]  Cloud Credential
           AWS Access Key ID — AKIAXXX***
  [BLOCK]  PII — Payment
           Credit Card Number — 4111*** (Luhn-valid)
```

---

### Destructive Command Guard (`PreToolUse` on Bash)

Every time Claude attempts to run a Bash command, the guard script receives
the command as JSON on stdin, inspects it, and either:

- Exits `0` — safe, Claude proceeds.
- Exits `2` — blocked; the reason is printed and fed back to Claude as context
  so it can adjust its approach.

**Patterns blocked:**

| Category | Examples |
|---|---|
| Recursive rm on critical paths | `rm -rf /`, `rm -rf ~`, `rm -rf /etc`, `rm -rf /usr`, `rm -rf $HOME`, `/System`, `/Library`, `/bin`, … |
| Filesystem format | `mkfs.ext4 /dev/sda`, `mkfs /dev/disk2` |
| Block device wipe via dd | `dd if=/dev/zero of=/dev/disk0` |
| macOS diskutil destructive ops | `diskutil eraseDisk`, `diskutil zeroDisk` |
| chmod 777 on root or home | `chmod -R 777 /`, `chmod 777 ~` |
| Fork bomb | `:(){ :|:& };:` |
| Truncation of system files | `> /etc/passwd`, `> /etc/sudoers` |
| shred / wipefs on block devices | `shred /dev/sda`, `wipefs /dev/disk1` |

Nothing is blocked silently — the engineer always sees why.

---

### ESLint On-Save (`PostToolUse` on Write + Edit)

**Why `PostToolUse`, not `Stop`?**

`Stop` fires after Claude has finished its entire response — at that point
there is no automatic mechanism to feed errors back and have Claude fix them
in the same turn. `PostToolUse` fires immediately after each file write, while
Claude is still active, creating a real lint-and-fix loop with no human prompt
required.

**The loop:**

```
Claude writes/edits a .ts/.tsx/.js/.jsx file
        ↓
eslint-on-save.py fires (PostToolUse)
        ↓
  eslint --fix runs (auto-corrects formatting, simple rules)
        ↓
  Re-check for remaining errors
        ↓
  No errors? → exit 0, Claude continues silently
  Errors?    → exit 2, errors printed → Claude sees them,
               fixes the code, writes the file again → loop repeats
```

**ESLint discovery order** (for monorepos):

1. `node_modules/.bin/eslint` — nearest ancestor directory that has it
2. `npx eslint` — if `package.json` in an ancestor directory lists `eslint` as a dep
3. System `eslint` — if found via `which eslint`
4. Skip silently — if none found (never blocks Claude in ESLint-free projects)

**Supported file extensions:** `.js` `.ts` `.jsx` `.tsx` `.mjs` `.cjs` `.mts` `.cts`

Files outside these extensions (CSS, JSON, YAML, markdown, etc.) are skipped.

---

### Bell Notification (`Stop` + `Notification`)

| Event | Sound | Meaning |
|---|---|---|
| `Stop` | `Glass.aiff` (chime) | Claude has finished its response or task |
| `Notification` | `Ping.aiff` (ping) | Claude is waiting for user input or approval |

Falls back to `tput bel` (terminal bell) if `afplay` is unavailable.

---

## How Hooks Are Delivered

Hooks are defined in `hooks/hooks.json` using `${CLAUDE_PLUGIN_ROOT}` paths. When the plugin is installed, Claude Code resolves these paths at runtime to the plugin's installed location.

```
hooks/hooks.json → defines all hook events and script paths
hooks/   → contains the actual hook scripts (Python/Bash)
```

Plugin hooks are **additive**: they run alongside any hooks your project defines locally. No conflict.

---

## Scope: Plugin-Delivered

Hooks are delivered via the plugin system and apply to any project where the plugin is installed. No machine-level installation (`~/hooks/`) is needed.

| Scope | Mechanism | When it applies |
|---|---|---|
| Plugin | `hooks/hooks.json` via plugin system | Any project with the plugin installed |
| Project-level | `.claude/settings.json` hooks | Only inside that project directory |

Plugin hooks and project hooks are **additive** — both fire, neither replaces the other.

---

## MCP Servers (Project-Scoped)

The plugin ships a `.mcp.json` at the repo root. When Claude Code opens any
project that imports this plugin, these servers are **auto-loaded** — no manual
`claude mcp add` needed. All run locally via `npx` with **no API keys required**.

| Server | Package | Purpose |
|---|---|---|
| Sequential Thinking | `@modelcontextprotocol/server-sequential-thinking` | Structured problem decomposition through dynamic thought sequences |
| Playwright | `@playwright/mcp` | Official Microsoft browser automation via accessibility snapshots (E2E testing, web interaction) |
| Context7 | `@upstash/context7-mcp` | Up-to-date library docs and code examples — prevents hallucinated APIs |

**Prerequisites:** Node.js 18+ and `npx` available in your `PATH`.

**First-run note:** Claude Code will prompt you to approve project-scoped MCP
servers the first time. Accept once — the choice is remembered.

**Adding more servers:** Edit `.mcp.json` and add entries following the same
pattern. Use `npx -y` to auto-install.

---

## Uninstalling

To remove hooks, uninstall the plugin:

```
/plugin uninstall client-master@client-registry
```

If you previously used `install-hooks.sh` (v1.x), see [MIGRATION.md](MIGRATION.md) for cleanup of stale `~/hooks/` files.

---

## Extending

**Add blocked shell patterns** — edit `CRITICAL_PATHS` or `_STATIC_RULES` in
`hooks/guard-destructive-commands.py`. Plugin updates propagate automatically.

**Lint additional file types** — add extensions to `LINTABLE_EXTENSIONS` in
`hooks/eslint-on-save.py` and ensure the relevant linter is available.

**Add notification sounds** — add `case` branches in `hooks/notify-bell.sh`
and register the new event in `hooks/hooks.json`.

---

## Troubleshooting

**Prompt Scanner blocking a legitimate security discussion**
Set `PROMPT_SCANNER_MODE=audit` temporarily to allow the prompt through
while still logging findings. Or run `PROMPT_SCANNER_MODE=audit` in your
shell before starting Claude Code for that session.

**False positive on a code example**
The scanner uses pattern matching and Luhn validation — it won't match
well-known test values like `4111 1111 1111 1111` as a "real" card (Luhn
passes but the scanner only fires on less obvious candidates). If a real
false positive occurs, open a PR with the specific pattern and a fix.

**Hook not firing after install**
Restart Claude Code. Verify the plugin is installed: `/plugin list`.

**ESLint not running / no errors reported**
Confirm the project has ESLint installed (`node_modules/.bin/eslint` or a
`package.json` that lists it). The hook skips silently if no ESLint is found
to avoid blocking Claude in non-JS projects.

**ESLint running with wrong config**
The hook walks up from the edited file's directory to find the nearest
`node_modules/.bin/eslint`. In a monorepo, ensure each package has its own
`node_modules/.bin/eslint` or that the root `npx eslint` resolves correctly.

**`afplay` not found / no sound**
Falls back to `tput bel`. Check your terminal bell and system volume settings.

**A legitimate shell command is being blocked**
Run it manually in your terminal. If the guard pattern is too broad, open a PR
with a narrowed regex and evidence that the command is safe.

**Hooks double-firing (v1.x migration)**
If you previously used `install-hooks.sh`, stale hooks in `~/hooks/`
may fire alongside plugin hooks. See [MIGRATION.md](MIGRATION.md) Step 2 for cleanup.
