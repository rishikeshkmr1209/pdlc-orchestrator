# JS/TS Extended Quality Checklist

Supplementary checklist for the `code-review` skill covering JavaScript and TypeScript quality concerns beyond the core review.

---

## JavaScript-Specific Issues

### Equality and Comparisons
- [ ] Uses `===` / `!==` (never `==` / `!=` outside of null checks)
- [ ] Null checks use `=== null` or `?? `/ `?.` operators appropriately
- [ ] No accidental falsy checks on `0` or `''` when those are valid values

### Object and Array Operations
- [ ] Spread operator `{...obj}` used for shallow cloning (not `Object.assign` unless intentional)
- [ ] No mutation of function parameters
- [ ] Array methods (`.map`, `.filter`, `.reduce`) used functionally — no side effects inside
- [ ] No `delete` operator on object properties — prefer destructuring with rest

### `this` Context
- [ ] Arrow functions used in callbacks to preserve `this` where needed
- [ ] Class methods that use `this` are not passed as callbacks without binding

### Coercion
- [ ] No implicit string-to-number coercion (`+'123'` or `123 + ''`)
- [ ] `parseInt(str, 10)` — radix always specified
- [ ] `Number.isNaN()` used (not the global `isNaN()` which coerces)
- [ ] `Number.isFinite()` used instead of global `isFinite()`

---

## TypeScript-Specific Issues

### Type Assertions
- [ ] `as Type` assertions are minimized — prefer type guards
- [ ] Non-null assertion `!` used only when null is truly impossible and a comment explains why
- [ ] Type predicates used for type narrowing: `function isUser(v: unknown): v is User`

### Generics
- [ ] Generic constraints are as specific as possible (`T extends Record<string, unknown>` not just `T`)
- [ ] Generic parameter names are descriptive for complex generics (`TEntity`, `TKey`)
- [ ] Conditional types are documented with an example

### Declaration Files
- [ ] No manual `.d.ts` files that could be auto-generated
- [ ] `declare module` augmentations are in dedicated type files

### tsconfig Compliance
- [ ] No `"skipLibCheck": true` introduced without justification
- [ ] `"noUncheckedIndexedAccess": true` compatible (array access handles `undefined`)
- [ ] `"exactOptionalPropertyTypes": true` compatible where enabled

---

## Node.js Specific

### File System
- [ ] `fs/promises` (async) used — never `fs.readFileSync` in request handlers
- [ ] File paths constructed with `path.join()` or `path.resolve()` — never string concatenation
- [ ] Relative paths use `__dirname` or `import.meta.url` — not `process.cwd()`

### Environment Variables
- [ ] Environment variables accessed through a validated config module, not scattered `process.env.FOO`
- [ ] Missing required env vars fail fast at startup with a clear error message
- [ ] No `process.env.NODE_ENV === 'production'` scattered throughout business logic

### Streams
- [ ] Streams are destroyed/closed on error to prevent memory leaks
- [ ] Large file processing uses streams, not `readFile` into memory

---

## Package / Dependency Issues

### package.json
- [ ] No duplicate dependencies in both `dependencies` and `devDependencies`
- [ ] Scripts use cross-platform tools (no Unix-only commands in npm scripts)
- [ ] `engines` field specifies required Node.js version
- [ ] No unnecessary `^` or `~` on lock-file-managed projects (pnpm/yarn)

### Lock Files
- [ ] Lock file is present and committed
- [ ] `pnpm-lock.yaml` / `package-lock.json` / `yarn.lock` is not in `.gitignore`
- [ ] Lock file is up to date with `package.json`

---

## ESLint / Prettier Compliance

Common rule violations to look for manually when ESLint output isn't available:

- `no-console` — no `console.log` in production code (use logger)
- `no-unused-vars` — no declared but unused variables
- `prefer-const` — `let` only when re-assigned
- `no-var` — no `var` declarations
- `object-shorthand` — `{ foo }` not `{ foo: foo }`
- `arrow-body-style` — `x => x * 2` not `x => { return x * 2; }`
- `@typescript-eslint/no-floating-promises` — all promises handled
- `@typescript-eslint/await-thenable` — `await` only on promises

---

## React-Specific (for frontend services)

### Hooks Rules
- [ ] No conditional `useEffect`/`useState` calls
- [ ] `useEffect` dependency arrays are complete (no missing deps)
- [ ] Cleanup functions returned from `useEffect` when needed (event listeners, timers)

### Performance
- [ ] `React.memo` used for components that re-render with same props frequently
- [ ] `useMemo` / `useCallback` used for expensive computations / callback props
- [ ] Keys in lists are stable and unique (not array indices)

### Accessibility
- [ ] Interactive elements use semantic HTML (`<button>` not `<div onClick>`)
- [ ] Images have `alt` text
- [ ] Form elements have associated `<label>`
- [ ] Modals manage focus and have `aria-modal="true"`
