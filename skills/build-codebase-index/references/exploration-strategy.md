# Targeted Exploration Strategy

## Purpose

Defines the full algorithm for pre-requirements exploration using the codebase index. This strategy replaces broad codebase scanning with targeted file reads, reducing exploration time from 8-10 minutes to under 2 minutes.

## Staleness Detection

Before using the index, check whether it is fresh, stale, or missing.

### Detection Steps

1. Attempt to read `.claude/codebase-index/index.json`
2. If file not found → status = **missing**
3. If file found but invalid JSON → status = **corrupted** (treat as missing)
4. Extract `git_head` field from the index
5. Run `git rev-parse HEAD` to get the current HEAD SHA
6. Compare:
   - `git_head` matches current HEAD → status = **fresh**
   - `git_head` does not match → status = **stale**

### Rebuild Decision Matrix

| Index Status | Action |
|---|---|
| Missing | Full rebuild: invoke `build-codebase-index` skill |
| Corrupted | Full rebuild: invoke `build-codebase-index --force` |
| Stale (≤ 200 changed files) | Incremental update: invoke `build-codebase-index` (without `--force`) |
| Stale (> 200 changed files) | Full rebuild: invoke `build-codebase-index --force` |
| Fresh | Proceed directly — no rebuild needed |
| Any + `--rebuild-index` flag | Full rebuild: invoke `build-codebase-index --force` |

To determine the number of changed files when stale:
```bash
git diff --name-only <indexed-git-head> HEAD | wc -l
```

## 12-Step Exploration Algorithm

Follow these steps in order. Record the start time before Step 1.

### Step 1: Check Index Existence

Read `.claude/codebase-index/index.json`. If the file does not exist, go to Step 2. If it exists, go to Step 3. **Retain the parsed index in memory for all subsequent steps — do not re-read the file.**

### Step 2: Build Missing Index

Invoke the `build-codebase-index` skill via the Skill tool:
```
Skill: build-codebase-index
Args: --path=<target-repo-path>
```
After the skill completes, proceed to Step 6.

### Step 3: Check Staleness

Extract `git_head` from the index. Run `git rev-parse HEAD`. Compare the two values.
- If they match → index is **fresh**, go to Step 6
- If they differ → index is **stale**, go to Step 4

### Step 4: Determine Rebuild Scope

Run: `git diff --name-only <indexed-git-head> HEAD | wc -l`
- If result ≤ 200 → **incremental update**, go to Step 5a
- If result > 200 → **full rebuild**, go to Step 5b

### Step 5a: Incremental Update

Invoke the `build-codebase-index` skill without `--force`:
```
Skill: build-codebase-index
Args: --path=<target-repo-path>
```
Proceed to Step 6.

### Step 5b: Full Rebuild

Invoke the `build-codebase-index` skill with `--force`:
```
Skill: build-codebase-index
Args: --path=<target-repo-path> --force
```
Proceed to Step 6.

### Step 6: Read Repo Map

Read `.claude/codebase-index/repo-map.md`. This provides a compact structural overview of the entire codebase with graph-ranked symbols.

### Step 7: Identify Relevant Modules and Files

Using the repo map and the feature description (from the ticket or user input):
1. Follow the query algorithm in `references/query-guide.md`
2. Extract keywords from the feature description
3. Match keywords against module keywords and domain concepts
4. Identify the most relevant modules and their top-ranked files

### Step 8: Use Detailed Metadata

Using the already-loaded `index.json` (from Step 1), get detailed file metadata for the identified modules:
- File types, exports, import relationships
- Entry points and dependencies
- Domain concept mappings

### Step 9: Read Top-Ranked Files

Read the top-ranked relevant source files from the target repo. **Maximum 15 files.** Prioritize:
1. Entry points of matched modules
2. Files with highest `import_rank` in matched modules
3. Files appearing in matched `domain_concepts`

### Step 10: Fallback Exploration

If Step 7 returned no matches (zero keyword hits, or all matched files have import_rank = 0):

Execute the Fallback Procedure described in `references/query-guide.md` (Glob + Grep with feature keywords, max 20 files). Mark `fallback_triggered = true` in metrics.

### Step 11: Record Exploration Metrics

Calculate exploration duration (current time minus start time from Step 1). Record metrics:

```json
{
  "exploration_metrics": {
    "files_read_count": <number of files actually read>,
    "exploration_time_ms": <duration in milliseconds>,
    "index_hit": <true if index was used, false if fallback>,
    "fallback_triggered": <true if Step 10 was executed>,
    "index_version": "1.0",
    "index_freshness": "<fresh|stale|missing>"
  }
}
```

Write these metrics to `pipeline_state_<ticket>.json` under the `exploration_metrics` key.

### Step 12: Pass Context to Requirements

Pass the gathered context (file contents, module structure, domain concepts) to the `sdlc-requirements` skill invocation. The requirements skill will use this context instead of performing its own broad codebase exploration.

## Incremental Update Procedure

When the index is stale and ≤ 200 files have changed:

1. Get list of changed files: `git diff --name-only <indexed-git-head> HEAD`
2. For each **modified** file: re-extract exports, imports, type classification
3. For each **deleted** file: remove from `file_index` and from its module's `files` array
4. For each **new** file: add to `file_index`, assign to appropriate module
5. Recompute `import_rank` for:
   - Files that were modified
   - Files that import from modified files (`imported_by` relationships)
   - Modules containing any affected files
6. Regenerate `repo-map.md` (always a full regeneration — it's a compact summary)
7. Update `git_head` to current HEAD and `generated_at` to current timestamp

## .gitignore Compatibility Check

The `.gitignore` compatibility check is performed during index build (see SKILL.md Step 2). It runs during Steps 2, 5a, and 5b — not during every exploration.
