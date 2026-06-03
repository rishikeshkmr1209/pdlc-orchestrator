---
name: build-codebase-index
user-invocable: true
description: >
  Build a persistent codebase index for targeted exploration. Use when user says
  "build index", "index codebase", "create repo map", or when the SDLC pipeline
  needs pre-requirements exploration optimization.
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - Bash
context: fork
---

# Build Codebase Index

Build a persistent codebase index that maps files to modules, domain concepts, and import relationships. The index enables targeted exploration — reading only the most relevant files for a given feature instead of scanning the entire codebase.

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--path=<repo-path>` | No | Target repository path. Defaults to current working directory. |
| `--force` | No | Force full rebuild even if index exists and is fresh. |

## Process

### Step 1: Determine Target Repo Path

- If `--path` is provided, use it as the target repo root
- Otherwise, use the current working directory
- Verify the path is a git repository: `git -C <path> rev-parse --git-dir`
- If not a git repo, warn and proceed without staleness detection

### Step 2: Check .gitignore Compatibility

Run: `git -C <path> check-ignore .claude/codebase-index/index.json`

- If the file is gitignored (exit code 0): print warning:
  ```
  WARNING: .claude/codebase-index/ is gitignored. Add !.claude/codebase-index/ to your
  .gitignore to commit the index, or use --force each session to rebuild.
  ```
- If not gitignored (exit code 1): proceed silently

### Step 3: Scan File Structure

Use Glob to discover all source files:

**Include patterns:**
```
**/*.ts, **/*.tsx, **/*.js, **/*.jsx, **/*.mjs, **/*.cjs
```

**Exclude directories:** `node_modules/`, `dist/`, `build/`, `.git/`, `.env*`, `coverage/`, `__mocks__/`

Record the total file count.

### Step 4: Extract Imports

For each discovered source file, extract import statements using the 6 Grep patterns and path resolution rules defined in `references/repo-map-generator.md`. Combine all 6 patterns into as few Grep passes as possible (ideally 1-2 combined regex calls rather than 6 separate passes) for efficiency.

### Step 5: Build Import Graph and Compute import_rank

1. For each file A that imports file B: add B to A's `imports_from`, add A to B's `imported_by`
2. Compute file-level `import_rank = len(imported_by)`
3. Apply co-location fallback for isolated files (see `references/repo-map-generator.md`)
4. Compute module-level `import_rank = avg(file import_ranks)`

### Step 6: Detect Modules

Identify logical modules from directory structure:

1. Find top-level directories under the repo root (1-2 levels deep)
2. Group files by their containing module directory
3. Name modules from directory names (kebab-case)
4. Generate a 1-line description for each module based on its file types and naming patterns
5. Identify entry points: files named `index.{ts,tsx,js,jsx}`, `main.*`, `app.*`, `handler.*`
6. Extract module dependencies from the import graph (which modules import from which)

### Step 7: Extract Domain Concepts

Build the `domain_concepts` mapping using two sources:

**Source A — `copilot-instructions.md` (primary, higher signal):**

For each top-level repo directory found in Step 3, check for `.github/copilot-instructions.md`.
If found, extract keywords from these sections:
- **Service Overview / Purpose** → business domain keywords (e.g., "bag fee", "order lifecycle", "phone masking")
- **Module Structure** — module directory names and their descriptions (e.g., domain-specific module names from the project)
- **External Integrations** — third-party names (e.g., identity providers, payment processors, CMS platforms, feature flag services, analytics tools)
- **Technology Stack** — framework/runtime keywords (e.g., "NestJS", "Apollo", "DynamoDB", "SQS", "SNS")
- **Business Rules** — domain terms from rule names (e.g., pricing rules, eligibility conditions, validation logic specific to the project)

Map each extracted keyword → repo name (not file path, since this is a multi-repo index).
Filter out generic words: "service", "the", "and", "for", "with", "using", "via", "from", "into".

**Source B — file/directory name analysis (fallback for repos without copilot-instructions.md):**

1. Split directory names on `-` and `/`
2. Split file names on `-`, `.`, and camelCase boundaries
3. Split exported symbol names on camelCase boundaries
4. Collect unique terms, filtering out generic words (e.g., "index", "utils", "types", "test")
5. Map each domain term to the files that contain it

Merge both sources into the final `domain_concepts` object. Source A entries take precedence where a keyword maps to multiple repos.

### Step 8: Generate index.json

Assemble the complete index following `references/index-schema.md`:

- Set `version` to `"1.0"`
- Set `generated_at` to current ISO-8601 timestamp
- Set `repo_root` to `"."` (always relative — never store absolute paths to avoid leaking filesystem structure)
- Set `git_head` to current `git rev-parse HEAD`
- Compute `stats`: total_files, total_modules, build_duration_ms
- Assemble `modules[]` with all fields
- Assemble `file_index{}` with all fields
- Assemble `domain_concepts{}`
- Enforce size constraints: `exports` capped at 10, `imported_by` capped at 20

### Step 9: Generate repo-map.md

Generate the compact repo map following `references/repo-map-generator.md`:

- Sort modules by `import_rank` descending
- Within each module, sort files by `import_rank` descending
- Include exported symbols for each file
- Enforce token budget (default 8,000 characters)
- Add truncation footers where modules/files are omitted

### Step 10: Validate Consistency

Verify that `repo-map.md` and `index.json` are consistent:

1. Every module in repo-map.md exists in index.json
2. Every file in repo-map.md exists in index.json file_index
3. No phantom modules or files

If validation fails, log a warning and regenerate the failing artifact.

### Step 11: Write Output

1. Create directory `.claude/codebase-index/` if it doesn't exist
2. Write `.claude/codebase-index/index.json`
3. Write `.claude/codebase-index/repo-map.md`
4. Compute `index_size_bytes` from the written file and update `stats`
5. Print summary:
   ```
   Codebase index built successfully.
   Files: <total_files> | Modules: <total_modules> | Duration: <build_duration_ms>ms
   Index: .claude/codebase-index/index.json (<index_size_bytes> bytes)
   Repo map: .claude/codebase-index/repo-map.md
   ```

## Error Handling

| Error | Action |
|-------|--------|
| Unreadable file | Skip with warning: `WARNING: Could not read <path>, skipping.` Continue building. |
| Empty repo (0 source files) | Create empty index with warning: `WARNING: No source files found. Index is empty.` |
| Build failure (unexpected) | Print error, do NOT block pipeline. Index build failure is non-blocking (C-004). |
| Invalid tsconfig.json | Skip path alias resolution, warn: `WARNING: Could not parse tsconfig.json. Path aliases not resolved.` |
| Not a git repository | Proceed without staleness detection. Set `git_head` to `"unknown"`. |

## Output

- `.claude/codebase-index/index.json` — Structured programmatic index
- `.claude/codebase-index/repo-map.md` — Compact LLM-readable repo map

## References

- `references/index-schema.md` — JSON schema for index.json (COMP-002)
- `references/repo-map-generator.md` — Grep patterns, graph ranking, token budget, repo map format (COMP-008)
- `references/query-guide.md` — How to query the index for feature-relevant files (COMP-003)
- `references/exploration-strategy.md` — Targeted exploration algorithm with staleness detection (COMP-004)

## Evaluation

See `appendix/evaluation.md` for 10 test scenarios covering happy path, edge cases, security boundaries, and negative triggers.
