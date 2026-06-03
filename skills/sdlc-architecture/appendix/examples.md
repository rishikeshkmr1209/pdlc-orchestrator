# Architecture Skill — Examples & Output Templates

This file contains the Markdown output template and refinement mode details for the sdlc-architecture skill.
Read this file only if you need format guidance for producing `ph2_design_spec.md`.

---

## Output File Structure

The `ph2_design_spec.md` MUST contain these top-level sections:

```markdown
## Meta

- **Feature ID:** FEAT-0001
- **Ticket ID:** TICKET-1234
- **Created At:** ISO-8601 timestamp
- **Agent Version:** 2.0
- **Problem Spec Version:** hash or version string
- **Codebase Location:** /absolute/path or null
- **Codebase Analyzed:** true
- **Implementation Status:** not_started
- **Brands:** BK, PLK, FHS, TH

## Problem Spec Reference

See `ph1_problem_spec.md`.

## Current Architecture

### Description
...

### Existing Components
- ...

### Existing Patterns
- ...

### Integration Points
- ...

## Architecture

- **Pattern:** container_presenter
- **Components:** ...
- **Data Flow:** ...

## API Contracts

### GraphQL

#### Queries
- ...

#### Mutations
- ...

### Hooks
- ...

## Data Models

### Types
- ...

### State Shape
(nested object description)

## Decisions
- ...

## Implementation Guidelines

### File Structure
- ...

### Naming Conventions
(key-value conventions)

### Patterns to Use
- ...

### Patterns to Avoid
- ...

### Libraries
- ...

## Testing Strategy

- **Unit Test Targets:** ...
- **Integration Test Targets:** ...
- **E2E Scenarios:** ...
- **Coverage Target:** 85

## Security Considerations
- ...
```

---

## Refinement Mode — When to Push Back

**Valid reasons to reject feedback:**
- Out of scope for this iteration
- Over-engineering for current requirements
- Premature optimization without evidence
- Incorrect context (reviewer misunderstood existing codebase)

**Invalid reasons to reject feedback:**
- "Too much work" for critical issues
- "We will fix it later" for security or data loss
- "It is probably fine" without evidence
- "The old way works" when it demonstrably does not scale

---

## Handling Requirement Issues

If you find issues with the `ph1_problem_spec.md`, do NOT fix them. Add a `## Flags` section:

```markdown
## Flags

### Flag 1
- **Type:** ambiguity
- **Requirement ID:** REQ-003
- **Issue:** Unclear what 'previously saved customizations' means
- **Suggestion:** Clarify: use default customizations or prompt user?

### Flag 2
- **Type:** missing_requirement
- **Requirement ID:** (none)
- **Issue:** No requirement for maximum items limit
- **Suggestion:** Add REQ-006 for limit handling
```

Flag types: `ambiguity`, `missing_requirement`, `contradiction`, `infeasible`, `out_of_scope`
