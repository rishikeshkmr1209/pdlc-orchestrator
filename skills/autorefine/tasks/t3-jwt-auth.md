---
id: t3-jwt-auth
tier: 3
token_budget: 30000
expected_turns: 14
---

# Task: Add JWT Auth Middleware to Express API

## Description

Create an Express.js REST API with JWT authentication middleware. The API should have public routes (health check, login) and protected routes (user profile, data endpoints). The auth middleware verifies JWT tokens from the Authorization header. Include tests for both authenticated and unauthenticated requests.

## Success Criteria

- [ ] Express server starts on configurable port
- [ ] `POST /login` returns a signed JWT token
- [ ] `GET /health` is publicly accessible without auth
- [ ] `GET /profile` returns 401 without valid token
- [ ] `GET /profile` returns user data with valid token
- [ ] Auth middleware extracts and verifies JWT from `Authorization: Bearer <token>`
- [ ] Tests cover both authenticated and unauthenticated flows
- [ ] No hardcoded secrets (use environment variables)

## Setup Commands

```bash
npm init -y && npm install express jsonwebtoken && npm install --save-dev jest supertest
```
