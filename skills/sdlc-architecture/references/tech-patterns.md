# Technology Patterns Reference

This reference documents technology patterns that the architect MUST follow
when designing features for projects. Every design decision should
align with these established patterns unless an ADR justifies deviation.

---

## 1. Brand Constants and Theming

The project supports multiple brands: **BR1**, **BR2**, **BR3**, **BR4**. <!-- Configure brand codes for your organization -->

### Brand Configuration
- Brand is determined at build time via `REACT_APP_CLIENT_BRAND` environment variable.
- Platform is set via `REACT_APP_CLIENT_PLATFORM` (web, ios, android).
- Brand-specific constants live in configuration files keyed by brand enum.
- Features must be brand-agnostic in logic; brand-specific behavior is driven by configuration.

### Design Rules
- Never hardcode brand-specific values in component logic.
- Use brand constants from configuration for colors, copy, assets, and behavior flags.
- Components receive brand context via the theme provider, not direct imports.
- When designing a feature, specify which brands it applies to in `meta.brands`.

### Theme Structure
- Themes are defined per brand and injected via styled-components `ThemeProvider`.
- Components access theme values via `props.theme` or the `useTheme` hook.
- Theme tokens include: colors, typography, spacing, breakpoints, brand-specific assets.

---

## 2. LaunchDarkly Feature Flags

All features requiring per-market or gradual rollout MUST include LaunchDarkly integration.

### Flag Naming Convention
- Format: `<team>-<feature>-<description>` in kebab-case
- Examples: `core-favorites-offline-sync`, `checkout-new-payment-flow`

### SDK Integration Pattern
- Use the project LaunchDarkly wrapper, not the raw SDK directly.
- Evaluate flags using the provided hook: `useFeatureFlag('flag-name')`.
- Default values must always be provided (the "off" state must be safe).
- Flag evaluation happens client-side; server-side flags use the Node SDK.

### Design Rules
- Every new feature that could affect production must have a kill switch flag.
- Design the "flag off" state first; it must match current production behavior.
- Document the flag name, default value, and expected variants in the design spec.
- Include flag cleanup as a follow-up task (remove flag after full rollout).

---

## 3. Sanity CMS Content

Content-driven features use Sanity as the headless CMS.

### Schema Patterns
- Sanity schemas are defined in the `whitelabel-cms` repository.
- Content types follow a naming convention: `<brand><ContentType>` (e.g., `br1HomePage`).
- Localized content uses Sanity's `localeString` and `localeBlock` types.

### GROQ Queries
- Frontend fetches content using GROQ (Graph-Relational Object Queries).
- Queries are co-located with the feature that uses them.
- Use projections to fetch only the fields needed (minimize payload).
- Cache Sanity responses appropriately (content changes infrequently).

### Design Rules
- If the feature displays CMS-driven content, define the Sanity schema shape.
- Specify which fields are localized and which are brand-specific.
- Document the GROQ query structure (not the query itself, but what it fetches).
- Account for content not existing yet (loading states, fallbacks).

---

## 4. Capacitor Native Plugins

The whitelabel app runs on web, iOS, and Android via Capacitor.

### Plugin Structure
- Native plugins are in `workspaces/frontend/src/plugins/`.
- Each plugin has a web implementation and native bridge definitions.
- Platform-specific code is isolated behind the plugin interface.

### Bridge Patterns
- Use `@capacitor/core` `registerPlugin` to define plugin interfaces.
- Web fallbacks must exist for every native capability.
- Platform detection: use `Capacitor.isNativePlatform()` not user-agent sniffing.

### Design Rules
- Always use `globalThis` instead of `window` for cross-platform compatibility.
- Design features to degrade gracefully on web when native APIs are unavailable.
- If the feature requires a new native capability, document the plugin interface.
- Specify platform-specific behavior differences in the design (e.g., biometric auth).

---

## 5. Apollo GraphQL Client

The primary data fetching layer for the frontend.

### Query Patterns
- Queries are defined in `.graphql` files or tagged template literals.
- Types are auto-generated via GraphQL Codegen (`yarn apollo:generate`).
- Use generated hooks: `useGetUserFavoritesQuery()` not raw `useQuery()`.

### Cache Policies
- `cache-first`: For data that rarely changes (menu items, store locations).
- `cache-and-network`: For data that changes moderately (user profile, favorites).
- `network-only`: For data that must always be fresh (cart, order status).
- `no-cache`: For one-time operations (authentication tokens).

### Optimistic Updates
- Use optimistic responses for mutations that affect UI state immediately.
- Define the optimistic response shape in the design spec.
- Specify cache update logic (which queries to refetch or update in cache).

### Error Handling
- Every query and mutation must have error handling designed.
- Use Apollo's `onError` link for global error handling.
- Design retry strategies for transient failures.
- Map GraphQL errors to user-facing messages.

### Design Rules
- Never bypass Apollo's cache with direct fetch calls for GraphQL data.
- Design queries to minimize over-fetching (use fragments for shared fields).
- Specify cache policies for every query in the design spec.
- Account for loading, error, and empty states in every data-driven component.

---

## 6. styled-components

The styling solution for the whitelabel app.

### Theme Usage
- Access theme via `${({ theme }) => theme.token.path}` in styled components.
- Use theme tokens for all colors, spacing, typography, and breakpoints.
- Never use hardcoded color values or pixel sizes.

### Responsive Patterns
- Use theme breakpoints for responsive design: `theme.breakpoints.mobile`, `theme.breakpoints.tablet`.
- Mobile-first approach: base styles are mobile, add breakpoints for larger screens.
- Use CSS Grid and Flexbox for layout, not absolute positioning.

### Brand-Aware Styling
- Brand-specific styles come from the theme, not conditional logic in components.
- If a component looks different per brand, the difference is in theme tokens.
- Shared components use only theme tokens, never brand-specific constants.

### Design Rules
- Specify which theme tokens a new component will use.
- If new tokens are needed, document them and note they must be added to all brand themes.
- Design responsive behavior explicitly (mobile, tablet, desktop breakpoints).
- Never design styles that depend on brand-specific CSS classes.

---

## 7. Redux Toolkit

Used for global state management when React Context is insufficient.

### Slice Structure
- One slice per feature domain: `favoritesSlice`, `cartSlice`, `userSlice`.
- Slices are defined with `createSlice` from `@reduxjs/toolkit`.
- Async operations use `createAsyncThunk`.
- Selectors are co-located with the slice file.

### Selector Patterns
- Use `createSelector` from `reselect` for derived/computed state.
- Selectors are the public API of a slice; components never access state directly.
- Name selectors with `select` prefix: `selectFavoriteItems`, `selectCartTotal`.

### Design Rules
- Use Redux only when state must be shared across distant components.
- Prefer Apollo cache for server-state and React Context for scoped UI state.
- If a Redux slice is needed, define its shape in `data_models.state_shape`.
- Specify all actions, thunks, and selectors in the design.
- Follow existing slice patterns found in `workspaces/frontend/src/state/`.

---

## 8. Logger (`@client/logger`)

Structured logging is mandatory for all service code.

### Logger Setup
```
import { logger as clientLogger } from '@client/logger';

const logger = clientLogger.child({
  module: 'CORE_USERS_EXPIRE_POINTS',
  step: 'QUERY_EXPIRED',
});
```

### Naming Conventions
- `module`: UPPER_SNAKE_CASE with service prefix. Example: `CORE_TRANSACTION_CREATE`.
- `step`: UPPER_SNAKE_CASE describing the operation phase. Example: `VALIDATE_INPUT`, `QUERY_DB`, `SEND_EVENT`.
- Message format: `[TopicOfConcern] Descriptive message`.

### Design Rules
- Every service-level component must specify its logger module and steps.
- Never use `console.log` in production code; always use the structured logger.
- Never log PII (email, phone, name, address, payment data, government IDs).
- Never log raw user objects; log only anonymized identifiers.
- Log key events: operation start, success, failure, retry, timeout.
- Include correlation IDs (request ID, transaction ID) in log context.

---

## 9. DynamoDB Patterns

Used by backend services.

### Table Design
- **Single-table design** is preferred for services with complex access patterns.
- **Multi-table** is acceptable for simple services with few access patterns.
- Partition key and sort key design must support all required query patterns.

### GSI Design
- Global Secondary Indexes support additional access patterns.
- Design GSIs based on the queries the feature needs, not the data structure.
- Minimize GSI count (max 20 per table, but aim for fewer).
- Use sparse indexes where not all items need the GSI.

### Access Patterns
- Document every access pattern the feature requires:
  - What data is needed?
  - What is the partition key and sort key for the query?
  - Is a GSI needed?
  - What are the expected read/write volumes?

### Design Rules
- Specify the table name, key schema, and GSI definitions.
- Document item schemas with all attributes and their types.
- Design for single-digit millisecond reads at scale.
- Use DynamoDB transactions for operations that must be atomic.
- Follow existing repository patterns in `core-service/data/`.

---

## 10. Serverless Framework

Lambda deployment and infrastructure-as-code for backend services.

### Handler Patterns
- Lambda handlers are thin wrappers: validate input, call service, return response.
- Business logic lives in service classes, never in the handler function.
- Use middleware pattern (middy or custom) for cross-cutting concerns.

### Middleware Stack
Common middleware in order:
1. Request parsing (JSON body, query params)
2. Authentication/authorization
3. Input validation
4. Logging context setup (correlation IDs)
5. Error handling wrapper

### Error Handling
- Lambda handlers catch all errors and return structured error responses.
- Use custom error classes with HTTP status codes and error codes.
- Never let unhandled errors crash the Lambda; wrap in try/catch.
- Log errors with full context before returning the error response.

### Design Rules
- Specify the Lambda handler entry point and its route configuration.
- Define IAM permissions the Lambda needs (least privilege).
- Document environment variables the Lambda requires.
- Specify timeout and memory settings (follow existing conventions unless changing them is justified).
- Use `nodejs20.x` runtime for new Lambdas.
- Follow existing patterns in `core-service/serverless.yml` and `core-middleware/serverless.yml`.

---

## Cross-Cutting Patterns

### Observability
- Every new service or major feature must include:
  - Datadog metrics for key operations (latency, error rate, throughput)
  - Dashboard panels for service health
  - Alerts for error rate spikes and latency degradation
- Design which metrics and alerts are needed as part of the architecture.

### Internationalization (i18n)
- All user-facing text must be externalized for translation.
- Use `react-intl` for frontend string localization.
- Design content structures that support locale-specific overrides.
- Never hardcode user-facing strings in component designs.

### Accessibility (a11y)
- Design components with semantic HTML structure in mind.
- Specify ARIA attributes for interactive components.
- Ensure keyboard navigation paths are documented.
- Color contrast must meet WCAG AA standards (handled by theme tokens).

### Performance
- Specify code-splitting boundaries for large features.
- Design lazy loading for below-the-fold content.
- Account for bundle size impact of new dependencies.
- Specify image optimization strategy if the feature includes media.
