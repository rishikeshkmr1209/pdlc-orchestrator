---
id: t2-todo-cli
tier: 2
token_budget: 25000
expected_turns: 10
---

# Task: Build CLI Todo App

## Description

Build a command-line todo application in Node.js with four operations: add, list, complete, and delete. Todos persist to a JSON file (`todos.json`). Each todo has an id (auto-increment), title, and completed status. Include unit tests.

## Success Criteria

- [ ] `node todo.js add "Buy groceries"` adds a new todo
- [ ] `node todo.js list` displays all todos with status
- [ ] `node todo.js complete 1` marks todo #1 as done
- [ ] `node todo.js delete 1` removes todo #1
- [ ] Data persists to `todos.json` between invocations
- [ ] Unit tests exist and pass
- [ ] Handles edge cases: empty list, invalid id, duplicate complete

## Setup Commands

```bash
npm init -y && npm install --save-dev jest
```
