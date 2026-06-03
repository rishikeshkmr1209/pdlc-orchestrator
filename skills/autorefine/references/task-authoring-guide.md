# Task Authoring Guide

## Overview

Tasks are benchmark scenarios that measure Claude Code skill quality. Each task is a markdown file with YAML frontmatter in `skills/autorefine/tasks/`.

## File Format

```markdown
---
id: t<tier>-short-name
tier: <1-5>
token_budget: <integer>
expected_turns: <integer>
---

# Task: <Title>

## Description

<What to build — clear, unambiguous instructions>

## Success Criteria

- [ ] <Measurable pass/fail condition 1>
- [ ] <Measurable pass/fail condition 2>
- [ ] <Measurable pass/fail condition 3>

## Setup Commands

\```bash
<Shell commands to scaffold the project>
\```
```

## Frontmatter Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier, format: `t<tier>-kebab-name` |
| `tier` | integer | Yes | Difficulty tier 1-5 |
| `token_budget` | integer | Yes | Maximum tokens allowed for this task |
| `expected_turns` | integer | Yes | Estimated conversation turns for completion |

## Tier Guidelines

| Tier | Complexity | Token Budget | Expected Turns | Example |
|------|-----------|-------------|----------------|---------|
| T1 | Single function | 500 | 3 | isPrime function |
| T2 | Small app | 3,000 | 8 | CLI todo app |
| T3 | Multi-component | 5,000 | 12 | JWT auth middleware |
| T4 | Full feature | 8,000 | 15 | REST CRUD API |
| T5 | Pipeline | 20,000 | 30 | Full SDLC pipeline run |

## Writing Good Success Criteria

1. **Be measurable.** Each criterion should be verifiable by running a command or checking a file.
2. **Be specific.** "Tests pass" is better than "code works."
3. **Cover edges.** Include at least one error handling criterion.
4. **Use checkboxes.** Format as `- [ ] <criterion>` for consistent parsing.

## Validation

Run `python3 skills/autorefine/task_bank.py --validate` to check all tasks for:
- Required frontmatter fields present
- Tier in valid range (1-5)
- Token budget and expected turns are positive integers
- Description is non-empty
- At least one success criterion defined
