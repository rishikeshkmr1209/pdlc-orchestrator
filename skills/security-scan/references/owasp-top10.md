# OWASP Top 10 (2021) — Reference

Quick reference for the `security-scan` skill. For each category: what to look for in JS/TS + Node.js applications, and how to remediate.

---

## A01 — Broken Access Control

**What it is:** Users can act outside their intended permissions.

**Look for:**
- API endpoints that check authentication but not authorization (role/ownership)
- Direct object references: `/api/orders/12345` — is `12345` checked against the current user?
- IDOR (Insecure Direct Object Reference) patterns
- Missing `authz` middleware on some routes when others have it

**Remediate:**
```typescript
// BAD — checks auth but not ownership
app.get('/orders/:id', requireAuth, async (req, res) => {
  const order = await db.orders.findById(req.params.id); // any user can get any order!
  res.json(order);
});

// GOOD — verify ownership
app.get('/orders/:id', requireAuth, async (req, res) => {
  const order = await db.orders.findById(req.params.id);
  if (!order || order.userId !== req.user.id) {
    return res.status(404).json({ error: 'Not found' });
  }
  res.json(order);
});
```

---

## A02 — Cryptographic Failures

**What it is:** Sensitive data exposed due to weak/missing encryption.

**Look for:**
- Passwords hashed with MD5, SHA-1, SHA-256 (insufficient for passwords)
- HTTP URLs in production config
- Sensitive data in localStorage or unencrypted cookies
- Weak random number generation: `Math.random()` for tokens/IDs

**Remediate:**
```typescript
// BAD
const hash = crypto.createHash('md5').update(password).digest('hex');

// GOOD
import bcrypt from 'bcrypt';
const hash = await bcrypt.hash(password, 12);

// BAD — insecure token
const token = Math.random().toString(36);

// GOOD
import crypto from 'crypto';
const token = crypto.randomBytes(32).toString('hex');
```

---

## A03 — Injection

**What it is:** Hostile data sent to an interpreter as part of a command or query.

**SQL Injection:**
```typescript
// BAD
const result = await db.query(`SELECT * FROM users WHERE id = ${userId}`);

// GOOD — parameterized
const result = await db.query('SELECT * FROM users WHERE id = $1', [userId]);
```

**Command Injection:**
```typescript
// BAD
const output = execSync(`convert ${userFilename} output.pdf`);

// GOOD — avoid exec with user input; if unavoidable, validate strictly
import { z } from 'zod';
const safeFilename = z.string().regex(/^[a-zA-Z0-9_-]+\.(jpg|png)$/).parse(userFilename);
```

**NoSQL (DynamoDB):**
```typescript
// BAD — user controls the filter key
const filter = { [userInput]: value };
await db.scan({ FilterExpression: filter });

// GOOD — allowlist valid keys
const ALLOWED_KEYS = ['userId', 'status', 'createdAt'] as const;
const key = ALLOWED_KEYS.find(k => k === userInput);
if (!key) throw new ValidationError('Invalid filter key');
```

---

## A04 — Insecure Design

**What it is:** Missing or ineffective controls at the design level.

**Look for:**
- No rate limiting on login/reset/OTP endpoints
- Predictable resource IDs (sequential integers vs UUIDs)
- Business logic that allows negative quantities or prices
- No account lockout after repeated failed auth attempts

**Remediate:**
- Use `express-rate-limit` or API Gateway throttling
- Generate IDs with `crypto.randomUUID()` or `cuid2`
- Validate business invariants in service layer (not just DB constraints)

---

## A05 — Security Misconfiguration

**What it is:** Insecure default configurations, unnecessary features enabled.

**Look for:**
- `cors({ origin: '*' })` in production
- Stack traces returned in production error responses
- Default credentials in config files
- Unnecessary HTTP methods enabled on API routes

**Remediate:**
```typescript
// BAD
app.use(cors());
app.use((err, req, res, next) => {
  res.status(500).json({ error: err.stack }); // exposes internals!
});

// GOOD
app.use(cors({ origin: process.env.ALLOWED_ORIGIN }));
app.use((err: Error, req: Request, res: Response, next: NextFunction) => {
  logger.error('Unhandled error', { err, requestId: req.id });
  res.status(500).json({ error: 'Internal server error', requestId: req.id });
});
```

---

## A06 — Vulnerable and Outdated Components

**What it is:** Using components with known vulnerabilities.

**Check:**
```bash
pnpm audit --audit-level=high
```

**Patterns:**
- `package.json` with outdated major versions
- Known vulnerable packages: `lodash < 4.17.21`, `axios < 0.21.2`, `log4js < 6.4.1`
- Lock file not committed (prevents reproducible builds)

---

## A07 — Identification and Authentication Failures

**What it is:** Weaknesses in authentication implementation.

**Look for:**
- `jwt.decode()` used instead of `jwt.verify()` (decode doesn't validate signature)
- JWT `alg: none` accepted
- Session tokens not rotated after privilege change
- No `httpOnly` flag on session cookies

**Remediate:**
```typescript
// BAD
const payload = jwt.decode(token); // no signature verification!

// GOOD
const payload = jwt.verify(token, process.env.JWT_SECRET, {
  algorithms: ['HS256'], // explicit algorithm allowlist
});
```

---

## A08 — Software and Data Integrity Failures

**What it is:** Code/infrastructure without integrity verification.

**Look for:**
- CDN-hosted scripts without Subresource Integrity (SRI) hashes
- GitHub Actions using `@latest` or unversioned action tags
- `npm install` in CI without `--frozen-lockfile`
- Deserializing user-controlled JSON and executing it

**Remediate:**
```yaml
# BAD
- uses: actions/checkout@main

# GOOD — pinned to version tag (or full SHA for highest assurance)
- uses: actions/checkout@v4
```

---

## A09 — Security Logging and Monitoring Failures

**What it is:** Insufficient logging to detect and respond to breaches.

**Must log:**
- Authentication successes and failures (with user ID, IP)
- Authorization failures
- Input validation failures on sensitive endpoints
- Privileged operations (admin actions, config changes)

**Must NOT log:**
- Passwords (even failed ones)
- Full credit card numbers
- SSNs or government IDs
- Auth tokens or session IDs

---

## A10 — Server-Side Request Forgery (SSRF)

**What it is:** Server making HTTP requests to attacker-controlled locations.

**Look for:**
- `fetch(req.body.url)` — user controls the URL
- Webhooks that fetch user-provided URLs without validation
- Image/file proxying endpoints

**Remediate:**
```typescript
// BAD
const data = await fetch(req.query.url as string);

// GOOD — allowlist approach
const ALLOWED_HOSTS = ['api.partner.com', 'cdn.your-org.com'];
const url = new URL(req.query.url as string);
if (!ALLOWED_HOSTS.includes(url.hostname)) {
  throw new ValidationError('URL not in allowlist');
}
const data = await fetch(url.toString());
```
