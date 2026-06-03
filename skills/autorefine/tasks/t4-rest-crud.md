---
id: t4-rest-crud
tier: 4
token_budget: 35000
expected_turns: 16
---

# Task: Build REST API with CRUD, Validation, and Error Handling

## Description

Build a complete REST API for managing "items" (e.g., products) with full CRUD operations, input validation, structured error handling, and comprehensive tests. Use Express.js with in-memory storage. The API should follow REST conventions (proper status codes, JSON responses, error shapes).

## Success Criteria

- [ ] `POST /items` creates an item with validation (name required, price > 0)
- [ ] `GET /items` lists all items with optional `?sort=price` query param
- [ ] `GET /items/:id` returns a single item or 404
- [ ] `PUT /items/:id` updates an item with validation
- [ ] `DELETE /items/:id` deletes an item or 404
- [ ] Validation errors return 400 with structured error body `{ error, details }`
- [ ] Server errors return 500 with generic message (no stack traces)
- [ ] Tests cover happy paths, validation failures, 404s, and edge cases
- [ ] Code quality: no lint errors, consistent error handling pattern

## Setup Commands

```bash
npm init -y && npm install express && npm install --save-dev jest supertest eslint
```
