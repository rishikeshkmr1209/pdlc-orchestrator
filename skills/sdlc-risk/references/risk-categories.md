# Risk Categories Reference

Comprehensive risk taxonomy for adversarial risk assessment.
Use this as a checklist when identifying failure modes, attack vectors, and blind spots.

---

## Failure Mode Categories

### Network Failures
- **Timeout**: Request exceeds configured timeout; user sees spinner or error
- **DNS resolution failure**: Domain lookup fails; service unreachable
- **TLS handshake failure**: Certificate expiry, mismatch, or revocation
- **CDN origin failure**: Edge cache cannot reach origin; stale or error content served
- **Load balancer misconfiguration**: Traffic routed to unhealthy targets
- **Connection pool exhaustion**: All connections in use; new requests rejected
- **Partial network partition**: Some services reachable, others not; inconsistent state

### Data Failures
- **Data corruption**: Invalid data written to storage; downstream consumers break
- **Data inconsistency**: Different sources disagree on the same entity state
- **Migration failure**: Schema migration fails mid-way; half-migrated state
- **Race condition on write**: Concurrent writes produce unexpected final state
- **Serialization error**: Data format mismatch between producer and consumer
- **Orphaned records**: Parent deleted but child records remain; referential integrity broken
- **Data truncation**: Fields silently truncated at storage boundary; data loss

### State Failures
- **Stale state**: Cache or local state diverges from source of truth
- **Cache invalidation failure**: Updated data not reflected due to caching
- **Session expiry mid-operation**: User loses progress during a multi-step flow
- **State machine violation**: Entity reaches an invalid or unexpected state
- **Browser storage limits**: localStorage or IndexedDB quota exceeded
- **Hydration mismatch**: Server-rendered HTML does not match client-side state

### Concurrency Failures
- **Race conditions**: Two operations conflict; last write wins unpredictably
- **Deadlocks**: Two processes wait on each other indefinitely
- **Lost updates**: Concurrent edits overwrite each other without detection
- **Double submission**: User submits a form twice; duplicate records created
- **Phantom reads**: Data changes between two reads in the same logical operation
- **Lock contention**: Excessive locking degrades throughput under load

### Dependency Failures
- **SDK incompatibility**: Library update introduces breaking API change
- **API deprecation**: Upstream removes or changes an endpoint without notice
- **Service outage**: Dependent service returns errors or is unreachable
- **Version drift**: Different environments running different dependency versions
- **Rate limiting**: Upstream throttles requests; degraded functionality
- **Certificate rotation**: Dependency rotates certificates; mTLS breaks

---

## Attack Vector Categories

### Injection Attacks
- **Cross-Site Scripting (XSS)**: Reflected, stored, or DOM-based script injection
- **SQL Injection**: Malformed input alters database queries
- **Command Injection**: User input executed as system commands
- **Template Injection**: Server-side template engine evaluates user input
- **GraphQL Injection**: Deeply nested queries, alias abuse, or introspection exposure
- **Header Injection**: Malformed headers manipulate server behavior (CRLF, Host)
- **Log Injection**: Crafted input corrupts log entries or triggers log-based alerts

### Authentication and Authorization Bypass
- **Token theft**: Session token or JWT stolen via XSS, network sniffing, or logs
- **Session fixation**: Attacker sets a known session ID before victim authenticates
- **Privilege escalation**: User accesses resources beyond their role
- **IDOR (Insecure Direct Object Reference)**: Manipulating IDs to access other users' data
- **JWT manipulation**: Altering JWT payload without invalidation (alg:none, key confusion)
- **OAuth redirect manipulation**: Redirect URI changed to attacker-controlled domain
- **Broken function-level authorization**: Admin endpoints accessible to regular users

### Data Exposure
- **PII leaks in logs**: Personal data written to CloudWatch, DataDog, or console output
- **Error message disclosure**: Stack traces, SQL errors, or internal paths exposed to user
- **Debug endpoints in production**: Diagnostic routes left enabled after development
- **Verbose API responses**: Returning more fields than the client needs
- **Source map exposure**: Production build includes source maps with original code
- **Sensitive data in URLs**: Tokens, IDs, or PII in query parameters (logged in access logs)

### Configuration Vulnerabilities
- **Default credentials**: Admin accounts with known passwords left active
- **Open CORS policy**: Wildcard origins allowing cross-origin requests
- **Missing CSP headers**: No Content-Security-Policy; XSS vectors unblocked
- **Permissive IAM policies**: Overly broad AWS permissions (Resource: "*")
- **Exposed environment variables**: Secrets in client bundles or public config
- **Missing rate limiting**: No throttle on sensitive endpoints (login, payment, etc.)
- **Insecure cookie flags**: Missing HttpOnly, Secure, SameSite attributes

---

## Blind Spot Categories

### Scalability
- Horizontal scaling limits for stateful components
- Database connection pool sizing under peak load
- Cache eviction under memory pressure
- Queue depth and consumer throughput mismatch
- Auto-scaling lag during sudden traffic spikes
- DynamoDB partition hot spots with non-uniform access patterns

### Edge Cases
- Timezone handling across multi-region deployments
- Unicode and emoji in user input fields
- Extremely large payloads (menu items, order history)
- Empty states (zero items, first-time user, no search results)
- Boundary values (max integer, empty string, null vs undefined)
- Leap years, daylight saving transitions, end-of-month billing

### User Behavior
- Rapid clicking / rage taps on submit buttons
- Back button navigation in multi-step flows
- Multiple browser tabs with the same session
- Copy-paste of formatted text into plain-text fields
- Browser extensions interfering with DOM or network requests
- Users with slow devices or outdated browsers
- Accessibility technology interactions (screen readers, voice control)

### Third-Party Dependencies
- NPM package rate limits on install during CI/CD
- API version deprecation without migration path
- Upstream service outages with no fallback
- SDK breaking changes in minor/patch versions
- License changes affecting commercial use
- Supply chain attacks (compromised packages)
- CDN provider outage affecting static assets

### Data Consistency
- Eventual consistency windows in distributed systems
- Replication lag between primary and read replicas
- Split-brain scenarios during network partitions
- Conflict resolution in offline-first architectures
- Idempotency gaps in retry logic
- Transaction isolation level mismatches across services

### Compliance
- GDPR right to erasure across all data stores and backups
- PCI DSS scope expansion when handling payment data paths
- Data residency requirements per market (EU, APAC, LATAM)
- Cookie consent and tracking across brands and regions
- Age verification requirements in specific markets
- Accessibility standards (WCAG 2.1 AA) for public-facing features
- Data retention policies and automated purge schedules

---

## Project-Specific Risks

### Multi-Brand Risks
- Configuration conflicts between brands (BK, PLK, FHS, TH)
- Brand-specific feature flags interfering with shared code paths
- Theme or styling leaking between brand builds
- Shared component changes breaking brand-specific layouts
- CMS content model changes affecting multiple brands differently

### Multi-Region Risks
- Data residency violations (EU data stored in US region)
- Latency impact from cross-region API calls
- Deployment ordering dependencies across regions
- Currency and locale handling errors
- Regional menu availability and pricing discrepancies
- Time-based promotions across different timezones

### Payment Risks
- PCI scope expansion from new data flows
- PSP (Payment Service Provider) failover behavior
- Double-charge scenarios from retry logic
- Refund processing delays or failures
- Gift card balance manipulation
- Coupon/promo code abuse and stacking exploits

### CDN and Edge Risks
- Cache poisoning via manipulated request headers
- Stale content served after deployment
- Purge delay impact on time-sensitive content (pricing, availability)
- Edge function cold start latency
- CDN origin failover behavior
- Geo-routing errors sending users to wrong regional backend

### Mobile-Specific Risks
- App store review rejection for new permissions or capabilities
- Capacitor bridge failures between web and native layers
- Offline sync conflicts when connectivity is restored
- Push notification delivery failures
- Deep link handling errors across app states
- Background app state management (iOS vs Android differences)
- In-app update prompts and forced upgrade flows

### Menu and Ordering Risks
- Price manipulation via client-side request modification
- Item availability race conditions during high-demand periods
- Order total calculation discrepancies between client and server
- Modifier and customization combination explosions
- Restaurant capacity and throttling during peak hours
- Drive-through vs in-store vs delivery flow differences

### Loyalty-Specific Risks
- Point balance manipulation via replay attacks
- Double-earn exploits from concurrent transactions
- Redemption abuse (redeeming more than balance allows)
- Loyalty tier calculation errors during edge-case transitions
- Points expiry handling across timezones
- Cross-brand loyalty point transfer vulnerabilities
