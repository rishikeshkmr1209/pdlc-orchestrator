# Evaluation: build-codebase-index

## Test Scenarios

### 1. Index Build on Typical Monorepo

**Setup:** Target a multi-package monorepo with nested `src/`, `packages/`, or `workspaces/` structure.

**Steps:**
1. Run `/build-index --path=<monorepo-root>`
2. Read `.claude/codebase-index/index.json`
3. Read `.claude/codebase-index/repo-map.md`

**Expected:**
- `index.json` contains multiple modules matching top-level package directories
- Each module has `files[]`, `keywords[]`, `entry_points[]`, `dependencies[]`
- `repo-map.md` lists modules ordered by `import_rank` descending
- `stats.total_modules > 1`

### 2. Index Build on Flat Repo

**Setup:** Target a repo with files in a single directory (no `src/`, no nested packages).

**Steps:**
1. Run `/build-index --path=<flat-repo>`
2. Read index.json

**Expected:**
- Index contains 1 module (root-level)
- All files are grouped under that single module
- `import_rank` is computed from import relationships, not directory structure

### 3. Index Query with Specific Feature Description

**Setup:** Pre-built index on a loyalty platform repo.

**Steps:**
1. Use the query algorithm from `references/query-guide.md`
2. Query: "loyalty transaction creation"

**Expected:**
- Keywords extracted: `["loyalty", "transaction", "creation"]`
- Matches core-service module (keywords contain "loyalty", "transaction")
- Returns files sorted by `import_rank`: transaction-service.ts, transaction-repository.ts, etc.
- Top 15 files returned (within budget)

### 4. Index Query with Vague Feature Description

**Setup:** Pre-built index on any repo.

**Steps:**
1. Query: "improve performance"

**Expected:**
- Keywords: `["improve", "performance"]`
- Low or zero match score across modules
- Fallback triggered (condition 1 or condition 3)
- Fallback uses Glob/Grep with keywords, returns max 20 files
- `fallback_triggered = true` in metrics

### 5. Staleness Detection — Stale Index Triggers Incremental Rebuild

**Setup:** Pre-built index on a repo. Make a new commit after building.

**Steps:**
1. Read `index.json` → `git_head` = old SHA
2. Run `git rev-parse HEAD` → current SHA differs
3. Run `git diff --name-only <old-sha> HEAD | wc -l` → e.g., 5 files
4. Trigger incremental update (≤ 200 threshold)

**Expected:**
- Staleness detected (git_head mismatch)
- Incremental rebuild runs (not full rebuild)
- Updated `git_head` matches current HEAD
- Only changed files' metadata is updated

### 6. Import Extraction Accuracy

**Setup:** A source file containing all 6 import patterns.

**Sample file content:**
```typescript
import { Foo, Bar } from './foo';
import Baz from '../baz';
import * as Utils from './utils';
const Config = require('./config');
export { Helper } from './helper';
export * from './types';
```

**Steps:**
1. Run Grep with each of the 6 patterns from `references/repo-map-generator.md`

**Expected:**
- Pattern 1 matches `./foo`
- Pattern 2 matches `../baz`
- Pattern 3 matches `./utils`
- Pattern 4 matches `./config`
- Pattern 5 matches `./helper`
- Pattern 6 matches `./types`
- All 6 imports captured with correct paths

### 7. Token Budget Enforcement

**Setup:** Index built on a 500+ file repo.

**Steps:**
1. Read `.claude/codebase-index/repo-map.md`
2. Count characters in the file

**Expected:**
- File size ≤ 8,000 characters (default budget)
- Low-ranked modules/files are truncated with `... and N more files` footer
- Completely omitted modules show `... and M more modules` at the end
- All listed modules/files exist in index.json (consistency check passes)

### 8. Negative Trigger: Code Task Does NOT Activate

**Input:** "write code for feature X" or "fix the login bug"

**Expected:**
- Skill does NOT activate
- These are implementation tasks, not index-building tasks
- Only triggers: "build index", "index codebase", "create repo map"

### 9. Security Boundary: No PII, No Secrets, No Source Code Content

**Setup:** Index built on a repo that contains `.env` files, credentials in comments, and PII in variable names.

**Steps:**
1. Build index
2. Search index.json for any credential patterns, email patterns, or file content

**Expected:**
- `.env` files are excluded from indexing (Step 3 exclusion list)
- Index contains only: file paths, module names, export names, keyword terms
- No file content (source code bodies) appears in the index
- No PII or credential values appear anywhere in the index

### 10. Edge Case: Empty Repo

**Setup:** A git repo with no `.ts`, `.tsx`, `.js`, or `.jsx` files.

**Steps:**
1. Run `/build-index --path=<empty-repo>`

**Expected:**
- Warning printed: "No source files found. Index is empty."
- `index.json` is valid JSON with `stats.total_files = 0`, `stats.total_modules = 0`
- `modules` array is empty, `file_index` is empty, `domain_concepts` is empty
- `repo-map.md` contains header only with no module sections

### 11. Staleness Detection — Full Rebuild Threshold (>200 Files)

**Setup:** Pre-built index on a repo. Make >200 file changes (e.g., major branch merge).

**Steps:**
1. Read `index.json` → `git_head` = old SHA
2. Run `git rev-parse HEAD` → current SHA differs
3. Run `git diff --name-only <old-sha> HEAD | wc -l` → result > 200

**Expected:**
- Full rebuild triggers (not incremental update)
- `build-codebase-index --force` is invoked
- Entire index is regenerated from scratch
- `git_head` updated to current HEAD

### 12. Force Rebuild with --force Flag

**Setup:** Pre-built index that is fresh (git_head matches HEAD).

**Steps:**
1. Run `/build-index --force`

**Expected:**
- Full rebuild runs despite index being fresh
- `generated_at` timestamp is updated
- All modules and files re-scanned
- New `index.json` and `repo-map.md` written

### 13. Gitignore Conflict Warning

**Setup:** Repo with `.gitignore` containing `.claude/` or `*.json` patterns that would exclude the index.

**Steps:**
1. Run `git check-ignore .claude/codebase-index/index.json`
2. Exit code 0 (file is gitignored)

**Expected:**
- Warning printed: "WARNING: .claude/codebase-index/ is gitignored. Add !.claude/codebase-index/ to your .gitignore to commit the index, or use --force each session to rebuild."
- Index is still built (warning is non-blocking)

### 14. Corrupted Index Recovery

**Setup:** `.claude/codebase-index/index.json` exists but contains invalid JSON (e.g., truncated write).

**Steps:**
1. Read `index.json` → JSON parse fails

**Expected:**
- Status detected as **corrupted** (treat as missing)
- Full rebuild triggers via `build-codebase-index --force`
- Valid `index.json` written after rebuild

### 15. Pipeline Integration — Exploration Metrics Recorded

**Setup:** Run SDLC pipeline on a repo with a pre-built fresh index.

**Steps:**
1. Pipeline reaches Phase [0] TARGETED EXPLORATION
2. Index is fresh → no rebuild needed
3. Repo map read, relevant files identified and read
4. Metrics recorded

**Expected:**
- `pipeline_state_<ticket>.json` contains `exploration_metrics` with:
  - `files_read_count` > 0
  - `exploration_time_ms` > 0
  - `index_hit` = true
  - `fallback_triggered` = false
  - `index_freshness` = "fresh"
