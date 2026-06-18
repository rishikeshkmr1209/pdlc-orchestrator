# Architecture Design Specification: 1234

## Meta

- **Ticket:** 1234
- **Feature:** Tic-Tac-Toe React App
- **Date:** 2026-06-04
- **Author:** Claude (sdlc-architecture)
- **Version:** v1
- **Status:** pending_review
- **codebase_location:** `src/` (greenfield — created during implementation)
- **codebase_analyzed:** false
- **ready_for_implementation:** true
- **iteration_history:** []

---

## Problem Spec Reference

- **Source:** `docs/artifacts/1234/ph1_problem_spec.md`
- **Requirements addressed:** REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006
- **Non-goals confirmed:** AI opponent (NG-001), networked multiplayer (NG-002), persistent storage (NG-003)

---

## Current Architecture

- **Description:** Greenfield application. No existing codebase to analyze. This is a brand-new React app with no prior implementation.
- **codebase_analyzed:** false
- **Existing Components:** None — all components are new.
- **Existing Patterns:** None established — all patterns are chosen fresh for this project.
- **Integration Points:** None — standalone app with no external services.

---

## Architecture

### Pattern

**`container_presenter`** — The `GameContainer` owns all game state and business logic. Presentational components receive data and callbacks as props; they hold no state of their own. This cleanly separates testable game logic from rendering concerns.

### Components

| ID | Name | Type | Responsibility | File Path |
|----|------|------|----------------|-----------|
| COMP-001 | `GameContainer` | container | Owns all game state (board, currentPlayer, gameStatus, score); derives computed values; dispatches actions to game-logic utilities | `src/components/GameContainer.tsx` |
| COMP-002 | `Board` | presenter | Renders the 3×3 grid of Square cells; receives board state and onSquareClick callback | `src/components/Board.tsx` |
| COMP-003 | `Square` | presenter | Renders a single clickable board cell; displays the mark (X, O, or empty) and handles the click | `src/components/Square.tsx` |
| COMP-004 | `StatusDisplay` | presenter | Renders current turn prompt, win announcement, or draw message based on gameStatus | `src/components/StatusDisplay.tsx` |
| COMP-005 | `ScoreBoard` | presenter | Renders the running score (X wins, O wins, draws) | `src/components/ScoreBoard.tsx` |
| COMP-006 | `NewGameButton` | presenter | Renders the "New Game" button and fires the onNewGame callback | `src/components/NewGameButton.tsx` |
| COMP-007 | `useGameState` | hook | Encapsulates game state (board, currentPlayer, gameStatus, score) and all mutation actions (handleSquareClick, handleNewGame) | `src/hooks/useGameState.ts` |
| COMP-008 | `gameLogic` | utility | Pure functions: `calculateWinner`, `checkDraw`, `getInitialBoard` — no React dependency | `src/utils/gameLogic.ts` |
| COMP-009 | `App` | container | Root component: renders `GameContainer` within the app shell | `src/App.tsx` |

**Component dependency graph:**
- COMP-009 → COMP-001
- COMP-001 → COMP-007 (uses hook), COMP-002, COMP-004, COMP-005, COMP-006
- COMP-002 → COMP-003
- COMP-007 → COMP-008 (calls pure logic functions)

---

## API Contracts

### Hook Interface: `useGameState` (COMP-007)

```
Hook: useGameState()
Returns:
  board:         Mark[][]         — 3×3 array of 'X' | 'O' | null
  currentPlayer: 'X' | 'O'       — whose turn it is
  gameStatus:    GameStatus        — 'playing' | 'won' | 'draw'
  winner:        'X' | 'O' | null — populated only when gameStatus='won'
  score:         Score             — { X: number, O: number, draws: number }
  handleSquareClick: (row: number, col: number) => void
  handleNewGame:     () => void
```

**`handleSquareClick(row, col)`**
- No-op if `gameStatus !== 'playing'`
- No-op if `board[row][col]` is already occupied
- Updates board, flips `currentPlayer`, recalculates `gameStatus` and `winner`
- If game ends: increments the appropriate `score` counter

**`handleNewGame()`**
- Resets `board` to all-null
- Resets `currentPlayer` to `'X'`
- Resets `gameStatus` to `'playing'`, `winner` to `null`
- Score is **not** reset

### Pure Functions: `gameLogic` (COMP-008)

```
calculateWinner(board: Mark[][]): 'X' | 'O' | null
  — Checks all 8 winning lines; returns the winning mark or null

checkDraw(board: Mark[][]): boolean
  — Returns true if all cells are filled and calculateWinner returns null

getInitialBoard(): Mark[][]
  — Returns a 3×3 array of null values
```

### Component Props

**`Board` (COMP-002)**
```
board:          Mark[][]
onSquareClick:  (row: number, col: number) => void
disabled:       boolean   — true when gameStatus !== 'playing'
```

**`Square` (COMP-003)**
```
value:    Mark    — 'X' | 'O' | null
onClick:  () => void
disabled: boolean
```

**`StatusDisplay` (COMP-004)**
```
gameStatus:    GameStatus
currentPlayer: 'X' | 'O'
winner:        'X' | 'O' | null
```

**`ScoreBoard` (COMP-005)**
```
score: Score   — { X: number, O: number, draws: number }
```

**`NewGameButton` (COMP-006)**
```
onNewGame: () => void
```

---

## Data Models

```
type Mark = 'X' | 'O' | null

type GameStatus = 'playing' | 'won' | 'draw'

interface Score {
  X:     number
  O:     number
  draws: number
}

interface GameState {
  board:         Mark[][]
  currentPlayer: 'X' | 'O'
  gameStatus:    GameStatus
  winner:        Mark
  score:         Score
}
```

**Initial state:**
```
board:         [[null, null, null], [null, null, null], [null, null, null]]
currentPlayer: 'X'
gameStatus:    'playing'
winner:        null
score:         { X: 0, O: 0, draws: 0 }
```

---

## Decisions (ADRs)

### ADR-001: Architecture Pattern — Container/Presenter

- **Context:** Greenfield React app; need to separate game state/logic from rendering.
- **Decision:** Use `container_presenter` pattern. `GameContainer` holds state via `useGameState` hook; all child components are purely presentational.
- **Alternatives considered:**
  - *Redux/Zustand global store:* Overkill for a single-screen app with no shared state across routes. Adds boilerplate and a dependency with no benefit.
  - *Flat single-component approach:* All logic in `App.tsx`. Simple initially but untestable and violates single responsibility.
- **Consequences:**
  - Positive: Game logic is testable in isolation (pure hook + pure utility functions). Presenters are trivially testable with any props.
  - Negative: Prop drilling from GameContainer down to Square (two levels). Acceptable given the app's depth.
  - Risk: None significant for this scope.

### ADR-002: Game Logic as Pure Functions (No Side Effects)

- **Context:** Win detection, draw detection, and board initialization need to be correct and easily testable.
- **Decision:** Implement `calculateWinner`, `checkDraw`, and `getInitialBoard` as pure functions in `src/utils/gameLogic.ts` with no React dependency.
- **Alternatives considered:**
  - *Logic inside the hook:* Mixes pure computation with React state concerns; harder to unit test the logic in isolation.
  - *Logic inline in component:* Untestable, violates single responsibility.
- **Consequences:**
  - Positive: Pure functions have 100% deterministic, dependency-free unit tests. Logic can be reused if scope expands.
  - Negative: Slight extra file. Negligible for this scope.

### ADR-003: No External State Management Library

- **Context:** This is a simple single-screen app. C-004 explicitly prohibits backend/DB. Score is in-memory only.
- **Decision:** Use React `useState` via `useGameState` hook. No Redux, Zustand, or Context required.
- **Alternatives considered:**
  - *React Context:* Useful when sharing state across deeply nested trees or multiple routes. Not needed here — state is consumed in one place (GameContainer).
  - *Zustand:* Lightweight, but still an external dependency without justification.
- **Consequences:**
  - Positive: Zero new dependencies. Simplest possible solution.
  - Negative: If scope expands (AI, multiplayer), state management would need revisiting. Acceptable per NG-001, NG-002.

### ADR-004: No CSS-in-JS or External Styling Library

- **Context:** ASM-001 states standard clean UI is acceptable. No design system is specified. C-003 is local dev only.
- **Decision:** Use plain CSS modules (`*.module.css`) for component scoping. No styled-components, Tailwind, or Material UI.
- **Alternatives considered:**
  - *Tailwind CSS:* Requires setup (PostCSS config, class memorization). Not worth the overhead for a local dev app.
  - *Inline styles:* Difficult to maintain, no pseudo-class support.
  - *Global CSS file:* Name collisions in larger apps; CSS modules are the standard scoped alternative.
- **Consequences:**
  - Positive: Zero new dependencies. Standard React toolchain support.
  - Negative: Slightly more verbose than Tailwind for simple layouts. Acceptable.

---

## Implementation Guidelines

### File Structure

```
src/
  App.tsx                            — COMP-009: root component
  App.module.css                     — App-level layout styles
  components/
    GameContainer.tsx                — COMP-001: state owner
    Board.tsx                        — COMP-002: grid renderer
    Board.module.css
    Square.tsx                       — COMP-003: single cell
    Square.module.css
    StatusDisplay.tsx                — COMP-004: game status text
    StatusDisplay.module.css
    ScoreBoard.tsx                   — COMP-005: score display
    ScoreBoard.module.css
    NewGameButton.tsx                — COMP-006: reset action
    NewGameButton.module.css
  hooks/
    useGameState.ts                  — COMP-007: state + actions hook
  utils/
    gameLogic.ts                     — COMP-008: pure logic functions
  __tests__/
    gameLogic.test.ts                — unit tests for COMP-008
    useGameState.test.ts             — hook tests (renderHook)
    GameContainer.test.tsx           — integration tests
    Board.test.tsx
    Square.test.tsx
    StatusDisplay.test.tsx
    ScoreBoard.test.tsx
```

### Naming Conventions

- **Components:** PascalCase (`GameContainer`, `Board`, `Square`)
- **Hooks:** camelCase with `use` prefix (`useGameState`)
- **Types/Interfaces:** PascalCase (`GameState`, `Score`, `Mark`)
- **Constants:** UPPER_SNAKE_CASE (`WINNING_LINES`)
- **CSS modules:** kebab-case matching component (`game-container.module.css` or `GameContainer.module.css` — pick one and be consistent; prefer `Board.module.css` to match component name)
- **Test files:** `*.test.ts` / `*.test.tsx` in `src/__tests__/`

### Patterns to Use

- `useState` for all state in `useGameState`
- Derive computed values (`winner`, `gameStatus`) inside the hook after each `board` change — do not store them as separate independent state
- Pass callbacks as props (do not use Context for this depth)
- `disabled` prop on `Square` to prevent interaction after game ends — do not rely on `gameStatus` check inside Square

### Patterns to Avoid

- **No direct DOM manipulation** — all updates via React state
- **No `useEffect` for game logic** — win/draw detection is synchronous and should be computed inline in the state update function, not in an effect
- **No game state outside `useGameState`** — `GameContainer` must not duplicate state
- **No `any` TypeScript type** — use the defined types (`Mark`, `GameStatus`, `Score`)

### Libraries

All existing React toolchain dependencies (React, ReactDOM). No new libraries required.

### Code Standards

- TypeScript strict mode
- All component files export a single default component
- `gameLogic.ts` exports named functions (no default export)
- `useGameState.ts` exports a named hook

---

## Testing Strategy

### Unit Test Targets

- `calculateWinner` — test all 8 winning lines for X, all 8 for O, no winner (full board), partial board
- `checkDraw` — test full board no winner (true), full board with winner (false), partial board (false)
- `getInitialBoard` — test returns 3×3 null array
- `useGameState` via `renderHook` — test initial state, square click updates board, win detection increments score, draw detection increments draws, occupied square click is no-op, `handleNewGame` resets board but not score

### Integration Test Targets

- `GameContainer` — render full component; simulate a complete game (X wins); verify announcement and score; click New Game; verify board reset
- `Board` — renders 9 squares; clicking a square fires `onSquareClick` with correct (row, col)
- `Square` — disabled square does not fire onClick

### E2E Scenarios

- **Happy path win:** Player X clicks squares to complete a row → win message shown → score updates → New Game resets board
- **Draw:** All squares filled with no winner → draw message shown → draw counter increments
- **Invalid move prevention:** Click occupied square → board unchanged → turn unchanged

### Coverage Target

- **≥80% coverage** on `gameLogic.ts` and `useGameState.ts` (business logic)
- Presentational components: render smoke tests sufficient

---

## Security Considerations

| Concern | Mitigation | OWASP Category |
|---------|-----------|----------------|
| No user-supplied data processed | Game state is fully client-side; no input sanitization required | N/A |
| No network requests | No CORS, CSRF, or injection vectors; entirely local | N/A |
| No persistent storage | No localStorage read/write; no data leakage on page unload | A02: Cryptographic Failures (N/A by elimination) |
| XSS via React | React escapes all rendered values by default; no `dangerouslySetInnerHTML` used | A03: Injection — not applicable |

**Security verdict:** No security concerns for this feature. Fully local, no external I/O.
