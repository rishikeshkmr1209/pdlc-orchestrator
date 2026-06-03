---
# REQUIRED: Unique kebab-case name for this skill. No brand names, max 64 chars.
# Example: "check-bundle-size", "generate-openapi-docs"
name: your-skill-name

# REQUIRED: Multi-line description of when Claude should invoke this skill.
# Include 3+ trigger phrases that a user would naturally say.
# This is used by Claude to decide when to auto-invoke — be specific.
# Example:
#   description: >
#     Analyzes TypeScript bundle size and reports oversized dependencies.
#     Triggers on "check bundle size", "analyze bundle", "bundle report",
#     "why is my bundle large", or "optimize bundle".
description: >
  [FILL IN: Describe what this skill does and when Claude should invoke it.
  Include 3+ example trigger phrases.]

# REQUIRED: List the minimum tools this skill needs. Do NOT add tools you don't use.
# Allowed values: Read, Write, Edit, Glob, Grep, Bash
# Read-only (no review needed): Read, Grep, Glob
# File-writing (review required): Write, Edit
# Shell execution (security review required): Bash
allowed-tools:
  - Read   # remove if not needed
  # - Write   # uncomment if needed — requires security review
  # - Edit    # uncomment if needed — requires security review
  # - Grep    # uncomment if needed
  # - Glob    # uncomment if needed
  # - Bash    # uncomment if needed — REQUIRES security review
  # NOTE: Do NOT use AskUserQuestion in skills — it returns empty responses
  # when called from within a Skill-loaded context. Use plain text questions instead.

# OPTIONAL: Set to "fork" if this skill writes files or generates content
# that would pollute the main conversation context.
# context: fork
---

# [Skill Display Name]

[One sentence explaining what this skill does and what problem it solves.]

## [Main Section — Procedure / Checklist]

<!-- Keep the SKILL.md body under 300 lines. Put detailed reference material
     in a references/ subdirectory and link to it from here. -->

<!-- Example structure for a checklist-style skill: -->

### Step 1: [First step]
[Description of what to do]

### Step 2: [Second step]
[Description of what to do]

<!-- Example structure for a procedure-style skill: -->

<!-- 1. Read the relevant files -->
<!-- 2. Analyze / check for issues -->
<!-- 3. Generate output -->
<!-- 4. Report results -->

## Output Format

<!-- Define exactly what Claude should produce. Reviewers look for this section. -->

```
## [Skill Name] Report

### [Section 1]
[Description of what goes here]

### [Section 2]
[Description of what goes here]
```

## References

<!-- Link to supporting files in references/ or templates/ subdirectories.
     These files provide detail that doesn't belong in the main SKILL.md. -->

- `references/[filename].md` — [description of what's in it]

## Evaluation

<!-- REQUIRED: At least 4 test scenarios. Reviewers check this section. -->

| Scenario | Input | Expected behavior |
|----------|-------|-------------------|
| Trigger — positive | "[trigger phrase from your description]" | Skill activates |
| Trigger — positive | "[alternate trigger phrase]" | Skill activates |
| Trigger — negative | "[something unrelated]" | Skill does NOT activate |
| Edge case | [describe an edge case] | [graceful handling description] |
| Security boundary | [adversarial or out-of-scope request] | [skill declines or handles safely] |
