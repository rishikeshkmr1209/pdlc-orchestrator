Build a persistent codebase index for targeted exploration.

Arguments: $ARGUMENTS

**IMPORTANT:** Do NOT attempt to read or locate skill files. Instead, use the `Skill` tool to invoke skills by name.

To build the index, invoke the `build-codebase-index` skill using the Skill tool:

```
Skill: client-master:build-codebase-index
Args: $ARGUMENTS
```

The `build-codebase-index` skill accepts these arguments:
- `--path=<repo-path>` — target repository path (defaults to current directory)
- `--force` — force full rebuild even if index exists and is fresh

The skill scans the target repo's file structure, imports, and naming conventions
to generate:
- `.claude/codebase-index/index.json` — programmatic index for queries
- `.claude/codebase-index/repo-map.md` — compact LLM-readable repo map

Invoke the skill now with the arguments provided above.
