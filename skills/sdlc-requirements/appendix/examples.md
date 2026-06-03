# Requirements Skill — Examples & Output Templates

This file contains output examples and interaction flow examples for the sdlc-requirements skill.
Read this file only if you need format guidance for producing `ph1_problem_spec.md`.

---

## Output Format: ph1_problem_spec.md — Section Examples

### Meta

```markdown
## Meta

- **Feature ID:** FEAT-0042
- **Ticket ID:** TICKET-1234
- **Created At:** 2026-02-25T14:30:00Z
- **Agent Version:** 2.0
- **Source Ticket:** TICKET-1234
- **Brands:** BK, PLK, FHS
```

- `Feature ID`: Auto-generate in format `FEAT-XXXX`. Increment from the highest existing FEAT number in `docs/artifacts/`.
- `Ticket ID`: From the `--ticket` argument.
- `Created At`: ISO 8601 timestamp of when the spec was produced.
- `Agent Version`: Always `2.0`.
- `Source Ticket`: Same as Ticket ID (for cross-referencing).
- `Brands`: Comma-separated list of affected brands. Must be explicitly confirmed, never assumed.

### Problem Statement

```markdown
## Problem Statement

**Summary:** One-line summary of the problem (max 200 chars)

**User Problem:** What pain point does this solve for the end user? (max 500 chars)

**Business Value:** Why does your organization care about solving this? Revenue, retention, compliance? (max 500 chars)
```

- `Summary`: One sentence. A new team member should understand the feature from this alone.
- `User Problem`: Written from the user's perspective. "As a customer, I cannot..." or "Users currently have to..."
- `Business Value`: Quantify if possible. "Reduces checkout abandonment by X%" or "Required for GDPR compliance in EU markets."

### Requirements

```markdown
## Requirements

| ID | Type | Priority | Description | Depends On |
|----|------|----------|-------------|------------|
| REQ-001 | functional | P0 | The system shall allow users to sign in using their Google account. | — |

### Acceptance Criteria

**REQ-001:**

| AC ID | Given | When | Then |
|-------|-------|------|------|
| AC-001 | A user is on the sign-in screen | They tap the 'Sign in with Google' button | The Google OAuth consent screen is displayed |
| AC-002 | A user has completed Google OAuth consent | The OAuth callback is received with a valid token | The user is authenticated and redirected to the home screen |
```

- `ID`: Sequential `REQ-001`, `REQ-002`, etc.
- `Type`: One of `functional`, `non-functional`, `technical`.
  - `functional`: What the system does (user-visible behavior).
  - `non-functional`: How well the system does it (performance, security, accessibility).
  - `technical`: Infrastructure or architectural requirements (logging, monitoring, data migration).
- `Description`: Uses "shall" language. Describes WHAT, not HOW. Max 300 characters.
- `Priority`: `P0` (must-have for launch), `P1` (should-have, can ship without but fix soon), `P2` (nice-to-have, backlog if time runs out).
- `Acceptance Criteria`: Default to exactly 1 per requirement. Given/When/Then format. Each AC must be independently testable. Only add more ACs if the user explicitly requests them during the confirmation step.
- `Depends On`: List of REQ IDs that must be implemented first, or `—` if none.

**Requirement quality rules:**
- Every functional requirement needs at least 1 acceptance criterion.
- P0 requirements: start with 1 AC. Suggest additional ACs (error path) during the draft review, but only add them if the user confirms.
- Non-functional requirements must have measurable criteria (numbers, not "fast" or "secure").
- Technical requirements must specify validation method (how do we know it is done?).
- **Never add ACs the user did not see and approve.** The draft confirmation step is the quality gate for AC completeness.

### Constraints

```markdown
## Constraints

### Performance
- **Response time (p95):** 500 ms
- **Throughput:** 100 rps
- **Max payload:** 256 KB

### Security
- Authentication required
- Encrypt in transit
- GDPR

### Compatibility
- **Browsers:** Chrome 90+, Safari 15+, Firefox 90+, Edge 90+
- **Platforms:** iOS, Android, Web
- **Min OS — iOS:** 15.0
- **Min OS — Android:** 10

### Accessibility
- WCAG 2.1 AA

### Localization
- **Languages:** en, fr, es, de
- **RTL support:** No

### Brands
- BK, PLK, FHS
```

- `Performance`: Use concrete numbers. If unknown, ask. Do not default to arbitrary values.
- `Security`: Select applicable values. If the feature touches user data, authentication required and encrypt in transit are almost always needed.
- `Compatibility`: List specific browser/platform targets. Reference the project's existing support matrix.
- `Accessibility`: Default to WCAG 2.1 AA unless the team specifies otherwise.
- `Localization`: List target languages. Ask about RTL if Arabic or Hebrew markets are in scope.
- `Brands`: Explicit brand list. Must match the Meta section's brands.

### Non-Goals

```markdown
## Non-Goals

| ID | Description | Rationale |
|----|-------------|-----------|
| NG-001 | Admin dashboard for managing OAuth providers | Provider configuration is handled via environment variables and LaunchDarkly; no admin UI is needed for this ticket. |
| NG-002 | Automatic migration of existing email/password users to social login | User migration is a separate initiative tracked under TICKET-2000. This ticket only adds social login as an additional option. |
```

- Minimum 2 non-goals per spec. This is a hard quality gate.
- Each non-goal must have a rationale explaining WHY it is excluded.
- Non-goals prevent scope creep during implementation. They are a contract: "We explicitly decided not to do this."

### Assumptions

```markdown
## Assumptions

| ID | Assumption | Risk if Wrong | Validation Needed |
|----|-----------|---------------|-------------------|
| ASM-001 | Google OAuth client IDs are already provisioned for all target brands. | High | Yes |
| ASM-002 | The existing authentication service can accept OAuth tokens without schema changes. | Medium | Yes |
```

- Every assumption must have a risk-if-wrong level.
- High-risk assumptions with validation needed should be flagged to the team lead for verification.
- Common assumption categories:
  - Infrastructure assumptions (services exist, APIs are available)
  - Data assumptions (schema is compatible, data exists)
  - Business assumptions (rules are consistent across brands)
  - Dependency assumptions (third-party services are reliable)

### Edge Cases

```markdown
## Edge Cases

| ID | Scenario | Expected Behavior | Related Requirement |
|----|----------|-------------------|---------------------|
| EC-001 | User denies OAuth consent on the Google consent screen | Return to sign-in screen with message 'Sign-in was cancelled. You can try again or use email/password.' | REQ-001 |
| EC-002 | User's Google account email already exists in the system under an email/password account | Prompt user to link accounts: 'An account with this email already exists. Sign in with your password to link your Google account.' | REQ-001 |
| EC-003 | OAuth token exchange fails due to network timeout | Show retry prompt: 'Something went wrong. Please try again.' Log error with correlation ID to DataDog. | REQ-001 |
```

- Minimum 3 edge cases per spec. This is a hard quality gate.
- Every edge case should reference a related requirement.
- Common edge case categories:
  - Empty/null states (0 items, no data, first-time user)
  - Network failures (timeout, DNS, server error, offline)
  - Boundary values (max length, max items, min values)
  - Concurrent operations (double-tap, race conditions)
  - State conflicts (stale data, expired sessions, revoked permissions)
  - Platform differences (iOS vs Android vs Web behavior)

### Glossary

```markdown
## Glossary

| Term | Definition |
|------|-----------|
| OAuth | Open Authorization protocol used for token-based authentication with third-party providers. |
| Capacitor | Cross-platform native runtime that powers the iOS and Android apps from a single web codebase. |
| LaunchDarkly | Feature flag management platform used for controlled rollouts and kill switches. |
| PII | Personally Identifiable Information — any data that can identify a specific individual. |
```

- Include definitions for any term that a new team member might not know.
- Include project-specific terms (brand abbreviations, internal tool names, architecture terms).
- Include domain-specific terms (loyalty points, menu items, store concepts).

---

## Interaction Flow Example

```
User: /requirements --ticket=TICKET-1234 "Add ability for users to redeem loyalty points at checkout"

Skill: I have read your feature request for loyalty point redemption at checkout.
       Before I can produce a complete requirements specification, I need to
       clarify several aspects. Let me start with the most impactful question:

       **Which brands does this apply to?**
       Programs differ by brand. Does this feature target
       BK, PLK, FHS, TH, or a specific subset?

User: BK and PLK only, for now.

Skill: Noted: BK and PLK only. TH and FHS are non-goals for this ticket.

       **What platforms are in scope?**
       Should point redemption work on web (desktop + mobile browser),
       native iOS, native Android, or all?

User: All platforms.

Skill: All platforms (web, iOS, Android). I will note Capacitor-specific
       considerations for native.

       **What happens when the loyalty service is unavailable?**
       If the user tries to redeem points but the loyalty API returns
       a 500 error or times out, should checkout:
       (a) Block entirely until loyalty is resolved?
       (b) Allow checkout without points and notify the user?
       (c) Queue the redemption and apply it retroactively?

User: Option B. Let them check out without points.

Skill: Understood. Here is my draft plan based on our discussion:

       ## Draft Requirements for TICKET-1234

       ### Problem
       Users cannot redeem loyalty points during checkout, missing a key
       engagement and retention opportunity.

       ### Scope
       - Brands: BK, PLK
       - Platforms: web, iOS, Android

       ### Requirements

       | ID | Type | Priority | Description |
       |----|------|----------|-------------|
       | REQ-001 | functional | P0 | System shall display redeemable point balance at checkout |
       | REQ-002 | functional | P0 | System shall allow users to apply points to reduce order total |
       | REQ-003 | non-functional | P0 | Checkout shall proceed without points if loyalty API is unavailable |

       ### Acceptance Criteria (1 per requirement)
       - **REQ-001**: Given a user with 500 points at checkout, when the
         checkout screen loads, then their point balance is displayed
       - **REQ-002**: Given a user applies 200 points, when they confirm,
         then the order total is reduced by the equivalent value
       - **REQ-003**: Given the loyalty API returns a 500 error, when the
         user is at checkout, then checkout proceeds normally with a
         notification that points are temporarily unavailable

       ### Non-Goals
       - NG-001: Points earning at checkout (separate ticket)
       - NG-002: TH and FHS brand support (future phase)

       ### Key Assumptions
       - ASM-001: Loyalty Engine API already supports point redemption
         endpoints (risk if wrong: high)

       ### Edge Cases
       - EC-001: User has 0 points -> hide redemption option
       - EC-002: User applies more points than order total -> cap at order total
       - EC-003: Network drops mid-redemption -> rollback points, show retry

       ---

       **Reply "approved" to proceed, or describe what you'd like changed.**

User: Add an AC for REQ-002 covering partial point redemption. Otherwise approved.

Skill: Updated REQ-002 with a second AC for partial redemption.

       **Reply "approved" to proceed, or describe what you'd like changed.**

User: approved

Skill: Writing ph1_problem_spec.md now...

       [Generates and saves docs/artifacts/TICKET-1234/ph1_problem_spec.md]
```
