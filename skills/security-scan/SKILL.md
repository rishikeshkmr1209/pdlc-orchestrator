---
name: 07.3-security-scan
description: >
  Use when user says "security scan", "check for vulnerabilities", "security audit",
  "are there any security issues", "check for secrets", or "security review".
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
---

# Security Scan Skill

You are performing a project security scan. Identify vulnerabilities, misconfigurations, and compliance gaps. All findings must include location, severity, risk description, and remediation.

## Severity Levels

- **Critical** — Exploitable immediately, data breach or system compromise risk
- **High** — Significant risk, should be fixed before next deployment
- **Medium** — Real risk, should be addressed in current sprint
- **Low** — Minor risk, address in backlog
- **Info** — Not a vulnerability, but noteworthy for security posture

## Scan Procedure

### Step 1: Secrets Detection

Search for hardcoded secrets:
```
Patterns to find:
- API keys: /api[_-]?key\s*[:=]\s*['"][^'"]{8,}/i
- AWS credentials: AKIA[0-9A-Z]{16}
- Passwords in config: password\s*[:=]\s*['"][^'"]+['"]
- JWT secrets: (jwt|secret|token)[_-]?secret\s*[:=]
- Database URLs with credentials: (mongodb|postgres|mysql)://[^:]+:[^@]+@
- Private keys: -----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----
```

Also check:
- `.env` files committed to the repo
- GitHub Actions YAML for inline secrets
- `config/` directories for non-template config files with real values

### Step 2: Dependency Audit
```bash
# Run if in a Node.js project
npm audit --audit-level=high 2>/dev/null || \
pnpm audit --audit-level=high 2>/dev/null || \
yarn audit --level high 2>/dev/null
```

### Step 3: Injection Vulnerabilities

**SQL Injection**
- Look for string concatenation in database queries
- Patterns: `query = "SELECT ... WHERE id = " + userId`
- Check ORMs are used correctly (no raw query strings with user input)

**NoSQL Injection (DynamoDB, MongoDB)**
- User input used directly in query filters without sanitization
- `$where` operator in MongoDB with user data

**Command Injection**
- `child_process.exec()`, `execSync()`, `spawn()` with user-controlled input
- Template literals in shell commands

**XSS**
- `dangerouslySetInnerHTML={{ __html: userInput }}`
- `innerHTML = userInput` without sanitization
- `document.write(userInput)`

**SSRF**
- `fetch(userProvidedUrl)` without allowlist validation
- HTTP client calls to user-supplied hostnames

### Step 4: Authentication & Authorization

- JWT verification: `verify()` called (not just `decode()`)
- Session tokens validated on every request
- Authorization checks present on all API routes (not just auth middleware)
- No hardcoded admin credentials or backdoors

### Step 5: AWS Configuration Review

For CDK/SAM/CloudFormation files:
- IAM policies with `"Resource": "*"` combined with sensitive actions
- S3 bucket `BlockPublicAccess` not enabled
- Lambda functions without VPC (if accessing private resources)
- Security groups with `0.0.0.0/0` ingress on non-80/443 ports
- KMS encryption not enabled for sensitive data stores
- CloudTrail not enabled (flag as Info)

### Step 6: PII & Data Privacy Rules

**No PII to monitoring or logging tools — this is a hard requirement.**

- Any PII (email, phone, name, address, payment details, government IDs) sent to DataDog, CloudWatch, or any logging/monitoring system
- Raw user objects logged: `console.log(user)`, `logger.info('event', event)` where object contains PII fields
- IP addresses logged or processed without using the **CLIENT_ORG IP address library/package** (required per RFC)
- User data used or processed before the user has accepted the consent button in the app
- Analytics or tracking events fired before consent is confirmed
- Sensitive fields returned in API responses that aren't needed by the consumer
- Credit card data or SSNs handled in application code at all (should never reach the application layer)
- Anonymization techniques not used where PII observation is genuinely needed

### Step 7: CORS and HTTP Security

For Express/Fastify/Lambda API handlers:
- `cors({ origin: '*' })` in production configuration
- Missing security headers: `Strict-Transport-Security`, `Content-Security-Policy`, `X-Frame-Options`
- HTTP (not HTTPS) URLs used for internal service calls in production config

## Platform-Specific Security

### Lambda-Specific
- Timeout: verify Lambda timeout is set explicitly (not default 3s); flag timeouts >30s without justification
- Memory: flag functions with >1024MB unless processing large payloads or doing image/PDF work
- IAM roles: each Lambda must have its own execution role; flag shared roles across functions
- Secrets via SSM: environment variables must reference SSM Parameter Store or Secrets Manager ARNs, not plaintext secrets
- Reserved concurrency: critical Lambdas (payment, auth) should set reserved concurrency to prevent throttling
- Cold start: flag VPC-attached Lambdas without provisioned concurrency for latency-sensitive paths
- Layers: shared dependencies should use Lambda Layers, not bundled per-function

### GraphQL-Specific
- Introspection disabled: `introspection` must be `false` in production Apollo Server config
- Depth limiting: flag missing `depthLimit` plugin; max depth should be ≤10 for public APIs
- Query complexity: flag missing query complexity analysis; expensive operations (joins, aggregations) should have cost limits
- Persisted queries: production should use APQ (Automatic Persisted Queries) or a persisted query allowlist
- Rate limiting: GraphQL endpoints must have rate limiting per-client; flag missing rate limit middleware
- Input validation: mutation inputs must be validated (string length, allowed characters, enum values) before reaching resolvers
- Error masking: production must not expose stack traces or internal error messages in GraphQL error responses

### Capacitor / Mobile-Specific
- Deep link validation: verify URL schemes and universal links are validated against an allowlist before navigation
- Secure storage: sensitive tokens must use `@capacitor/preferences` with encryption or native Keychain/Keystore, not localStorage
- Certificate pinning: flag missing certificate pinning configuration for API calls in native builds
- WebView restrictions: `allowNavigation` in `capacitor.config.ts` must not include wildcards (`*`); restrict to known domains
- Biometric auth: flag biometric token storage that doesn't use the platform secure enclave
- App transport security: iOS `Info.plist` must not disable ATS (`NSAllowsArbitraryLoads: true`) in production builds

## Output Format

```
## Security Scan Report

**Scope:** [files / directories scanned]
**Date:** [today's date]

### Summary
[2-3 sentences on overall security posture]

---

### Findings

#### [CRITICAL|HIGH|MEDIUM|LOW|INFO] — [Finding Title]
- **Location:** `path/to/file.ts:line`
- **Issue:** [What was found]
- **Risk:** [What an attacker could do with this]
- **Remediation:**
  ```typescript
  // Current (vulnerable):
  [current code]

  // Fixed:
  [fixed code]
  ```

[Repeat for each finding]

---

### Totals
Critical: N | High: N | Medium: N | Low: N | Info: N

### Next Steps
1. [Priority action]
2. [Priority action]
```

## References

- `references/owasp-top10.md` — OWASP Top 10 (2021) details and remediation patterns
- `references/aws-security-checklist.md` — AWS-specific security configuration checklist

## Evaluation

| Scenario | Input | Expected behavior |
|----------|-------|-------------------|
| Trigger — positive | "security scan this file" | Skill activates, runs full scan |
| Trigger — positive | "check for hardcoded secrets" | Skill activates |
| Trigger — negative | "how do I write a for loop?" | Skill does NOT activate |
| High-value find | File with `AKIA...` AWS key | Reports as Critical finding |
| Clean file | Well-written service with no issues | Reports "No findings" with explanation |
