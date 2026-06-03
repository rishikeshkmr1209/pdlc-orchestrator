# Claude Plugin Standards

This document defines the naming conventions, YAML frontmatter rules, and tool access standards that all skills, agents, and commands in this repository must follow.

---

## Naming Conventions

### File Names
- **Format:** `kebab-case`
- **Extension:** `.md` for all plugin files
- **Max length:** 64 characters (including extension)
- **Characters:** lowercase letters, numbers, hyphens only — no spaces, underscores, or capitals

| Good | Bad |
|------|-----|
| `aws-lambda-deploy.md` | `AWS_Lambda_Deploy.md` |
| `check-bundle-size.md` | `checkBundleSize.md` |
| `generate-openapi-docs.md` | `Generate OpenAPI Docs.md` |

### Skill Names (frontmatter `name:`)
- Same rules as file names
- Must be unique across all skills in the repository
- Should describe the action, not the tool: `generate-tests` not `jest-runner`
- No brand names: `run-linter` not `eslint-runner`

### Agent Names (frontmatter `name:`)
- Same rules as file names
- Should describe the role: `security-auditor` not `owasp-checker`
- No numbers in the name (numbers are for file ordering only)

### Agent File Ordering
Agent files are prefixed with two-digit numbers for display ordering:
- `01-` through `09-`: core agents (maintained by Platform Engineering)
- `10-` through `19-`: team-contributed agents (after approval)
- `20+`: experimental agents

---

## YAML Frontmatter Rules

All skill and agent files must have valid YAML frontmatter between `---` delimiters.

### Required Fields

#### Skills (SKILL.md)
```yaml
---
name: skill-name            # Required: unique kebab-case identifier
description: >              # Required: multi-line string, when to invoke
  Trigger phrases and use cases. Must include at least 3 trigger examples.
  Used by Claude to decide when to auto-invoke the skill.
allowed-tools:              # Required: explicit list, minimum needed
  - Read
---
```

#### Agents (agent files)
```yaml
---
name: agent-name            # Required: unique kebab-case identifier
description: >              # Required: multi-line, when to invoke this agent
  Specific use cases and trigger conditions.
tools:                      # Required: explicit list
  - Read
model: inherit              # Required: always "inherit" (do not hardcode model IDs)
---
```

### Optional Fields (Skills)
```yaml
context: fork               # "fork" runs the skill in an isolated subagent
                            # Use for skills that write files (generate-tests)
                            # to avoid polluting main conversation context
```

### Forbidden in Frontmatter
- Hardcoded model IDs (`claude-3-5-sonnet-20241022`) — use `model: inherit`
- Hardcoded AWS account IDs, regions, or org-specific URLs
- Credentials or secrets of any kind
- `tools: ["*"]` or wildcard tool lists

---

## Tool Least-Privilege Table

Assign the **minimum** tools required. Reviewers will reject over-permissioned skills.

| Capability | Tools to request | Notes |
|------------|----------------|-------|
| Read and analyze code | `Read, Grep, Glob` | Most read-only operations |
| Find files by pattern | `Glob` | Add `Grep` for content search |
| Generate new files | `Read, Write, Glob, Grep` | Requires security review |
| Edit existing files | `Read, Edit, Glob, Grep` | Requires security review |
| Run shell commands | `Bash` | Requires security review + explicit justification |
| Create GitHub PRs | `Bash` (gh CLI only) | Bash use limited to `gh` commands |
| Full read + write | `Read, Write, Edit, Glob, Grep` | Full justification required in PR |
| Orchestrate sub-skills | `Skill` | Pipeline orchestrator only |

### Tool Definitions

| Tool | What it does | When to use |
|------|-------------|-------------|
| `Read` | Read file contents | Any time you need to see file content |
| `Write` | Create or overwrite files | Only when generating new files is the point |
| `Edit` | Make targeted edits to existing files | Preferred over Write for modifications |
| `Glob` | Find files by name pattern | Finding relevant files before reading |
| `Grep` | Search file contents by pattern | Finding specific code, imports, patterns |
| `Bash` | Execute shell commands | Last resort — justify explicitly |
| `Skill` | Invoke another skill | Pipeline orchestration only |
| `AskUserQuestion` | Present structured questions to user | **Pipeline orchestrator only** — does not work reliably inside skills invoked via the Skill tool (returns empty responses). Skills that need user input should use plain text questions instead. |

---

## Skill Body Guidelines

### Length
- SKILL.md body: **under 300 lines** (excluding frontmatter and Evaluation section)
- If detailed reference material is needed, put it in `references/` and link to it
- If code templates are needed, put them in `templates/` and reference them

### Required Sections
Every SKILL.md must include:
1. A brief intro line explaining the skill's role
2. The core procedure or checklist
3. An output format section (what Claude should produce)
4. A `## Evaluation` section with test scenarios (see below)

### Evaluation Section Format
```markdown
## Evaluation

| Scenario | Input | Expected behavior |
|----------|-------|-------------------|
| Trigger — positive | "[trigger phrase]" | Skill activates |
| Trigger — positive | "[alternate trigger]" | Skill activates |
| Trigger — negative | "[non-trigger phrase]" | Skill does NOT activate |
| Edge case | [edge case description] | [expected graceful handling] |
```

Minimum requirements:
- 2 positive trigger scenarios
- 1 negative (non-trigger) scenario
- 1 edge case

---

## Agent Body Guidelines

### Required Sections
1. Role statement (first paragraph)
2. Operating philosophy (principles, not rules)
3. Detailed procedure or framework
4. Output format
5. What this agent does NOT do (scope limits)

### Agent Scope Rules
- Each agent has a clearly bounded scope
- Agents should NOT overlap significantly with other agents
- Cross-domain concerns should delegate: e.g., a code-reviewer finding a security issue should note it and suggest using the security-auditor

---

## Version History

Changes to this standards document require:
- A PR with changes clearly explained
- 2 approvals from core maintainers
- An update to `docs/ARCHITECTURE.md` if the change reflects a new design decision
