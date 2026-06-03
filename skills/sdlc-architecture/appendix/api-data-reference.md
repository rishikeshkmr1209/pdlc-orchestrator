# Architecture Skill — API & Data Model Field Reference

This file contains the detailed field-by-field specifications for API contracts and data models.
Read this file only when you need the exact field definitions for producing `ph2_design_spec.md`.

---

## Phase 7: API Contract Design — Field Specifications

### GraphQL Queries

For each query:
- `name`: Query operation name (PascalCase)
- `description`: What the query fetches
- `variables`: Array of `{ name, type, required, default? }`
- `return_type`: The GraphQL return type name
- `cache_policy`: One of `cache-first`, `network-only`, `cache-and-network`, `no-cache`

### GraphQL Mutations

For each mutation:
- `name`: Mutation operation name (PascalCase)
- `description`: What the mutation does
- `variables`: Array of `{ name, type, required }`
- `return_type`: The GraphQL return type name
- `optimistic_response`: Boolean — should the UI update before server confirms?
- `cache_update`: Description of how the Apollo cache should be updated
- **Error handling**: Every mutation MUST have error handling defined (in the description or as a separate note)

### Custom Hooks

For each hook:
- `name`: Must start with `use` followed by PascalCase (e.g., `useFavorites`)
- `purpose`: What the hook encapsulates
- `parameters`: Array of `{ name, type, optional? }`
- `returns`: Object with `type` and `properties[]` array defining the return shape

### Context APIs

If the feature requires React Context:
- Provider component name and location
- Context value shape (TypeScript interface)
- Consumer hook name (e.g., `useFeatureContext`)

---

## Phase 8: Data Model Design — Field Specifications

### Types and Interfaces

For each type:
- `name`: PascalCase type name
- `kind`: `interface`, `type`, or `enum`
- `description`: What this type represents
- `properties`: Array of `{ name, type, optional?, description }`
- `values`: Array of string values (enums only)

### Design Rules

- Extend existing types where possible instead of creating new ones
- Use `interface` for object shapes that may be extended
- Use `type` for unions, intersections, and mapped types
- Use `enum` sparingly; prefer string literal unions unless the enum is used across many files
- Document every field's purpose

### State Shape

If the feature has local or global state:
- Define the complete state shape as a nested object
- Specify initial values
- Note which state is persisted vs. ephemeral
- If using Redux, define the slice name and reducer structure
