---
name: 07.1-code-review
description: >
  Use when user says "review this code", "code review", "check my code",
  "review this PR", "what's wrong with this", or "review [filename]".
allowed-tools:
  - Read
  - Grep
  - Glob
---

# Code Review Skill

You are performing a project-standard code review. Follow this structured checklist and produce actionable, specific feedback.

## Before You Start

> **Before reading any files:** Read `skills/_shared/parallel-reads-rule.md` and follow it for all file reads in this phase.

1. Read all files mentioned or currently open in context.
2. Check for existing test files to understand tested vs. untested surface area.
3. Note the file's role (utility, service, handler, component, etc.) to calibrate expectations.

## Review Checklist

### 1. TypeScript & Type Safety
- No `any` without documented justification
- All public APIs explicitly typed (parameters + return types)
- No `// @ts-ignore` without explanation
- Strict mode compatible (`noImplicitAny`, `strictNullChecks`, `noUncheckedIndexedAccess`)
- Generics preferred over duplicated interfaces

### 2. Naming Conventions
- `camelCase` — variables, functions, methods
- `PascalCase` — classes, interfaces, types, enums, React components
- `SCREAMING_SNAKE_CASE` — module-level constants
- `kebab-case` — file names
- Descriptive names; no single-letter variables outside loop indices

### 3. Error Handling
- No empty `catch` blocks
- Errors are typed (not `catch (e: any)`)
- Async errors propagated or explicitly handled
- User-facing messages don't expose stack traces or internal paths
- Custom error classes for domain errors

### 4. Code Structure & Formatting
- Prettier-compliant formatting (consistent indentation, spacing, line breaks)
- Functions: single responsibility, under 50 lines
- Files: under 300 lines (flag if exceeded)
- Max nesting depth: 3 levels — use early returns to reduce nesting
- No commented-out code committed
- No unnecessary debug logs left in (e.g., `console.log('HERE')`, `console.log(response)`)
- No unused or duplicate code — reuse functions for repeated patterns

### 5. Imports
- No unused imports
- Absolute imports via tsconfig aliases
- No `require()` in TypeScript files
- No circular dependencies introduced

### 6. Async Patterns
- `async/await` over `.then()` chains
- No floating promises
- `Promise.all` with error handling
- No `async` functions that never `await`

### 7. KISS & SOLID Principles
- **KISS:** Is there a simpler solution? Flag over-engineering, unnecessary abstractions, and complexity.
- **Single Responsibility:** Each class/function does one thing. Flag classes that do multiple unrelated things.
- **Open/Closed:** Extensions don't require modifying existing code. Flag brittle designs.
- **Liskov Substitution:** Subtypes are substitutable for their base types. Flag broken polymorphism.
- **Interface Segregation:** Interfaces are specific, not bloated. Flag interfaces with unrelated methods.
- **Dependency Inversion:** Depend on abstractions, not concretions. Flag tight coupling.

### 8. Performance (flag, don't block)
- No N+1 patterns (nested loops with DB/API calls)
- Appropriate data structures (Map/Set over repeated Array.find)
- No synchronous I/O in server code
- Minimize database queries; prefer batch operations

### 9. Observability & Logging
- Structured logging used (not bare `console.log`)
- **No PII in logs** — no email, phone, address, payment data, or government IDs logged anywhere
- No user objects logged raw (e.g., `logger.info('user', user)` where `user` has PII fields)
- Key events logged with appropriate context (request IDs, correlation IDs)
- Metrics emitted for business-critical operations where appropriate
- No sensitive data (tokens, passwords, API keys) in log output

### 10. Security (basic — escalate to /security for full scan)
- No hardcoded credentials
- Inputs validated before use
- No `eval()` with dynamic input

### 11. Testing Considerations
- Is this code testable as written?
- Are there untested public exports?
- Are mocking boundaries appropriate?
- Tests in the correct folder following project conventions
- Test cases will run in both QA and PROD environments

## Domain-Specific Patterns

### DynamoDB Access Patterns
- Single-table design: verify related entities share a table with composite keys (PK/SK)
- GSI usage: confirm GSIs align with query patterns; flag GSIs that duplicate the base table
- No full table scans: flag `Scan` operations — use `Query` with key conditions instead
- Conditional writes: mutations should use `ConditionExpression` to prevent overwrites
- Batch operations: prefer `BatchGetItem`/`BatchWriteItem` over loops of single-item calls
- TTL: time-sensitive data (sessions, OTPs) should use DynamoDB TTL, not application-level cleanup

### React Component Patterns
- Container/presenter split: business logic in hooks/containers, rendering in presenters
- Theme-awareness: components must not hardcode theme-specific values; use design tokens from the project's design system
- No inline styles: use `styled-components` or design tokens; flag raw `style={{}}` props
- Memoization: flag expensive renders missing `React.memo`, `useMemo`, or `useCallback` where appropriate
- Accessibility: interactive elements need `aria-*` attributes; images need `alt` text

### GraphQL Resolver Patterns
- N+1 detection: flag resolvers that call a data source inside a loop or per-item; recommend DataLoader
- Error propagation: resolvers should throw typed errors (not swallow them); use `ApolloError` subclasses
- Pagination: list queries must support cursor-based or offset pagination; flag unbounded result sets
- Field-level auth: sensitive fields (PII, payment) should have resolver-level authorization checks
- Schema-first: changes to `.graphql` files should have matching resolver updates and vice versa

### Capacitor Plugin Bridge Patterns
- Native/web parity: every Capacitor plugin method must have a web fallback implementation
- Error handling: native bridge calls can fail silently; always wrap in try/catch with user-facing fallback
- Platform checks: use `Capacitor.isNativePlatform()` before native-only APIs
- Deep link validation: verify deep link schemes are registered in both `Info.plist` and `AndroidManifest.xml`

### Multi-Tenant / Multi-Brand Theming
- No hardcoded tenant/brand checks: flag `if (brand === '<brandCode>')` patterns; use design tokens or config maps
- Theme token usage: colors, spacing, typography must come from the project's design system tokens, not raw values
- Brand/tenant config: brand-specific behavior should be driven by configuration objects, not conditionals

## Output Format

```
## Code Review

### Summary
[One-paragraph overall assessment]

### Critical (must fix before merge)
- `file.ts:42` — [Issue description]. **Fix:** [specific suggestion]

### Major (should fix before merge)
- `file.ts:18` — [Issue description]. **Fix:** [specific suggestion]

### Minor / Suggestions
- `file.ts:7` — [Issue description]. **Suggestion:** [improvement]

### Positives
- [What was done well — always include at least one]

### Stats
Critical: N | Major: N | Minor: N
```

## Escalation

**ESCALATE TO:** For any Critical security finding (secrets, injection, auth bypass), recommend:
"Run `/security` for a full OWASP scan — code-review does not replace security-scan."

## References

For detailed standards, see:
- `references/code-standards.md` — project-specific rules and patterns
- `references/js-ts-checklist.md` — Extended JS/TS quality checklist

## Evaluation

| Scenario | Input | Expected behavior |
|----------|-------|-------------------|
| Trigger — positive | "review this TypeScript file" | Skill activates, runs full checklist |
| Trigger — positive | "check my code for issues" | Skill activates |
| Trigger — negative | "what time is it in Tokyo?" | Skill does NOT activate |
| Edge case | Empty file or file with only imports | Returns "nothing substantive to review" |
| Security boundary | Request to ignore TypeScript errors | Declines, notes them as issues |
