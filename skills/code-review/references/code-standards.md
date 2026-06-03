# Code Standards — JavaScript & TypeScript

Reference document for the `code-review` skill. Provides project-specific rules beyond generic best practices.

> Last aligned with Project Standard Practices

---

## Core Principles

### KISS — Keep It Simple
Always prioritize the simplest solution that solves the problem. Avoid over-engineering. If a function can be 5 lines instead of 20, it should be 5 lines. Clever code that's hard to read is a liability.

```typescript
// BAD — over-engineered
class UserNameFormatterFactory {
  createFormatter(type: 'full' | 'short') {
    return type === 'full'
      ? new FullNameFormatter()
      : new ShortNameFormatter();
  }
}

// GOOD — just a function
function formatName(user: User, format: 'full' | 'short'): string {
  return format === 'full' ? `${user.firstName} ${user.lastName}` : user.firstName;
}
```

### SOLID Principles

**Single Responsibility** — one class/function, one reason to change:
```typescript
// BAD — mixes concerns
class OrderService {
  createOrder(data: CreateOrderInput) { /* business logic */ }
  sendConfirmationEmail(order: Order) { /* email concern */ }
  formatOrderForPdf(order: Order) { /* formatting concern */ }
}

// GOOD — separated
class OrderService { createOrder(data: CreateOrderInput) { ... } }
class OrderNotificationService { sendConfirmationEmail(order: Order) { ... } }
class OrderDocumentService { formatOrderForPdf(order: Order) { ... } }
```

**Dependency Inversion** — depend on abstractions:
```typescript
// BAD — tight coupling to concrete class
class OrderService {
  private emailer = new SendGridEmailer(); // can't be swapped or mocked
}

// GOOD — inject via interface
interface Emailer { send(to: string, subject: string, body: string): Promise<void>; }
class OrderService {
  constructor(private readonly emailer: Emailer) {}
}
```

---

## Logging & Observability Standards

### Structured Logging
```typescript
// BAD — unstructured, leaks PII
console.log(`Processing order for user ${user.email}`);
console.log('Order:', order); // order object may contain PII

// GOOD — structured, no PII
logger.info('Processing order', {
  orderId: order.id,
  userId: anonymize(user.id), // anonymized ID only
  itemCount: order.items.length,
});
```

### No PII in Logs (Hard Requirement)
**Never log to DataDog, CloudWatch, or any monitoring tool:**
- Email addresses
- Phone numbers
- Full names
- Physical addresses
- Payment card data (PAN, CVV)
- Government IDs (SSN, passport)
- Session tokens or API keys

Use anonymized/hashed identifiers when you need to track a user across log lines.

### IP Address Handling
Per project policy, always use the **project IP address library** when processing IP addresses:
```typescript
// BAD — raw IP handling
const userIp = req.headers['x-forwarded-for'];
logger.info('Request from', { ip: userIp }); // may be PII in some jurisdictions

// GOOD — use project IP library
import { anonymizeIp } from '@client/ip-utils';
logger.info('Request received', { ip: anonymizeIp(req.ip) });
```

### User Consent Gating
Only use user data after consent is confirmed:
```typescript
// BAD — fires analytics before consent
trackEvent('page_view', { userId: user.id });

// GOOD — check consent first
if (hasUserConsented(user)) {
  trackEvent('page_view', { userId: user.id });
}
```

---

## Module Structure

### Preferred File Organization
```
src/
  [feature]/
    index.ts          ← Public API (re-exports only)
    [feature].ts      ← Core logic
    [feature].types.ts ← Type definitions
    [feature].errors.ts ← Custom error classes
    __tests__/
      [feature].test.ts
```

### Re-export Pattern
```typescript
// src/auth/index.ts — GOOD: explicit public API
export { authenticate } from './auth';
export type { AuthResult, AuthError } from './auth.types';

// Avoid barrel files that re-export everything with *
export * from './auth'; // BAD — leaks internals
```

---

## TypeScript Patterns

### Typed Error Classes
```typescript
// GOOD
export class AuthenticationError extends Error {
  readonly code: string;
  constructor(message: string, code: string) {
    super(message);
    this.name = 'AuthenticationError';
    this.code = code;
  }
}

// AVOID
throw new Error('auth failed'); // too generic
throw 'auth failed';            // never throw strings
```

### Result Pattern (for fallible operations)
```typescript
// Use when errors are expected business outcomes
type Result<T, E extends Error = Error> =
  | { ok: true; value: T }
  | { ok: false; error: E };

async function findUser(id: string): Promise<Result<User, UserNotFoundError>> {
  const user = await db.users.findById(id);
  if (!user) return { ok: false, error: new UserNotFoundError(id) };
  return { ok: true, value: user };
}
```

### Discriminated Unions Over Boolean Flags
```typescript
// AVOID
type Order = {
  status: string;
  isPending: boolean;
  isCompleted: boolean;
  isCancelled: boolean;
};

// PREFER
type OrderStatus = 'pending' | 'completed' | 'cancelled';
type Order = {
  status: OrderStatus;
};
```

### Readonly for Immutable Data
```typescript
// Mark data that shouldn't be mutated
function processItems(items: readonly Item[]): ProcessedItem[] { ... }
```

---

## Service Layer Patterns

### Dependency Injection
```typescript
// GOOD — testable, injectable
export class OrderService {
  constructor(
    private readonly db: OrderRepository,
    private readonly events: EventBus,
  ) {}
}

// AVOID — hard to test
export class OrderService {
  private db = new PostgresOrderRepository(); // tight coupling
}
```

### Validation
```typescript
// Use zod for runtime validation at system boundaries
import { z } from 'zod';

const CreateOrderSchema = z.object({
  userId: z.string().uuid(),
  items: z.array(z.object({
    productId: z.string().uuid(),
    quantity: z.number().int().positive().max(99),
  })).nonempty(),
});

type CreateOrderInput = z.infer<typeof CreateOrderSchema>;
```

---

## React / Next.js Patterns

### Component File Structure
```typescript
// 1. Imports (external, then internal)
// 2. Types/interfaces
// 3. Constants
// 4. Component function
// 5. Sub-components (if small, else separate file)
// 6. Default export
```

### Hook Naming and Patterns
```typescript
// Custom hooks: always prefix with `use`
function useOrderStatus(orderId: string) {
  // ALWAYS handle loading, error, and data states
  const [state, setState] = useState<
    | { status: 'loading' }
    | { status: 'error'; error: Error }
    | { status: 'success'; data: Order }
  >({ status: 'loading' });
  ...
}
```

### Avoid `useEffect` for Data Fetching
Prefer React Query / SWR / server components over `useEffect` + `fetch`.

---

## API Handler Patterns (Lambda / Express)

### Input Validation
```typescript
export const handler = async (event: APIGatewayProxyEvent) => {
  // Always validate before processing
  const parseResult = CreateOrderSchema.safeParse(JSON.parse(event.body ?? '{}'));
  if (!parseResult.success) {
    return {
      statusCode: 400,
      body: JSON.stringify({ error: 'Invalid request', details: parseResult.error.flatten() }),
    };
  }
  // ... process parseResult.data
};
```

### Consistent Response Shape
```typescript
// Success
{ data: T, meta?: { page, total } }

// Error
{ error: string, code: string, details?: unknown }
```

---

## Logging

```typescript
// GOOD — structured, no PII
logger.info('Order created', { orderId, userId, itemCount: items.length });

// BAD — unstructured, contains PII
console.log(`Order created for ${user.email} with card ${card.number}`);
```

Never log: passwords, tokens, credit card numbers, SSNs, full email addresses in production logs.
