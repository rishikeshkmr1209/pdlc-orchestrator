---
# REQUIRED: Unique kebab-case name. Should describe the role, not the technology.
# Example: "database-optimizer", "api-designer"
# Agent files are prefixed with numbers for ordering: 10-your-agent-name.md
name: your-agent-name

# REQUIRED: Multi-line description of when to invoke this agent.
# Be specific — Claude uses this to decide when to delegate to this agent.
# Include the types of tasks, input artifacts, and output this agent produces.
# Example:
#   description: >
#     Analyzes AWS cost and usage data to identify optimization opportunities.
#     Invoke when asked to review cloud costs, find unused resources, or
#     reduce AWS spend. Produces a prioritized list of cost reduction actions.
description: >
  [FILL IN: What does this agent do? When should it be invoked?
  What inputs does it work with? What does it produce?]

# REQUIRED: Minimum tools this agent needs. Follow least-privilege rules.
# Read-only: Read, Grep, Glob
# File-writing (requires security review): Write, Edit
# Shell execution (requires security review): Bash
tools:
  - Read    # remove if not needed
  # - Grep  # uncomment if needed
  # - Glob  # uncomment if needed
  # - Write # requires security review
  # - Edit  # requires security review
  # - Bash  # requires security review

# REQUIRED: Always set to "inherit". Never hardcode model IDs.
model: inherit
---

You are the [role name] agent. Your role is to [one sentence describing what this agent does for engineers].

## [Role] Philosophy

<!-- 3-5 guiding principles for how this agent approaches its work.
     These should be stable values, not task-specific instructions. -->

- **[Principle 1]:** [Description]
- **[Principle 2]:** [Description]
- **[Principle 3]:** [Description]

## [Core Framework / Checklist]

<!-- The main body of the agent's expertise.
     This can be a checklist, a structured analysis framework, or a procedure.
     Aim for depth here — this is the agent's primary value. -->

### [Category 1]
- [ ] [Check or step]
- [ ] [Check or step]

### [Category 2]
- [ ] [Check or step]
- [ ] [Check or step]

## Agent Workflow

<!-- Numbered procedure the agent follows when invoked. -->

1. **[First action]** — [what the agent does first and why]
2. **[Second action]** — [what comes next]
3. **[Analysis]** — [how the agent processes the information]
4. **[Output]** — [what the agent produces]

## Output Format

<!-- Define the structure of the agent's output so it's consistent and useful. -->

```
## [Agent Name] Report: [subject]

### Summary
[Brief overall assessment]

### [Finding Category 1]
[What goes here]

### [Finding Category 2]
[What goes here]

### Recommendations
1. [Priority recommendation]
2. [Next recommendation]
```

## What This Agent Does NOT Do

<!-- Scope limits are important. What should this agent decline or redirect? -->

- Does not [out-of-scope action 1] — refer to [other agent/resource]
- Does not [out-of-scope action 2]
- Will not [safety boundary]
