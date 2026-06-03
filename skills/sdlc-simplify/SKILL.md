---
name: 06-simplify
description: >
  Phase 6 of the SDLC pipeline. Reviews implementation-changed files for code
  quality, clarity, dead code, duplicate logic, project standards
  conventions. Runs inline (Sonnet) scoped strictly to files touched by the
  implementation phase via git diff.
allowed-tools:
  - Bash
  - Read
  - Edit
---

# 6-Simplify (Phase 6)

## Prime Directive

> **Simplify without breaking.** Improve clarity, remove dead code, eliminate duplication. Never change behaviour — only how the code expresses it.

---

## Instructions

1. **Get changed files:**
   ```bash
   git diff --name-only HEAD~1
   ```
   Skip: `*.lock`, `*.snap`, `*.md`, `dist/`, `build/`, `.next/`, `node_modules/`. Fallback to `git diff --name-only --cached` if empty. Exit cleanly if still empty.

2. **Read all changed files** — follow `skills/_shared/parallel-reads-rule.md`.

3. **Simplify each file** applying:
   - Project standards: import sorting, explicit return types, React Props types, naming conventions, `async/await` over Promise chains
   - Clarity: reduce nesting (max depth 3, use early returns), replace nested ternaries with `if/else`, clear variable/function names, remove obvious comments
   - Balance: don't over-simplify — no overly clever solutions, no combining too many concerns, no removing helpful abstractions
   - Dead code: unused imports, commented-out blocks (>3 lines), unreachable branches
   - Duplication: copy-pasted blocks (>5 lines), repeated conditionals extractable to a shared util
   - project conventions: no bare `any`, typed error classes over `catch (e: any)`, structured logger over `console.log`, path aliases over relative `../../..` chains

4. **Apply fixes** using Edit only — never rewrite entire files with Write. Match exact existing formatting. Before removing an export, verify it's unused:
   ```bash
   grep -r "import.*<symbol>" <repo_root>/src --include="*.ts" --include="*.tsx"
   ```
   If a fix risks changing behaviour, skip it and flag it in the summary.

5. **Output summary:**
   ```
   Simplify — Phase 6 Complete
   Files reviewed: N  |  Files modified: N

   Changes:  <file> — [type] description
   Flagged:  <file> — reason skipped
   ```
