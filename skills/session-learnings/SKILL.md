---
name: session-learnings
user-invocable: false
description: >
  Use when user says "capture learnings", "session learnings",
  "update instructions", invokes /learnings command, or when auto-invoked
  by session-learnings-check Stop hook after repeated corrections.
allowed-tools:
  - Read
  - Grep
  - Glob
  - Edit
  - Write
  - Bash
---

# Session Learnings Skill

You are analyzing the current conversation to extract behavioral learnings
that should be persisted into the project's CLAUDE.md file so future sessions
do not repeat the same mistakes.

## Research-Backed Principle (arxiv:2602.11988)

Context files that are too verbose HURT agent performance and increase costs.
Every instruction you propose must pass the **Minimality Test**:

> "Would removing this instruction cause the agent to make the same mistake
> again in a future session?"

If the answer is no — do NOT add it. Prefer zero updates over bloated ones.

## Step 1: Scan the Conversation for Learning Signals

Read through the full conversation history and identify instances of:

| Signal | Pattern | Example |
|--------|---------|---------|
| **Repeated correction** | User says the same thing 2+ times | "I already told you to..." |
| **Escalation language** | User pushes for more effort | "think harder", "be more thorough", "check everything" |
| **Missed workflow step** | User points out a forgotten step | "you forgot to run the install script" |
| **Wrong tool/approach** | User redirects to a different tool | "use osgrep not grep", "use podman not docker" |
| **Style correction** | User corrects output format/style | "don't add emojis", "be more concise" |
| **Missing knowledge** | Agent didn't know a project convention | Tool paths, naming conventions, deployment steps |

For each signal found, record:
- **What happened**: one-sentence description
- **Root cause**: why the agent got it wrong (missing instruction? ignored instruction? incomplete thinking?)
- **Proposed fix**: the minimal instruction that would prevent this in the future

## Step 2: Check Existing Instructions

Before proposing any update, read the current CLAUDE.md files:

1. Read the project CLAUDE.md (the one being updated)
2. Read the global `~/.claude/CLAUDE.md`

For each proposed instruction, check:
- Is it **already covered**? If yes, skip — the issue was ignoring it, not missing it.
- Does it **contradict** an existing instruction? If yes, flag for user decision.
- Is it **too specific** to this one session? If yes, generalize or skip.
- Is it **already obvious** from general best practices? If yes, skip.

## Step 3: Draft the Update

Format each proposed addition as:

```
### [Section Name]

- **Instruction**: [The minimal, imperative instruction]
- **Reason**: [One line — what went wrong without this]
- **Signal**: [Quote from conversation that triggered this]
```

Rules for the instruction text:
- **Imperative mood**: "Always run X after Y" not "You should consider running X"
- **Specific and actionable**: "Check required `##` section headers exist after modifying SDLC artifacts" not "Remember to validate artifacts"
- **No filler**: No "please", "remember to", "it's important to" — just the instruction
- **Under 2 sentences**: If it needs more, it's too complex for CLAUDE.md — make it a skill instead

## Step 4: Present to User for Approval

Show the user:

```
## Session Learnings Report

### Signals Detected
[Bulleted list of learning signals found]

### Proposed CLAUDE.md Updates
[Each proposed instruction with reason]

### Skipped (already covered or too specific)
[Any signals that don't warrant a CLAUDE.md change]
```

**Do NOT auto-edit CLAUDE.md.** Wait for user approval on each proposed instruction.

## Step 5: Apply Approved Updates

After user approves:
1. Edit the project CLAUDE.md with approved instructions
2. Place them in the most relevant existing section, or create a new section only if no existing section fits
3. Keep the file organized — do not create a "Session Learnings" dump section
4. Verify the edit didn't break markdown formatting

## Anti-Patterns (DO NOT do these)

- Adding instructions the user never corrected you on — that's speculation
- Adding verbose explanations — CLAUDE.md is not documentation
- Adding instructions that duplicate existing ones in different words
- Creating a "lessons learned" or "session notes" section — integrate into existing structure
- Adding more than 5 instructions from a single session — if there are more, prioritize the top 5 by frequency/severity

## Evaluation

| Scenario | Expected behavior |
|----------|-------------------|
| User corrected tool choice twice | Propose one instruction about the correct tool |
| User said "think harder" once | Propose instruction about comprehensive-first approach for that category |
| User corrected a workflow step | Propose instruction about the specific workflow |
| No corrections in session | Report "No learning signals detected" — propose nothing |
| Proposed instruction already exists | Skip it, note in "Skipped" section |
| 10+ learning signals | Prioritize top 5 by frequency, note the rest as skipped |
