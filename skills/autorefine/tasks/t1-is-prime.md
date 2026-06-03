---
id: t1-is-prime
tier: 1
token_budget: 20000
expected_turns: 10
---

# Task: Write isPrime Function

## Description

Write a function `isPrime(n)` in JavaScript that returns `true` if `n` is a prime number and `false` otherwise. Include unit tests using Jest. The function should handle edge cases (0, 1, negative numbers).

## Success Criteria

- [ ] Function `isPrime` exists and is exported from `src/is-prime.js`
- [ ] Returns `true` for 2, 3, 5, 7, 11, 13
- [ ] Returns `false` for 0, 1, 4, 6, 8, 9, -1
- [ ] Unit tests exist in `src/is-prime.test.js` and pass
- [ ] No lint errors when running `npx eslint src/`

## Setup Commands

```bash
mkdir -p src && npm init -y && npm install --save-dev jest eslint
```
