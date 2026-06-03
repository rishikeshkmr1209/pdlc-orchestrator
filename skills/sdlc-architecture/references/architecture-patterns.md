# Architecture Patterns Reference

This reference documents when to use each architectural pattern supported by the
`sdlc-architecture` skill. The pattern is specified in `architecture.pattern` in
the `ph2_design_spec.md` output.

---

## 1. Container/Presenter (`container_presenter`)

**Default pattern for React UI features.**

### When to Use
- Building React UI features with a clear separation between data logic and visual rendering
- Features where the same UI may be driven by different data sources
- Components that need to be reusable across brands or pages
- Most frontend features in the whitelabel app

### Structure
```
feature/
  containers/          # Data fetching, state management, business logic
    FeatureContainer.tsx
  components/          # Pure rendering, receives all data via props
    FeatureView.tsx
    FeatureItemCard.tsx
  hooks/               # Shared business logic extracted into hooks
    useFeature.ts
  types/               # TypeScript interfaces and types
    index.ts
  graphql/             # GraphQL operations
    queries.ts
    mutations.ts
```

### Component Roles
- **Container**: Fetches data, manages state, handles side effects. No JSX layout logic.
- **Presenter**: Renders UI from props. No data fetching. No direct state mutations.
- **Hook**: Encapsulates reusable logic shared between containers or features.

### Pros
- Clear separation of concerns
- Presenters are easy to test (pure props in, JSX out)
- Containers can be swapped without changing UI
- Familiar pattern for most React developers

### Cons
- Can lead to prop drilling if hierarchy is deep (mitigate with context or composition)
- Extra files for simple features (overhead for trivial components)

### Codebase Examples
- CDP provider pattern in `workspaces/frontend/src/state/cdp/`
- Layout components in `workspaces/frontend/src/components/layout/`
- Page-level containers throughout `workspaces/frontend/src/pages/`

---

## 2. Feature-Sliced Design (`feature_sliced`)

### When to Use
- Complex features with multiple sub-domains that need independent development
- Features spanning many screens, workflows, or user journeys
- When multiple teams might work on different parts of the same feature
- Large features where co-location of all related code improves discoverability

### Structure
```
features/
  feature-name/
    api/               # API integration (hooks, queries, mutations)
      useFeatureQuery.ts
      mutations.ts
    model/             # State management (Redux slices, context, stores)
      slice.ts
      selectors.ts
    ui/                # React components (containers + presenters co-located)
      FeaturePage.tsx
      FeatureCard.tsx
    lib/               # Utilities, helpers, constants specific to this feature
      validators.ts
      constants.ts
    types/             # TypeScript types scoped to this feature
      index.ts
    __tests__/         # Tests co-located with feature
      feature.test.ts
```

### Layer Rules
- `api/` depends on `model/` and `types/`
- `ui/` depends on `api/`, `model/`, and `lib/`
- `model/` depends only on `types/`
- `lib/` depends only on `types/`
- No circular dependencies between layers

### Pros
- All feature code in one place (high cohesion)
- Clear internal boundaries prevent spaghetti
- Easy to delete or refactor an entire feature
- Scales well for large features with many sub-concerns

### Cons
- Overhead for small features (unnecessary directory depth)
- Requires discipline to maintain layer boundaries
- Less familiar to developers used to flat component structures

### Codebase Examples
- Loyalty engine service modules in `core-service/services/`
- Payment integration features in `workspaces/frontend/src/payments/`

---

## 3. Clean Architecture (`clean_architecture`)

### When to Use
- Backend service layers (Lambda handlers, Express services)
- Features with complex business rules that must be testable in isolation
- When business logic must be independent of framework, UI, or database
- Loyalty Engine and Middleware service design

### Structure
```
service/
  domain/              # Business entities and rules (zero dependencies)
    entities/
      Order.ts
    value-objects/
      Money.ts
    errors/
      InsufficientPointsError.ts
  application/         # Use cases / application services
    use-cases/
      CreateTransaction.ts
    ports/              # Interfaces for external dependencies
      ITransactionRepository.ts
      INotificationService.ts
  infrastructure/      # Implementations of ports
    repositories/
      DynamoTransactionRepository.ts
    services/
      SESNotificationService.ts
  api/                 # Entry points (REST controllers, Lambda handlers)
    controllers/
      TransactionController.ts
```

### Layer Rules (strict dependency direction: outer depends on inner)
- **Domain**: No imports from other layers. Pure business logic.
- **Application**: Imports from Domain. Defines port interfaces.
- **Infrastructure**: Imports from Application (implements ports) and Domain.
- **API**: Imports from Application. Never imports Infrastructure directly (use DI).

### Pros
- Business logic fully testable without mocks for database or HTTP
- Easy to swap infrastructure (DynamoDB to PostgreSQL, SES to SendGrid)
- Forces explicit dependency boundaries
- Scales well for complex domains

### Cons
- Significant boilerplate for simple CRUD features
- Over-engineering for thin API layers with no complex logic
- Requires dependency injection setup

### Codebase Examples
- Loyalty Engine in `core-service/` (services, data, api layers)
- Loyalty Middleware in `core-middleware/` (api, gql, services, data layers)

---

## 4. MVVM — Model-View-ViewModel (`mvvm`)

### When to Use
- State-heavy features with complex UI state transformations
- Features where the view state differs significantly from the data model
- Form-heavy features with validation, computed fields, and derived state
- Features needing bidirectional data binding patterns

### Structure
```
feature/
  models/              # Data layer (API types, domain models)
    FeatureModel.ts
  view-models/         # State transformation and business logic for the view
    useFeatureViewModel.ts
  views/               # React components (consume view-model, render UI)
    FeatureView.tsx
    FeatureForm.tsx
  types/
    index.ts
```

### Component Roles
- **Model**: Raw data types and API response shapes. No UI logic.
- **ViewModel**: Hook that transforms model data into view-ready state. Handles validation, computed fields, formatting. Exposes actions.
- **View**: Renders based on view-model output. No data transformation.

### Pros
- Clean separation between data shape and UI shape
- ViewModels are independently testable
- Complex form state is well-organized
- View components stay simple

### Cons
- Extra abstraction layer that may not be needed for simple views
- Can be confusing to developers unfamiliar with MVVM in React
- ViewModel hooks can grow large without discipline

### Codebase Examples
- Complex form patterns in checkout flows
- Cart state management with computed totals and validation

---

## 5. MVC — Model-View-Controller (`mvc`)

### When to Use
- Traditional server-side features (Express/Serverless handlers)
- REST API endpoints with straightforward request/response cycles
- TSOA controller patterns in Loyalty Engine and Middleware
- When the existing codebase already follows MVC conventions

### Structure
```
service/
  models/              # Data access and business entities
    TransactionModel.ts
  controllers/         # Request handling, input validation, response formatting
    TransactionController.ts
  services/            # Business logic (optional, for complex operations)
    TransactionService.ts
  types/
    index.ts
```

### Component Roles
- **Model**: Data access layer. Talks to database/external services.
- **Controller**: Receives HTTP request, validates input, calls service/model, returns response.
- **Service** (optional): Business logic that sits between controller and model.

### Pros
- Simple and well-understood by most developers
- Maps naturally to REST API structure
- Low overhead for CRUD-style features
- Matches TSOA controller patterns in the project backend

### Cons
- Controllers can become bloated without discipline
- No clear boundary for complex business logic (service layer helps)
- Not well-suited for complex UI state management

### Codebase Examples
- Loyalty Engine controllers in `core-service/api/`
- Loyalty Middleware controllers in `core-middleware/api/`
- TSOA-decorated controllers throughout backend services

---

## Pattern Selection Decision Tree

```
Is this a backend/service feature?
  YES -> Does it have complex business rules?
    YES -> clean_architecture
    NO  -> mvc
  NO  -> Is this a React UI feature?
    YES -> Is it a simple component or page?
      YES -> container_presenter (default)
      NO  -> Is it state-heavy with complex form logic?
        YES -> mvvm
        NO  -> Does it span multiple sub-domains?
          YES -> feature_sliced
          NO  -> container_presenter (default)
```

Always document the pattern choice as ADR-001 with at least two alternatives considered.
