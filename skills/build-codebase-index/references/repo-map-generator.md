# Repo Map Generator

## Purpose

Generates a compact `repo-map.md` from `index.json`. The repo map is the primary artifact the LLM reads during targeted exploration — it provides a human/LLM-readable overview of the codebase structure with key symbols, ordered by importance (graph-ranked).

## Import Extraction — 6 Grep Patterns

Use these Grep patterns to extract import statements from source files. Apply them in order of priority.

| Pattern Name | Matches | Regex |
|---|---|---|
| ES6 named import | `import { Foo } from './bar'` | `^import\s+\{[^}]+\}\s+from\s+['"]([^'"]+)['"]` |
| ES6 default import | `import Foo from './bar'` | `^import\s+\w+\s+from\s+['"]([^'"]+)['"]` |
| ES6 namespace import | `import * as Foo from './bar'` | `^import\s+\*\s+as\s+\w+\s+from\s+['"]([^'"]+)['"]` |
| CommonJS require | `const Foo = require('./bar')` | `require\(['"]([^'"]+)['"]\)` |
| Re-export | `export { Foo } from './bar'` | `^export\s+\{[^}]+\}\s+from\s+['"]([^'"]+)['"]` |
| Re-export all | `export * from './bar'` | `^export\s+\*\s+from\s+['"]([^'"]+)['"]` |

**Implementation note:** Use the Grep tool with each pattern across all indexed source files. Combine results to build the full import graph.

## Path Resolution

After extracting import paths, resolve them to actual file paths:

1. **Relative paths** (`./`, `../`): Resolve against the importing file's directory. Try extensions `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, `.cjs` if the import omits the extension. Also try appending `/index.{ts,tsx,js,jsx}` for directory imports.
2. **Path aliases**: Read `tsconfig.json` → `compilerOptions.paths` to resolve aliases (e.g., `@app/utils` → `src/utils`). If `tsconfig.json` is missing or has no paths, skip alias resolution.
3. **Bare specifiers** (no `./` prefix, not in tsconfig paths): Treat as external (node_modules) — **skip these entirely**.

## Graph Ranking Algorithm

### File-Level Ranking

```
import_rank = len(imported_by)
```

Count the number of unique internal files that import this file. Higher rank = more central to the codebase.

### Module-Level Ranking

```
import_rank = avg(file import_ranks for files in this module)
```

Average of all file-level import_ranks within the module.

### Co-Location Fallback

When a file has 0 imports AND 0 imported_by (isolated file):

- **Sibling heuristic:** `import_rank = max(1, sibling_max_rank * 0.3)` where `sibling_max_rank` is the highest import_rank of any file in the same directory
- **Entry point bonus:** Files named `index.ts`, `main.ts`, `app.ts`, `handler.ts` get a base rank of **5**

## Token Budget

Approximation: **1 token ~ 4 characters**.

| Budget Level | Characters | Tokens (approx) | When Used |
|---|---|---|---|
| Default | 8,000 | ~2,000 | Files already in context |
| Expanded | 16,000 | ~4,000 | No files in context yet |

### Truncation Algorithm

1. Sort modules by `import_rank` descending
2. Within each module, sort files by `import_rank` descending
3. For each module, write the module header and file entries
4. After each entry, check cumulative character count
5. When budget is reached, stop adding files
6. For each truncated module, append: `... and N more files`
7. For completely omitted modules, append a footer: `... and M more modules (N files total)`

## Repo Map Format

The generated `repo-map.md` follows this structure:

```markdown
# Repo Map

Generated: <ISO-8601 timestamp> | Files: <total> | Modules: <total>

## <module-name> (<file-count> files, rank: <import_rank>)
<relative-file-path>:
  <exported-symbol-1>
  <exported-symbol-2>(param: Type): ReturnType
<relative-file-path>:
  <exported-symbol>
... and N more files

## <module-name> (<file-count> files, rank: <import_rank>)
<relative-file-path>:
  <exported-symbol>

... and M more modules (N files total)
```

**Symbol format:**
- Functions: `functionName(param: Type): ReturnType`
- Classes: `class ClassName`
- Types/interfaces: `interface InterfaceName` or `type TypeName`
- Constants: `CONSTANT_NAME`

Only include symbols that are **exported** (appear in the file's `exports` array in index.json).

## Consistency Validation

After generating both artifacts, validate:

1. Every module listed in `repo-map.md` must exist in `index.json` modules array
2. Every file listed in `repo-map.md` must exist in `index.json` file_index
3. File counts in module headers must match or be less than (due to truncation) the module's `files` array length in index.json

If validation fails, log a warning and regenerate the failing artifact.

## Known Limitations

- **Dynamic imports** (`import('./module')`) are not captured by the Grep patterns
- **Path alias resolution** requires `tsconfig.json` — if absent, aliased imports appear as unresolved
- **Barrel files** (`index.ts` re-exporting) are captured via the re-export patterns
- **Conditional requires** (`if (x) require('./y')`) are captured syntactically but may overcount
- **CSS/SCSS imports** (`@import`, `composes`) are not tracked
- **Upgrade path:** If Grep-based extraction proves insufficient, v2 can use `node -e "..."` for AST-based extraction
