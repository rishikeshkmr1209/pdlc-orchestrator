# Codebase Index Schema (index.json)

## Overview

The codebase index uses a dual-artifact approach:

1. **`index.json`** — Structured JSON for programmatic queries (this schema)
2. **`repo-map.md`** — Compact LLM-readable text map (see `repo-map-generator.md`)

Both are stored in `.claude/codebase-index/` and committed to the repository.

## Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `version` | string | Schema version. Current: `"1.0"` |
| `generated_at` | string | ISO-8601 timestamp of index generation |
| `repo_root` | string | Relative path to the repo root (always `"."` since the index is stored inside the repo). Resolve to absolute at query time if needed. |
| `git_head` | string | Git HEAD commit SHA at generation time (for staleness detection) |
| `stats` | object | Summary statistics (see below) |
| `modules` | array | Logical module definitions (see below) |
| `file_index` | object | Flat file-path-keyed metadata lookup (see below) |
| `domain_concepts` | object | Domain term to file path mapping (see below) |

## `stats` Object

| Field | Type | Description |
|-------|------|-------------|
| `total_files` | number | Total source files indexed |
| `total_modules` | number | Total modules detected |
| `build_duration_ms` | number | Time taken to build the index in milliseconds |
| `index_size_bytes` | number | Size of the generated index.json file in bytes |

## `modules[]` Array

Each entry represents a logical module or feature area in the codebase.

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Module name derived from directory structure (e.g., `"core-service"`, `"payments"`) |
| `path` | string | Relative path to the module root directory |
| `description` | string | 1-line description of what this module does |
| `files` | string[] | Relative file paths belonging to this module |
| `keywords` | string[] | Domain keywords extracted from file names, exports, and comments |
| `entry_points` | string[] | Key files: index files, main exports, API handlers |
| `dependencies` | string[] | Other module names this module imports from |
| `import_rank` | number | Graph-based importance score (average of file import_ranks in this module) |

## `file_index{}` Object

A flat lookup keyed by relative file path. Each value contains:

| Field | Type | Description |
|-------|------|-------------|
| `module` | string | Which module this file belongs to |
| `type` | string | File type classification (see File Type Enum below) |
| `exports` | string[] | Named exports from this file (**top 10 only**) |
| `imports_from` | string[] | Internal file paths this file imports from |
| `imported_by` | string[] | File paths that import this file (**top 20 only**) |
| `import_rank` | number | File-level importance — count of unique files that import this file |

## `domain_concepts{}` Object

Maps domain terms to arrays of relevant file paths.

- **Key:** Domain concept string (e.g., `"loyalty-points"`, `"order-checkout"`, `"user-auth"`)
- **Value:** Array of relative file paths related to this concept

See SKILL.md Step 7 for the extraction algorithm.

## File Type Enum

Every file in `file_index` is classified as one of:

| Type | Typical Patterns |
|------|-----------------|
| `component` | React components (`*.tsx` in `components/`) |
| `hook` | Custom React hooks (`use*.ts`) |
| `service` | Business logic services (`*-service.ts`, `services/`) |
| `utility` | Helper functions (`utils/`, `helpers/`) |
| `type` | TypeScript type definitions (`types/`, `*.d.ts`) |
| `test` | Test files (`*.test.*`, `*.spec.*`, `__tests__/`) |
| `config` | Configuration files (`*.config.*`, `serverless.yml`) |
| `style` | Style files (`*.css`, `*.scss`, `styled.*`) |
| `schema` | Schema definitions (`*.schema.*`, `*.graphql`) |
| `migration` | Database migrations (`migrations/`) |
| `handler` | Lambda/API handlers (`handler.*`, `handlers/`) |
| `middleware` | Express/server middleware (`middleware/`) |
| `constant` | Constants and enums (`constants.*`, `enums.*`) |
| `unknown` | Files that don't match any pattern above (fallback) |

## Size Constraints

To keep the index compact for large repos:

- `exports` array: **capped at 10** per file (top 10 by usage frequency)
- `imported_by` array: **capped at 20** per file (top 20 by import_rank of the importing file)
- External dependencies (node_modules) are excluded from `imports_from` and `imported_by`

## Example

A minimal index for a small repo with 3 files:

```json
{
  "version": "1.0",
  "generated_at": "2026-03-03T10:00:00.000Z",
  "repo_root": ".",
  "git_head": "abc1234def5678",
  "stats": {
    "total_files": 3,
    "total_modules": 1,
    "build_duration_ms": 450,
    "index_size_bytes": 1024
  },
  "modules": [
    {
      "name": "auth",
      "path": "src/auth",
      "description": "User authentication and session management",
      "files": [
        "src/auth/auth-service.ts",
        "src/auth/auth-middleware.ts",
        "src/auth/types.ts"
      ],
      "keywords": ["auth", "login", "session", "token", "user"],
      "entry_points": ["src/auth/auth-service.ts"],
      "dependencies": [],
      "import_rank": 3
    }
  ],
  "file_index": {
    "src/auth/auth-service.ts": {
      "module": "auth",
      "type": "service",
      "exports": ["AuthService", "createSession", "validateToken"],
      "imports_from": ["src/auth/types.ts"],
      "imported_by": ["src/auth/auth-middleware.ts", "src/routes/login.ts"],
      "import_rank": 2
    },
    "src/auth/auth-middleware.ts": {
      "module": "auth",
      "type": "middleware",
      "exports": ["authMiddleware"],
      "imports_from": ["src/auth/auth-service.ts"],
      "imported_by": ["src/app.ts"],
      "import_rank": 1
    },
    "src/auth/types.ts": {
      "module": "auth",
      "type": "type",
      "exports": ["User", "Session", "AuthConfig"],
      "imports_from": [],
      "imported_by": ["src/auth/auth-service.ts"],
      "import_rank": 1
    }
  },
  "domain_concepts": {
    "authentication": [
      "src/auth/auth-service.ts",
      "src/auth/auth-middleware.ts"
    ],
    "session": [
      "src/auth/auth-service.ts",
      "src/auth/types.ts"
    ]
  }
}
```
