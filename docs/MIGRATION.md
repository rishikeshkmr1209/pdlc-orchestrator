# Migration Guide — Symlink Bootstrap to Native Plugin

This guide covers migrating from the old symlink-based bootstrap (`v1.x`) to the native Claude Code plugin system (`v2.0`).

**Time required:** ~5 minutes per project.

---

## What Changed in v2.0

| Old (v1.x) | New (v2.0) |
|-------------|------------|
| `bootstrap.sh` creates symlinks | Plugin installed via `/plugin` commands |
| `.claude/` is a symlink → plugin repo | `.claude/` is the project's own directory |
| `install-hooks.sh` copies hooks to `~/hooks/` | Hooks delivered via plugin system automatically |
| `~/.claude/settings.json` wires hooks with `~/hooks/` paths | Plugin hooks use `${CLAUDE_PLUGIN_ROOT}` paths |
| Skills/agents only from plugin (no project-local customization) | Plugin skills namespaced as `client-master:*`, project can have its own |

---

## Step 1: Clean Up Old Symlinks (per project)

In each project that used `bootstrap.sh`:

```bash
cd /path/to/your-project

# Remove the .claude symlink (NOT rm -rf — it's a symlink, not a directory)
if [ -L .claude ]; then
    rm .claude
    echo "Removed .claude symlink"
fi

# Remove the .mcp.json symlink
if [ -L .mcp.json ]; then
    rm .mcp.json
    echo "Removed .mcp.json symlink"
fi

# Remove symlink entries from .gitignore
# (edit manually — remove lines that say ".claude" and ".mcp.json")
```

## Step 2: Clean Up Machine-Level Hooks (once per machine)

The old `install-hooks.sh` copied hook scripts to `~/hooks/` and registered them in `~/.claude/settings.json`. These will **double-fire** alongside plugin hooks if not cleaned up.

**One-liner cleanup:**

```bash
# Remove stale hook copies
rm -f ~/hooks/scan-prompt.py \
      ~/hooks/guard-destructive-commands.py \
      ~/hooks/guard-env-files.py \
      ~/hooks/eslint-on-save.py \
      ~/hooks/notify-bell.sh \
      ~/hooks/session-learnings-check.py \
      ~/hooks/context-monitor.py

# Remove statusline script
rm -f ~/.claude/statusline-script.sh

# If the hooks directory is now empty, remove it
rmdir ~/hooks/ 2>/dev/null || true
```

**Then clean `~/.claude/settings.json`:**

Open `~/.claude/settings.json` and remove:
1. All entries in the `"hooks"` section that reference `~/hooks/` paths
2. The `"statusLine"` entry if it points to `~/.claude/statusline-script.sh`

If the only hooks in your settings were plugin hooks, you can remove the entire `"hooks"` section. If you have personal hooks mixed in, only remove the plugin ones (they reference `~/hooks/scan-prompt.py`, `guard-destructive-commands.py`, `guard-env-files.py`, `eslint-on-save.py`, `notify-bell.sh`, `session-learnings-check.py`, and `context-monitor.py`).

## Step 3: Install the Plugin (per project)

In a Claude Code session inside your project:

```
/plugin marketplace add your-org/claude-master-plugin
/plugin install client-master@client-registry
```

Or add to your project's `.claude/settings.json` for team-wide auto-discovery:

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

## Step 4: Set Up Project Files

```bash
# Run the new setup script to create CLAUDE.md template and docs/artifacts/
bash <plugin-path>/scripts/setup-project.sh
```

Or if you already have a `CLAUDE.md` with the old `@../claude-master-plugin/CLAUDE.md` import, you can keep it — the import still works as long as the plugin repo is cloned nearby. However, with the plugin system, the CLAUDE.md from the plugin is loaded automatically, so the `@import` line is no longer required.

## Step 5: Restart Claude Code

```bash
# Exit and restart Claude Code to pick up plugin changes
claude
```

---

## Verification

After migration, verify in a Claude Code session:

| # | Test | Expected |
|---|------|----------|
| 1 | "What organization are you working for?" | Mentions CLIENT_ORG |
| 2 | Paste a fake API key: `sk-test123abc` | Prompt scanner blocks it |
| 3 | `/review` | Code review skill activates |
| 4 | "What agents do you have?" | Lists 6 agents |
| 5 | `/client-master:sdlc --ticket=TEST-001` | Pipeline starts |

---

## Rollback

If you need to revert to v1.x:

```bash
# Re-create the symlink
cd /path/to/your-project
ln -s ../claude-master-plugin/.claude .claude
ln -s ../claude-master-plugin/.mcp.json .mcp.json

# Re-install machine-level hooks
bash ../claude-master-plugin/scripts/install-hooks.sh  # (from v1.x branch)
```

Note: `bootstrap.sh` and `install-hooks.sh` are only available on the v1.x branch/tag. The `main` branch (v2.0+) has removed these scripts.

---

## FAQ

**Q: Do I need to do anything if I never ran `install-hooks.sh`?**
A: Skip Step 2. You only need to clean up machine-level hooks if you previously ran `install-hooks.sh`.

**Q: Will my project-local `.claude/skills/` conflict with plugin skills?**
A: No. Plugin skills are namespaced under `client-master:` (e.g., `client-master:code-review`). Your local skills remain as-is.

**Q: What if I have personal hooks in `~/.claude/settings.json`?**
A: Only remove the plugin hook entries (ones referencing `~/hooks/`). Keep any personal hooks you've added.

**Q: Can I use both v1.x symlinks and v2.0 plugin on the same machine?**
A: Not recommended — hooks will double-fire. Migrate all projects at once, or at minimum ensure you clean up `~/hooks/` (Step 2) before using the plugin.
