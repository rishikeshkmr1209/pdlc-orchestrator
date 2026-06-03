# Requirements Interrogation Questions

## How to Use

Reference this document when running the sdlc-requirements skill. Work through categories in priority order. Not every category applies to every feature — use judgment based on the feature request content.

**Priority order for mandatory categories:**
1. Scope & Brand (always first — determines everything else)
2. Error States & Handling (most commonly missing)
3. Security & Compliance (highest risk if missed)
4. Performance & Constraints (hard to retrofit)
5. Feature Flag & Rollout (required by process)

**For recommended categories**, assess relevance based on the feature:
- If user-facing: Accessibility, i18n, Loading States
- If data-touching: Data Model, Observability
- If mobile: Offline & Connectivity
- If replacing existing: Migration & Rollback
- If auth-dependent: Authentication & Authorization
- If multi-service: Integration Points
- Always consider: Testing Strategy

Ask the MOST IMPACTFUL question first within each category. One question at a time. Wait for the answer before proceeding.

---

## Category: Scope & Brand

**Priority: MANDATORY — Always ask first.**

These questions define the boundaries of the feature. Getting scope wrong means building the wrong thing.

1. Does this feature apply to all brands (BK, PLK, FHS, TH) or specific ones? If specific, which ones and why?
2. Is this web-only, native mobile-only (iOS/Android via Capacitor), or cross-platform? What devices are in scope?
3. What minimum OS versions must be supported? (iOS 15+? Android 10+?)
4. What browsers and browser versions must be supported? (Chrome 90+, Safari 15+, etc.)
5. Does the UI differ by brand (theming, layout, copy, icons)? Or is it brand-agnostic with only color/font changes?
6. Which markets or regions is this launching in? Are there market-specific business rules?
7. Is this a net-new feature or a modification of existing behavior? If modifying, what is the current behavior?
8. What user segments are in scope? (All users, loyalty members only, first-time users, etc.)

---

## Category: Offline & Connectivity

**Priority: RECOMMENDED — Required for any mobile-targeted feature.**

Mobile users lose connectivity constantly. Features that ignore this break in the real world.

1. What happens when the user loses network connectivity mid-operation? (e.g., between tapping "submit" and receiving a response)
2. Is there a cached or offline state for this feature? Can users see stale data when offline?
3. How does the app recover when connectivity returns? Does it auto-retry, prompt the user, or silently sync?
4. Are there queued operations that accumulate offline and need to sync when reconnected? What is the conflict resolution strategy?
5. Should the UI indicate connectivity status (online/offline badge, greyed-out actions)?
6. What is the timeout threshold before showing an error vs. still loading? (e.g., 5 seconds, 10 seconds, 30 seconds)
7. Does partial connectivity (slow 2G/3G) need special handling? (Reduced payloads, compressed images, etc.)

---

## Category: Authentication & Authorization

**Priority: RECOMMENDED — Required if the feature involves user identity or restricted actions.**

Auth mistakes create security vulnerabilities and broken user experiences.

1. Does this feature require authentication? Can guest/anonymous users access it?
2. What authentication method is used? (Email/password, social login, biometrics, session tokens)
3. Are there role-based access controls? (Customer vs. staff vs. admin)
4. What happens when the user's session expires mid-operation? (Silent refresh, re-login prompt, data loss?)
5. If this feature creates or modifies data, how is the user's identity verified before the write operation?
6. Are there rate limits or abuse protections needed? (e.g., prevent brute-force point redemption)
7. Does this feature need to work across multiple sessions or devices? (e.g., started on mobile, finished on web)

---

## Category: Error States & Handling

**Priority: MANDATORY — The most commonly skipped category.**

Every happy path implies multiple unhappy paths. Undefined error states become user-facing crashes.

1. What happens when the primary API call fails? (500 error, timeout, malformed response)
2. What happens when the user provides invalid input? (Empty fields, wrong format, out-of-range values)
3. What happens when a business rule prevents the action? (Insufficient points, store closed, item unavailable)
4. Should errors be retriable? If so, is it automatic retry or manual (user taps "Try Again")?
5. What is the error message copy? Who writes it — engineering or content team? Is it localized?
6. Are there error states that should trigger alerts or monitoring? (e.g., if error rate exceeds 5%)
7. What is the fallback behavior? Does the feature degrade gracefully or does the entire flow block?
8. Are there partial failure scenarios? (e.g., 3 of 5 items succeed — what happens to the 2 failures?)

---

## Category: Loading & Async States

**Priority: RECOMMENDED — Required for any feature with API calls or data fetching.**

Users perceive loading as broken after 1 second. Undesigned loading states feel unpolished.

1. What loading indicator should appear while data is fetching? (Spinner, skeleton screen, progress bar)
2. Is there an optimistic UI strategy? (Show success immediately, roll back on failure)
3. What is the expected latency for the primary operation? Is there a timeout threshold?
4. Should the UI be interactive during loading, or should actions be disabled/blocked?
5. Are there multiple sequential API calls? If so, should they load independently or show a single aggregate loader?
6. What should happen if loading takes more than 10 seconds? (Timeout message, cancel option, background the operation)
7. Is there a placeholder or empty state shown before the first load completes?

---

## Category: Feature Flag & Rollout

**Priority: MANDATORY — Required by the development process.**

Every new feature must be behind a LaunchDarkly feature flag for safe rollout and instant kill-switch capability.

1. What is the LaunchDarkly flag key for this feature? (Follow naming convention: `enable-feature-name`)
2. Is the flag boolean (on/off) or multivariate (different variations for A/B testing)?
3. What is the default behavior when the flag is OFF? (Old behavior, hidden UI, error message?)
4. Is there a phased rollout plan? (5% of users, then 25%, then 50%, then 100%?)
5. Are there market-specific flag configurations? (e.g., enabled in US but not EU)
6. What happens if the flag is toggled OFF mid-session while a user is actively using the feature?
7. Is the flag evaluated on the client (frontend) or server (backend)? Both?
8. When can the flag be permanently removed (hardcoded ON)? What is the cleanup plan?

---

## Category: Performance & Constraints

**Priority: MANDATORY — Hard to retrofit after implementation.**

Performance requirements must be numeric and measurable. "Fast" is not a requirement.

1. What is the acceptable response time for the primary operation? (p95 in milliseconds)
2. What throughput must the system handle? (Requests per second during peak, e.g., lunch rush)
3. What is the maximum payload size for API requests and responses? (KB)
4. Are there bandwidth constraints? (Mobile users on 3G, emerging markets with slow connections)
5. Is there a client-side rendering performance budget? (Time to interactive, largest contentful paint)
6. Are there data volume constraints? (Max items in a list, max history records, pagination thresholds)
7. Does this feature have batch operations? If so, what is the maximum batch size?
8. Are there concurrent usage scenarios? (Multiple users modifying the same resource simultaneously)

---

## Category: Security & Compliance

**Priority: MANDATORY — Highest risk if missed.**

Security failures can expose millions of customer records. Compliance failures can result in regulatory fines.

1. Does this feature collect, store, display, or transmit PII? (Email, name, phone, address, payment data)
2. Is user consent required before processing this data? Has the user clicked the consent/accepted button?
3. Does this feature comply with GDPR requirements? (Right to erasure, data portability, consent management)
4. Is PCI DSS compliance required? (Any payment data handling)
5. Is the data encrypted at rest and in transit?
6. Are there audit logging requirements? (Who did what, when, from where)
7. Does this feature expose any data in URLs, query parameters, or browser history? (Data leakage risk)
8. Are there IP address processing requirements? (Must use CLIENT_ORG IP library)

---

## Category: Data Model & Migration

**Priority: RECOMMENDED — Required if the feature involves new data storage or schema changes.**

Data model changes are the hardest to reverse. Get them right the first time.

1. Does this feature require new database tables, fields, or indexes?
2. Is there a data migration needed for existing records? What is the migration strategy (lazy vs. batch)?
3. What is the data retention policy? How long is this data kept?
4. Are there data consistency requirements? (Strong consistency vs. eventual consistency)
5. Does this data need to sync across services? (e.g., loyalty engine and middleware both need it)
6. What is the expected data volume? (Number of records, growth rate)
7. Are there foreign key or referential integrity constraints?
8. Does this data power any reporting or analytics? If so, are there ETL considerations?

---

## Category: Observability & Monitoring

**Priority: RECOMMENDED — Required for any production-facing feature.**

If you cannot observe it, you cannot debug it. Observability must be designed in, not bolted on.

1. What metrics should this feature emit? (Counters, gauges, histograms — be specific)
2. What should the monitoring dashboard show? (Success rate, error rate, latency distribution, throughput)
3. What alerts should fire? (Error rate > 5%, latency > 2s, zero throughput for 5 minutes)
4. What structured log fields are needed? (Use the structured logger with module and step conventions)
5. Are there business metrics to track? (Conversion rate, adoption rate, revenue impact)
6. Is distributed tracing needed? (Correlation IDs across services)
7. Is PII excluded from all logs and metrics? (This is a hard requirement — no email, phone, name in logs)

---

## Category: Accessibility

**Priority: RECOMMENDED — Required for all user-facing features.**

WCAG 2.1 AA compliance is the minimum standard. Accessibility is a requirement, not a nice-to-have.

1. Are all interactive elements keyboard-navigable? (Tab order, focus management, keyboard shortcuts)
2. Do all images, icons, and non-text content have appropriate alt text or ARIA labels?
3. Are color contrasts sufficient? (4.5:1 for normal text, 3:1 for large text per WCAG AA)
4. Does this feature work with screen readers? (VoiceOver on iOS, TalkBack on Android, NVDA/JAWS on web)
5. Are form inputs properly labeled? Are error messages associated with their fields?
6. Is there any content that relies solely on color to convey meaning? (Must have secondary indicator)
7. Are touch targets at least 44x44 points for mobile? (iOS Human Interface Guidelines minimum)
8. Does the feature respect reduced-motion preferences? (prefers-reduced-motion media query)

---

## Category: i18n & Localization

**Priority: RECOMMENDED — Required for features launching in non-English markets.**

The organization operates globally. Features must handle multiple languages, date formats, and cultural conventions.

1. What languages must this feature support? List specific language codes (en, fr, es, de, ar, etc.)
2. Is right-to-left (RTL) language support needed? (Arabic, Hebrew)
3. Are there text strings that need translation? Who manages translations — engineering or localization team?
4. Does the feature handle different date, time, currency, or number formats by locale?
5. Are there locale-specific business rules? (e.g., tax display requirements, legal disclaimers)
6. Does the feature involve user-generated content? If so, is it stored with locale information?
7. Are there character set considerations? (Unicode, emoji support, special characters in names)
8. Do UI layouts accommodate text expansion? (German text is ~30% longer than English)

---

## Category: Integration Points

**Priority: RECOMMENDED — Required for features that interact with other services or systems.**

Features rarely exist in isolation. Most touch multiple microservices, CMS, or third-party APIs.

1. What existing APIs or services does this feature depend on? (List specific services)
2. Are there new API endpoints needed? What is the contract (request/response shape)?
3. Does this feature interact with Sanity CMS? Are there new content types or fields?
4. Does this feature interact with the loyalty engine or middleware? What operations?
5. Are there third-party integrations? (Payment providers, OAuth providers, analytics services)
6. What is the API versioning strategy? Can the API change without breaking existing clients?
7. Are there webhook or event-driven integrations? What events are published/consumed?
8. Is there a GraphQL schema change needed for the intl-gateway-service supergraph?

---

## Category: Migration & Rollback

**Priority: RECOMMENDED — Required for features that modify existing behavior.**

Every deployment must be reversible. Plan for failure before it happens.

1. Is there existing functionality being replaced or modified? What is the migration path?
2. Can this feature be rolled back safely? What is the rollback procedure?
3. If the feature flag is turned off, does the system return to the previous state cleanly?
4. Are there database migrations? Are they forward-only or reversible?
5. Is there a data backfill needed? How long does the backfill take? Can it run during business hours?
6. Are there breaking API changes? Is a deprecation period needed?
7. Do downstream consumers (mobile apps, SDKs) need to update? What is the minimum supported version?

---

## Category: Testing Strategy

**Priority: RECOMMENDED — Always relevant, depth varies by feature complexity.**

Tests validate that requirements are met. Testing strategy should be defined during requirements, not after implementation.

1. What are the critical paths that MUST have automated tests? (Happy path, primary error path)
2. Are there E2E test scenarios that cross service boundaries? (e.g., frontend to loyalty engine to payment)
3. Are there performance test requirements? (Load testing, stress testing, soak testing)
4. Are there accessibility test requirements? (Automated axe scans, manual screen reader testing)
5. Do tests need to run in both QA and PROD environments? Are there environment-specific considerations?
6. Are there test data requirements? (Specific user states, loyalty balances, store configurations)
7. Is A/B testing involved? How are test groups assigned and measured?
8. Are there device-specific test requirements? (Specific iOS/Android devices, browser versions)
