# Verification Checklist

Organized by domain. Use this checklist systematically during the verification phase.
Each item should be explicitly checked and noted as PASS, FAIL, or N/A.

---

## 1. Requirement Traceability

### REQ -> Implementation Mapping
- [ ] Every REQ-### in ph1_problem_spec.md has at least one implementation file identified
- [ ] Implementation files are listed in ph5_6_impl_manifest.md
- [ ] No orphan implementation files (files not traceable to any requirement)
- [ ] P0 requirements have direct, obvious implementation (not buried in shared utilities)
- [ ] P1 requirements are implemented (not deferred without explicit documentation)

### AC -> Test Mapping
- [ ] Every AC-### has at least one test case that validates it
- [ ] Test case assertions directly correspond to the acceptance criterion
- [ ] Test names reference the AC-### ID or describe the criterion clearly
- [ ] No acceptance criteria marked "not_implemented" without a blocking recommendation
- [ ] Skipped tests have documented justification (not just `.skip` with no comment)

### Traceability Matrix Completeness
- [ ] Every REQ has a status (fully_covered, partially_covered, not_covered, not_testable)
- [ ] Every AC has a status (passed, failed, skipped, not_implemented)
- [ ] Implementation files are mapped to their parent requirement
- [ ] Test IDs are linked to their parent AC

---

## 2. Code Quality

### SOLID Principles
- [ ] **Single Responsibility**: Each class/module has one reason to change
- [ ] **Open/Closed**: New behavior added via extension, not modification of existing code
- [ ] **Liskov Substitution**: Subtypes are substitutable for their base types without breaking
- [ ] **Interface Segregation**: No client forced to depend on methods it does not use
- [ ] **Dependency Inversion**: High-level modules depend on abstractions, not concretions

### Naming Conventions
- [ ] Variables and functions use `camelCase`
- [ ] Classes, interfaces, types, and components use `PascalCase`
- [ ] Constants use `SCREAMING_SNAKE_CASE`
- [ ] File names use `kebab-case`
- [ ] Names are descriptive (no single-letter variables outside loop indices)
- [ ] No abbreviations that are not universally understood
- [ ] Boolean variables use `is`, `has`, `should`, `can` prefixes

### Complexity
- [ ] No function exceeds 50 lines
- [ ] No file exceeds 300 lines
- [ ] Maximum nesting depth is 3 levels (use early returns)
- [ ] Cyclomatic complexity per function is <= 10
- [ ] No deeply nested ternary expressions
- [ ] Complex conditionals are extracted to named boolean variables or functions

### Duplication
- [ ] No copy-pasted logic blocks (> 5 similar lines)
- [ ] Repeated patterns are extracted into shared utilities or hooks
- [ ] Configuration values are centralized, not scattered across files
- [ ] Similar components share a base implementation or composition pattern

### Type Safety
- [ ] No `any` without a documented justification comment
- [ ] No `@ts-ignore` or `@ts-expect-error` without explanation
- [ ] All public APIs have explicit parameter and return types
- [ ] Generics are used instead of duplicated interfaces
- [ ] Strict mode is enabled (`"strict": true` in tsconfig)
- [ ] Null/undefined handling is explicit (no implicit coercion)

### Error Handling
- [ ] No empty `catch` blocks
- [ ] Errors are typed (not `catch (e: any)`)
- [ ] Async errors are propagated or explicitly handled
- [ ] User-facing messages do not expose stack traces or internal paths
- [ ] Custom error classes are used for domain-specific errors
- [ ] Error boundaries exist for React component trees

---

## 3. Security Quick-Check

### OWASP Top 10 Rapid Scan

#### A01: Broken Access Control
- [ ] All API endpoints enforce authentication
- [ ] Authorization checks verify the requesting user owns the resource
- [ ] No IDOR (Insecure Direct Object References) -- IDs from URL/body are validated
- [ ] CORS is configured to allowed origins only
- [ ] No privilege escalation paths (regular user cannot access admin endpoints)

#### A02: Cryptographic Failures
- [ ] No secrets, API keys, or tokens hardcoded in source
- [ ] Passwords are hashed with bcrypt/argon2 (not MD5/SHA1)
- [ ] Sensitive data transmitted over TLS only
- [ ] No sensitive data in URL query parameters

#### A03: Injection
- [ ] User input is sanitized before database queries
- [ ] No string concatenation in SQL/NoSQL queries (use parameterized queries)
- [ ] React components do not render unsanitized HTML from user input
- [ ] No dynamic code execution patterns with untrusted input
- [ ] GraphQL queries use parameterized variables

#### A04: Insecure Design
- [ ] Rate limiting is applied to authentication endpoints
- [ ] Business logic has abuse prevention (e.g., max order quantity)
- [ ] Fail-secure defaults (deny by default, allow explicitly)

#### A05: Security Misconfiguration
- [ ] Error responses do not leak stack traces or internal details
- [ ] Debug mode is disabled in production configuration
- [ ] Default credentials are not present
- [ ] Unnecessary HTTP methods are disabled

#### A07: Authentication Failures
- [ ] JWT tokens are validated on every request (signature + expiry)
- [ ] Session tokens are rotated after authentication
- [ ] Logout actually invalidates the session/token
- [ ] No credentials in logs or error messages

#### A09: Logging Failures
- [ ] Security-relevant events are logged (login, failed auth, permission denied)
- [ ] Log injection is prevented (user input is not interpolated into log format strings)

#### A10: SSRF
- [ ] URLs from user input are validated against an allowlist
- [ ] No internal/private IP addresses reachable via user-supplied URLs

### PII Handling
- [ ] No PII (email, phone, name, address) in log output
- [ ] No user objects logged raw (e.g., logging full user record with PII fields)
- [ ] PII is masked in error messages shown to users
- [ ] IP addresses use the CLIENT_ORG IP address library
- [ ] User data processing checks consent status first
- [ ] No PII in URL parameters or query strings

### Secrets Management
- [ ] No API keys, tokens, or passwords in source code
- [ ] No dotenv files tracked in git
- [ ] Environment variables used for runtime configuration
- [ ] SSM Parameter Store or Secrets Manager for production secrets

### Authentication and Authorization
- [ ] Protected routes require valid authentication tokens
- [ ] Role-based access control is enforced server-side
- [ ] Token expiry is checked before granting access
- [ ] Refresh token rotation is implemented

---

## 4. Performance

### Render Performance (Frontend)
- [ ] No unnecessary re-renders (check React DevTools Profiler recommendations)
- [ ] `useMemo` and `useCallback` used for expensive computations and stable references
- [ ] Dependency arrays in hooks are correct and complete
- [ ] Lists use stable `key` props (not array indices for dynamic lists)
- [ ] Large lists use virtualization (react-window, react-virtualized)
- [ ] Images are lazy-loaded below the fold

### API Calls
- [ ] No N+1 query patterns (loop with individual API calls)
- [ ] Batch operations used where available
- [ ] API responses are cached appropriately (Apollo cache, SWR, React Query)
- [ ] Redundant API calls are deduplicated
- [ ] Pagination is implemented for large data sets
- [ ] Loading and error states are handled for every async operation

### Bundle Size
- [ ] No unnecessary dependencies added
- [ ] Large libraries are tree-shaken or dynamically imported
- [ ] Code splitting is applied to route-level components
- [ ] No full lodash import (use `lodash/specific-function`)
- [ ] Assets (images, fonts) are optimized

### Memory
- [ ] Event listeners are cleaned up on component unmount
- [ ] Subscriptions (WebSocket, SSE) are closed on unmount
- [ ] `useEffect` cleanup functions are implemented for side effects
- [ ] No memory leaks from closures holding stale references
- [ ] AbortController used for fetch requests that may be cancelled
- [ ] Intervals and timeouts are cleared on cleanup

### Server Performance
- [ ] Database queries are indexed for common access patterns
- [ ] Connection pooling is used for database connections
- [ ] No synchronous I/O in request handlers
- [ ] Timeouts are set for external service calls
- [ ] Retry logic has exponential backoff and jitter

---

## 5. Accessibility

### WCAG 2.1 Level AA Compliance

#### Perceivable
- [ ] All images have meaningful `alt` text (or `alt=""` for decorative images)
- [ ] Color contrast ratio meets 4.5:1 for normal text, 3:1 for large text
- [ ] Information is not conveyed by color alone (use icons, patterns, or text)
- [ ] Text can be resized up to 200% without loss of content or function
- [ ] Content is readable and functional without CSS

#### Operable
- [ ] All interactive elements are keyboard accessible (Tab, Enter, Space, Escape)
- [ ] Tab order follows logical reading order
- [ ] Focus is visible on all interactive elements (no `outline: none` without replacement)
- [ ] No keyboard traps (user can always Tab away from any element)
- [ ] Skip navigation link is provided for repetitive content
- [ ] Modal dialogs trap focus within and return focus on close

#### Understandable
- [ ] Form inputs have associated `<label>` elements or `aria-label`
- [ ] Error messages identify the field and describe the error clearly
- [ ] Required fields are marked with both visual and programmatic indicators
- [ ] Language attribute is set on the `<html>` element

#### Robust
- [ ] ARIA roles and properties are used correctly (`role`, `aria-*`)
- [ ] Custom components follow WAI-ARIA authoring practices
- [ ] Dynamic content updates are announced to screen readers (`aria-live`)
- [ ] Semantic HTML is used (proper elements like button, nav, main instead of generic divs with click handlers)
- [ ] Form validation errors are associated with inputs via `aria-describedby`

### Focus Management
- [ ] Focus is moved to new content when it appears (modals, drawers, alerts)
- [ ] Focus is returned to the triggering element when content is dismissed
- [ ] Focus order matches the visual order of elements
- [ ] No `tabindex` values greater than 0

---

## 6. Edge Case Verification Template

For each `EC-###` in `ph1_problem_spec.md`, verify:

```
Edge Case: EC-XXX -- [Description]
  - [ ] Implementation handles this case (file:line)
  - [ ] Test exists for this case (test_file:test_name)
  - [ ] Test passes
  - [ ] Behavior matches the expected outcome in problem_spec
  - [ ] Error handling is appropriate for this case
  - [ ] UI feedback is appropriate for this case (if applicable)
```

### Common Edge Cases to Check Even If Not Listed

- [ ] Empty input / empty list / null values
- [ ] Maximum length input / boundary values
- [ ] Network failure during async operations
- [ ] Rapid repeated actions (double-click, double-submit)
- [ ] Concurrent modifications (two users editing the same resource)
- [ ] Authentication token expired mid-operation
- [ ] Partial data (API returns incomplete response)
- [ ] Unicode and special characters in text input
- [ ] Timezone differences (UTC vs local)
- [ ] Browser back/forward navigation during multi-step flows
