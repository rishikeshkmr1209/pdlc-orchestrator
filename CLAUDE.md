# CLIENT_ORG — Claude Master Plugin

## Organization Identity

You are assisting engineers at **CLIENT_ORG**, a technology organization.

**Stack:** <!-- Fill in your stack --> | **CI/CD:** <!-- Fill in CI/CD --> | **Cloud:** <!-- Fill in cloud provider --> | **Monorepo:** <!-- Fill in monorepo tool -->

---

## Core Behavioral Principles

1. **Security-first.** Never commit secrets, credentials, or PII. Flag any discovered secrets immediately.
2. **Minimal blast radius.** Prefer targeted, reversible changes. Ask before touching shared infrastructure. Use `trash` over `rm` for deletions.
3. **Explain, don't just do.** For non-trivial changes, briefly explain reasoning before making them.
4. **Fail loud, fail safe.** Surface errors clearly rather than silently swallowing them.
5. **Least privilege.** Minimal IAM permissions; never suggest `*` resource wildcards.
6. **Backward compatible by default.** Additive over subtractive. Never remove defaults without blast radius check.

---

## Forbidden Actions

- `git push --force` to `main`, `master`, or any release branch
- Creating a PR without a Jira ticket ID
- Committing `.env` files, AWS credentials, API keys, private certificates, or passwords
- Logging PII (email, phone, name, address, payment data) to any monitoring tool
- Processing IP addresses without proper anonymization
- Using user data before consent is confirmed
- Dropping/truncating database tables without explicit, confirmed user instruction
- Disabling CI checks (`--no-verify`, `ci skip`) unless user explicitly confirms
- Generating or guessing internal CLIENT_ORG URLs, account IDs, or region values
- Deleting files or directories with `rm` — use `trash` or confirm with the user first

---

## JS/TS Conventions

- **TypeScript:** strict mode. No `any` unless justified in a comment.
- **Formatting:** Prettier-compliant before committing.
- **Linting:** ESLint with `@typescript-eslint`. Auto-fixable issues fixed before PR.
- **Imports:** Absolute via `tsconfig.json` path aliases, not relative `../../..` chains.
- **Error handling:** Typed error classes or `Result<T, E>`. Avoid bare `catch (e: any)`.
- **Async:** `async/await` over raw Promise chains. No `Promise.all` without error handling.
- **Testing:** Jest for unit/integration, Playwright for E2E. ≥80% coverage on business logic.
- **Naming:** `camelCase` variables/functions, `PascalCase` classes/types/components, `SCREAMING_SNAKE_CASE` constants, `kebab-case` file names.

---

## Jira & Branch/PR Naming

Every change must be traceable to a Jira ticket:

- **Branch:** `<TICKET-ID>-short-description` (e.g., `TICKET-1234-add-social-login`)
- **PR title:** `<TICKET-ID>: Short description`
- **PR body:** must link the Jira ticket — required by security team, no exceptions.

---

## PII & Data Privacy

- Never log PII to any monitoring system (DataDog, CloudWatch, etc.). See also Forbidden Actions.
- Anonymize when PII must be observed (hash user IDs before logging).
- Trace full data flow before logging any object.

---

## Observability

- Every service change: consider metrics, dashboards, monitors.
- Structured logs only — never `console.log(object)` in production. Use the structured logger.
- Feature flags via LaunchDarkly. Document flag names in the PR.
- Update Postman collections when API shapes change.

---

## GitHub Actions

- Workflows in `.github/workflows/`. Don't modify shared reusable workflows without confirming.
- Use `actions/checkout@v4`, `actions/setup-node@v4` — don't downgrade.
- Secrets via GitHub Secrets or AWS OIDC — never hardcode in YAML.

## AWS

- Use env vars or SSM Parameter Store for runtime config. Never hardcode region or account IDs.
- CDK: follow existing stack patterns. SAM: `sam validate` before deployment.
- Lambda: prefer `nodejs20.x`. Match existing timeout/memory conventions.

---

## Implementation Safety Rules

1. **Test baseline first.** Run full test suite before modifying ANY file. Record pass/fail counts.
2. **Test after each file change.** Don't batch changes and test at the end.
3. **Never remove defaults without checking blast radius.** Grep all usages, run tests first.
4. **Use `git stash` to verify baseline.** If unsure whether failures are pre-existing: stash, test, pop.
5. **Logging costs money.** Only add logging where it provides actionable information.
6. **Check infrastructure impact.** Health endpoints, startup sequences, API response shapes.
8. **Never reformat unchanged code.** Use the Edit tool for targeted changes — never rewrite entire files via Write unless creating a new file. Match the exact existing formatting: indentation, line breaks, trailing commas, quote style, compact vs. multi-line JSON. Formatting-only diffs in PRs waste reviewer time and obscure real changes.
7. **TypeScript `!` breaks DI.** `region!: string` gives `undefined` in DI containers. Keep defaults.

---

## SDLC Artifact Paths

All SDLC pipeline artifact paths are rooted at `$PROJECT_ROOT/docs/artifacts/<ticketId>/`.

- `$PROJECT_ROOT` is the **workspace root** — captured once at pipeline startup by walking up from CWD until a directory containing `claude-master-plugin/` is found, so `docs/artifacts/` always lands at the same level as `claude-master-plugin/`:
  ```bash
  PROJECT_ROOT=$(python3 -c "
  import os, sys
  d = os.getcwd()
  while d != '/':
      if os.path.isdir(os.path.join(d, 'claude-master-plugin')):
          print(d); sys.exit()
      d = os.path.dirname(d)
  print(os.getcwd())
  ")
  ```
- Canonical base paths are defined in `claude-master-plugin/config/phase-artifact-map.json` under `md_base_path` and `state_base_path`
- **All skills MUST use these base path keys** when constructing artifact paths — never hardcode bare relative paths like `docs/artifacts/<ticket>/`
- Phase artifacts (`.md` files) live under `md_base_path`
- State files (`pipeline_state_<ticket>.json`, `artifact-digest.md`, `impl_state.json`) live under `state_base_path`
- **Never create directories outside these two paths.** Do not create `.claude/checkpoints/`, `.claude/state/`, or any other location for pipeline artifacts — these are forbidden paths.

---

## Codebase Index (Targeted Exploration)

When exploring a codebase, **always check for `.claude/codebase-index/` first** before doing broad Glob/Grep scans:

1. If `.claude/codebase-index/repo-map.md` exists, read it first — it's a compact map of all modules, files, and exported symbols ranked by importance.
2. If `.claude/codebase-index/index.json` exists, use it to look up specific modules, keywords, domain concepts, and file dependency graphs.
3. Use the index to identify the top-ranked files relevant to your task, then read those files directly — skip broad directory scanning.
4. If no index exists, fall back to standard Glob/Grep exploration.
5. To build or refresh the index, invoke the `build-codebase-index` skill.

---

## Per-Group Customization

Teams create a **project-level `CLAUDE.md`** that imports this file and adds project-specific context (AWS region, service name, Jira prefix, team lead). The master plugin never contains org-specific secrets, account IDs, or URLs.

---

## Response Style

- Concise. Bullet points over paragraphs.
- Code blocks for all code, config, commands.
- When unsure, ask — don't guess at org-specific details.
- Flag security concerns immediately.
