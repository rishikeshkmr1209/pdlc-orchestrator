# Parallel Reads Rule

## MANDATORY: Batch All Reads Before Any Writes

In your **first response**, issue ALL file reads and tool calls needed for this phase **in parallel**. Do not read one file, analyse it, then decide to read another.

**Why:** Every model turn re-reads the full accumulated conversation context from cache. Sequential reads multiply cache_read tokens with each turn as context grows. Batching all reads into one turn keeps context small during the read phase, reducing both token cost and execution time by ~20%.

### How to Apply

**DO:**
```
Turn 1: Read file_A, file_B, file_C, file_D — all in parallel
Turn 2: Analyse all results together
Turn 3+: Write / Edit based on analysis
```

**DO NOT:**
```
Turn 1: Read file_A
Turn 2: Read file_B  ← re-reads file_A result from cache
Turn 3: Read file_C  ← re-reads file_A + file_B from cache
...
```

### Deciding What to Read Upfront

Before making any tool calls, scan the phase instructions and identify every file, artifact, or resource the phase will need. Read them all in the first turn. The list is always deterministic from the phase inputs — there is no need to read one file to decide what to read next.

### Exception: Implementation Edits

When editing files sequentially (Edit tool), reads and writes may interleave — this is unavoidable. Apply this rule to the **planning reads** at the start of the phase: read all files listed in the implementation plan upfront in one batch before making any edits.

### Exception: Conditional Reads

If a file is only needed based on a runtime condition (e.g., "read this only if the ticket has a Figma link"), check the condition first (1 turn), then read all conditionally-needed files together in the next turn.
