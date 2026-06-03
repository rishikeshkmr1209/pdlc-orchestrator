#!/usr/bin/env bash
# Claude Master Plugin — Project Setup
#
# Prepares a child project for use with the master plugin by:
#   1. Creating a CLAUDE.md template (if none exists)
#   2. Creating docs/artifacts/ directory for SDLC spec artifacts
#   3. Adding .claude/checkpoints/ to .gitignore
#
# This script does NOT create symlinks — the plugin is installed via
# Claude Code's native plugin system (/plugin commands).
#
# Usage (from your target project root):
#   bash <plugin-path>/scripts/setup-project.sh
#
# Safe to re-run: already-configured items are detected and skipped.

set -euo pipefail

echo ""
echo "Claude Master Plugin — Project Setup"
echo "========================================="
echo ""

# Verify we're in a git repo
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "ERROR: Not inside a git repository."
    echo "Run this from your project root: cd /path/to/your-project && bash $0"
    exit 1
fi

PROJECT_ROOT="$(git rev-parse --show-toplevel)"
cd "$PROJECT_ROOT"

echo "Project root: $PROJECT_ROOT"
echo ""

changes=0

# ── 1. Create CLAUDE.md template ─────────────────────────────────────────

if [[ -f "CLAUDE.md" ]]; then
    echo "  —  CLAUDE.md: already exists, skipping"
else
    project_name="$(basename "$PROJECT_ROOT")"
    # Title-case the project name (replace hyphens with spaces)
    title="$(echo "$project_name" | tr '-' ' ' | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) tolower(substr($i,2)); print}')"

    cat > CLAUDE.md <<EOF
# ${title} — Claude Project Context

---

## Project Identity

**Repository:** \`${project_name}\`
**Jira prefix:** <!-- e.g. ILO, SHLD, IREQ -->

## Project-Specific Context

<!-- Customize below — do not store secrets, account IDs, or internal URLs here -->

- **Primary stack:** TypeScript / Node.js
- **CI/CD:** <!-- CircleCI / GitHub Actions -->
- **AWS region:** <!-- e.g. us-east-1 -->
- **Key services:** <!-- list main services this repo owns -->
- **Team lead:** <!-- @github-handle -->

## SDLC Pipeline Usage

\`\`\`bash
/sdlc --mode=gates --ticket=<TICKET-ID>   # Interactive approval gates
/sdlc --mode=auto  --ticket=<TICKET-ID>   # Full automation
/requirements      --ticket=<TICKET-ID>   # Standalone requirements phase
\`\`\`
EOF

    echo "  ✓  CLAUDE.md: created — customize the Project-Specific Context section"
    changes=$((changes + 1))
fi

# ── 2. Create docs/artifacts/ ────────────────────────────────────────────

ARTIFACTS_DIR="$PROJECT_ROOT/docs/artifacts"

if [[ -d "$ARTIFACTS_DIR" ]]; then
    echo "  —  docs/artifacts/: already exists, skipping"
else
    mkdir -p "$ARTIFACTS_DIR"
    echo "  ✓  docs/artifacts/: created (git-tracked spec artifacts)"
    changes=$((changes + 1))
fi

# ── 3. Update .gitignore ────────────────────────────────────────────────

GITIGNORE="$PROJECT_ROOT/.gitignore"
CHECKPOINT_PATTERN=".claude/checkpoints/"

if [[ -f "$GITIGNORE" ]]; then
    if grep -qF "$CHECKPOINT_PATTERN" "$GITIGNORE"; then
        echo "  —  .gitignore: '$CHECKPOINT_PATTERN' already present, skipping"
    else
        echo "" >> "$GITIGNORE"
        echo "# SDLC pipeline ephemeral checkpoints (auto-added by plugin)" >> "$GITIGNORE"
        echo "$CHECKPOINT_PATTERN" >> "$GITIGNORE"
        echo "  ✓  .gitignore: added '$CHECKPOINT_PATTERN'"
        changes=$((changes + 1))
    fi
else
    echo "# SDLC pipeline ephemeral checkpoints (auto-added by plugin)" > "$GITIGNORE"
    echo "$CHECKPOINT_PATTERN" >> "$GITIGNORE"
    echo "  ✓  .gitignore: created with '$CHECKPOINT_PATTERN'"
    changes=$((changes + 1))
fi

# ── 4. Copy plugin commands to .claude/commands/ ────────────────────────
#
# Claude Code registers slash commands from .claude/commands/.
# This copies the plugin's commands (e.g., /sdlc) so they work in the project.

PLUGIN_DIR="$(cd "$(dirname "$0")/.." && pwd)"
COMMANDS_SRC="$PLUGIN_DIR/commands"
COMMANDS_DST="$PROJECT_ROOT/.claude/commands"

if [[ -d "$COMMANDS_SRC" ]]; then
    mkdir -p "$COMMANDS_DST"
    copied=0
    for cmd_file in "$COMMANDS_SRC"/*.md; do
        [[ -f "$cmd_file" ]] || continue
        cmd_name="$(basename "$cmd_file")"
        if [[ -f "$COMMANDS_DST/$cmd_name" ]]; then
            # Update if plugin version is newer
            if ! cmp -s "$cmd_file" "$COMMANDS_DST/$cmd_name"; then
                cp "$cmd_file" "$COMMANDS_DST/$cmd_name"
                echo "  ✓  .claude/commands/$cmd_name: updated from plugin"
                copied=$((copied + 1))
            else
                echo "  —  .claude/commands/$cmd_name: already up to date, skipping"
            fi
        else
            cp "$cmd_file" "$COMMANDS_DST/$cmd_name"
            echo "  ✓  .claude/commands/$cmd_name: copied from plugin"
            copied=$((copied + 1))
        fi
    done
    if [[ $copied -gt 0 ]]; then
        changes=$((changes + copied))
    fi
else
    echo "  —  Plugin commands directory not found, skipping"
fi

# ── 5. Create .claude/settings.json (auto-approve safe read operations) ──

CLAUDE_DIR="$PROJECT_ROOT/.claude"
SETTINGS_FILE="$CLAUDE_DIR/settings.json"

if [[ -f "$SETTINGS_FILE" ]]; then
    echo "  —  .claude/settings.json: already exists, skipping"
else
    mkdir -p "$CLAUDE_DIR"
    cat > "$SETTINGS_FILE" <<'EOF'
{
  "permissions": {
    "allow": [
      "Read",
      "mcp__atlassian__*",
      "mcp__github__*",
      "Glob",
      "Grep",
      "Bash(git log*)",
      "Bash(git status*)",
      "Bash(git diff*)",
      "Bash(git show*)",
      "Bash(git branch*)",
      "Bash(git rev-parse*)",
      "Bash(git ls-files*)",
      "Bash(find * -name *)",
      "Bash(ls*)",
      "Bash(cat *)",
      "Bash(head *)",
      "Bash(tail *)",
      "Bash(wc *)",
      "Bash(jq * *)",
      "Bash(node --version*)",
      "Bash(npm test*)",
      "Bash(npx tsc --noEmit*)",
      "Bash(npx eslint *)"
    ],
    "deny": []
  }
}
EOF
    echo "  ✓  .claude/settings.json: created (read-only ops auto-approved)"
    changes=$((changes + 1))
fi

# ── Summary ──────────────────────────────────────────────────────────────

echo ""
if [[ $changes -gt 0 ]]; then
    echo "Applied $changes change(s). Review and commit when ready:"
    echo "  git add CLAUDE.md docs/artifacts/ .gitignore .claude/settings.json .claude/commands/"
    echo "  git commit -m 'chore: configure project for Claude plugin'"
else
    echo "Project already configured — no changes made."
fi

echo ""
echo "Plugin installation (if not already installed):"
echo "  /plugin marketplace add your-org/claude-master-plugin"
echo "  /plugin install client-master@client-registry"
echo ""
echo "SDLC pipeline usage:"
echo "  /sdlc --mode=auto --ticket=<TICKET-ID>    Full automation"
echo "  /sdlc --mode=gates --ticket=<TICKET-ID>   Interactive approval"
echo "  /requirements --ticket=<TICKET-ID>         Standalone requirements phase"
