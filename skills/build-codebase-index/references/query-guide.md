# Index Query Guide

## Purpose

How to find feature-relevant files given a feature description, using the codebase index (`index.json`) and repo map (`repo-map.md`).

## Query Algorithm

### Step 1: Extract Keywords

From the feature description, extract meaningful keywords:
- Remove stop words (a, the, is, are, in, on, for, to, of, with, and, or, this, that)
- Split remaining words on spaces, hyphens, and camelCase boundaries
- Lowercase all keywords
- Example: "Add loyalty points display on user profile" → `["loyalty", "points", "display", "user", "profile"]`

### Step 2: Match Keywords Against Index

Search for keyword matches in two places:

1. **Module `keywords[]`**: For each module in `index.json`, count how many query keywords appear in the module's `keywords` array
2. **`domain_concepts{}` keys**: For each key in `domain_concepts`, count keyword overlap with the query keywords

Score each module: `match_score = count of distinct keyword matches`

### Step 3: Collect Files from Matched Modules

For modules with `match_score >= 1`:
- Collect all files from the module's `files` array
- Also collect files from `domain_concepts` entries that matched
- Sort all collected files by `import_rank` descending (most important first)
- Deduplicate (a file may appear from both module and domain_concept matches)

### Step 4: Select Top Files

Select the top **15 files** from the sorted, deduplicated list. This is the budget for targeted exploration — reading more than 15 files defeats the speed goal.

### Step 5: Expand if Score is Low

If the best module's `match_score < 3` (fewer than 3 keyword matches):
- For each matched module, check its `dependencies[]` array
- Add files from dependent modules (sorted by import_rank)
- Cap total at 15 files (replace lowest-ranked files if needed)

## Fallback Trigger Conditions

The query algorithm falls back to broad exploration when ANY of these conditions are true:

1. **Zero keyword matches**: No module's `keywords[]` and no `domain_concepts{}` key contains any query keyword
2. **Feature description too vague**: After stop-word removal, fewer than 2 meaningful words remain
3. **All matched files have import_rank = 0**: The matched files are all isolated (no imports, no importers)

## Fallback Procedure

When fallback is triggered:

1. Use **Glob** to find files matching query keywords in file names:
   - Pattern: `**/*{keyword1}*.*`, `**/*{keyword2}*.*` (for each keyword)
   - Exclude: `node_modules/`, `dist/`, `build/`, `.git/`, `.env*`, `coverage/`, `__mocks__/`
2. Use **Grep** to find files containing query keywords in their content:
   - Search for each keyword across source files
   - Collect file paths from matches
3. Combine Glob and Grep results, deduplicate
4. Cap at **20 files** maximum
5. Sort by frequency of keyword matches (files matching more keywords rank higher)

**Important:** Fallback exploration is slower than index-based queries. If fallback triggers frequently, the index may need rebuilding with `--force`.

## Examples

### Example 1: Specific Feature Query

**Feature:** "loyalty transaction creation"
**Keywords:** `["loyalty", "transaction", "creation"]`

**Step 2 matches:**
- Module `core-service`: keywords contain `["loyalty", "transaction", "points", "reward"]` → match_score = 2
- Domain concept `"loyalty-transaction"`: matches keyword `"transaction"` → adds files

**Step 3 result:** Files from core-service sorted by import_rank:
1. `core-service/services/transaction-service.ts` (rank: 8)
2. `core-service/data/transaction-repository.ts` (rank: 5)
3. `core-service/types/transaction.ts` (rank: 4)
4. `core-service/api/transaction-controller.ts` (rank: 3)
...

**Step 4:** Top 15 files selected for targeted exploration.

### Example 2: Vague Feature Query

**Feature:** "improve performance"
**Keywords:** `["improve", "performance"]`

**Step 2 matches:** No modules have "improve" or "performance" in keywords → match_score = 0 for all modules.

**Fallback triggered** (condition 1: zero keyword matches).

**Fallback procedure:** Glob for `**/*performance*.*`, Grep for `performance` in source files. Returns config files, utility files, and any files with "performance" in comments or code.

### Example 3: Low-Score Expansion

**Feature:** "add social login"
**Keywords:** `["social", "login"]`

**Step 2 matches:**
- Module `auth`: keywords contain `["login", "session", "token"]` → match_score = 1

**Step 5 expansion** (match_score = 1 < 3):
- `auth` module's `dependencies[]` = `["users", "config"]`
- Add files from `users` and `config` modules
- Total capped at 15 files
