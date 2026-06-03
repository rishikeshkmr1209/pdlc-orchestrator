---
name: invalid-tools
description: >
  This skill has an unrecognized tool name in allowed-tools.
allowed-tools:
  - Read
  - FooBar
  - Grep
---

# Invalid Tools Skill

Has an unrecognized tool name.

## Evaluation

| Scenario | Input | Expected behavior |
|----------|-------|-------------------|
| Test | "test" | Warns about FooBar |
