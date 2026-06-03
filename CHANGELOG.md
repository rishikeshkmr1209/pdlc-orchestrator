# Changelog

All notable changes to the Claude Master Plugin will be documented in this file.

This project follows [Semantic Versioning](https://semver.org/).

---

## [2.0.0] — 2026-02-27

### Breaking Changes

- **Removed symlink-based bootstrap.** `scripts/bootstrap.sh` and `scripts/install-hooks.sh` have been deleted. The plugin is now installed via Claude Code's native plugin system. See [MIGRATION.md](docs/MIGRATION.md) for upgrade steps.
- **Removed `.claude/settings.json` hook wiring.** Hooks are now delivered via `hooks/hooks.json` through the plugin system using `${CLAUDE_PLUGIN_ROOT}` paths.
- **Restructured to match Claude Code plugin conventions.** `commands/`, `agents/`, `skills/` moved to repo root. Hook scripts moved to `hooks/` alongside `hooks.json`. Manifests live in `.claude-plugin/`.

### Added

- **Native plugin installation.** Install via `claude plugin marketplace add your-org/claude-master-plugin` then `claude plugin install client-master@client-registry`.
- **`.claude-plugin/marketplace.json`** with `$schema` and `metadata.description` per Claude Code convention.
- **`.claude-plugin/plugin.json`** — minimal plugin manifest (name, version, author).
- **Context monitor hook in plugin hooks.** `context-monitor.py` now fires via `hooks/hooks.json` (previously only delivered via `install-hooks.sh`).
- **`scripts/setup-project.sh`.** Replaces the non-symlink parts of bootstrap — creates CLAUDE.md template and docs/artifacts/ directory.
- **`docs/MIGRATION.md`.** Step-by-step guide for teams migrating from symlink bootstrap to plugin installation.
- **`CHANGELOG.md`.** This file — semver versioning for controlled upgrades.
- **Team auto-discovery via `enabledPlugins`.** Child repos can auto-prompt engineers to install the plugin.

### Changed

- **SDLC pipeline renumbered to 9 phases.** Replaced 8-phase model (with `4a`/`4b` sub-phase nesting) with a flat 9-phase schema. Phase 4 (Implementation Planning) is now a first-class phase tracked in `pipeline_state.json`. The `sub_phase` field has been removed.
- **`sdlc-impl-planning` skill added** as a first-class pipeline phase (Phase 4). Total skill count is now 17.
- **Artifact validation field names aligned** with JSON schemas (`design_review`, `verification_report`, `risk_assessment`).
- **`commands/`, `agents/`, `skills/` moved to repo root** (from `.claude/commands/`, `.claude/agents/`, `.claude/skills/`). Symlinks in `.claude/` for local dev.
- **Hook scripts moved to `hooks/`** (from `.claude/hooks/`). Now live alongside `hooks.json` per convention.
- **`README.md` rewritten.** Plugin installation is now the primary Quick Start. Symlink references removed.
- **`docs/ONBOARDING.md` rewritten.** Full guide now uses `claude plugin` commands. Symlink/copy/submodule options removed.
- **`docs/HOOKS.md` updated.** Removed `install-hooks.sh` references; hooks now delivered via plugin system.
- **`docs/WIKI.md` updated.** Distribution model section updated to reflect plugin-based approach.

### Removed

- `scripts/bootstrap.sh` — replaced by native plugin installation
- `scripts/install-hooks.sh` — hooks delivered via plugin system
- `.claude/settings.json` — hook wiring now in `hooks/hooks.json`

---

## [1.0.0] — 2026-02-20

### Added

- Initial release with symlink-based distribution model
- 7 hooks (prompt scanner, destructive guard, env guard, ESLint on-save, context monitor, bell, session learnings)
- 6 agents (code reviewer, security auditor, test engineer, PR manager, architect, DevOps)
- 16 auto-invocable skills including full SDLC pipeline
- 1 slash command (/sdlc)
- 3 MCP servers (Sequential Thinking, Playwright, Context7)
- 203 unit tests
- Bootstrap.sh and install-hooks.sh for project setup
