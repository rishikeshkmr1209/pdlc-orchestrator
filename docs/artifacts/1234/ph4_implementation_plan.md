# Implementation Plan: 1234

## Pipeline Context

- **Ticket:** 1234
- **Mode:** gates
- **Pipeline state:** docs/artifacts/1234/.state/pipeline_state_1234.json
- **Artifacts:** docs/artifacts/1234/ (ph1_problem_spec.md, ph2_design_spec.md, ph3b_qa_test_plan.md)

## Problem Summary

Build a browser-based Tic-Tac-Toe game in React for two local human players. The app renders a 3×3 board with alternating turns, detects wins and draws, prevents invalid moves, tracks a running score across games in the session, and provides a "New Game" reset button. This is a greenfield standalone app with no backend or persistence.

## Key Requirements & Constraints

| ID      | Priority | Description |
| ------- | -------- | ----------- |
| REQ-001 | P0       | 3×3 board where X and O alternate turns |
| REQ-002 | P0       | Detect and announce win (row, column, or diagonal) |
| REQ-003 | P0       | Detect and announce draw (board full, no winner) |
| REQ-004 | P0       | Prevent clicking already-occupied squares |
| REQ-005 | P1       | Running score (X wins, O wins, draws) across games in session |
| REQ-006 | P1       | "New Game" button resets board without clearing score |

**Constraints:**

- React framework (C-001)
- Web browser / desktop target (C-002)
- Local development only — no deployment required (C-003)
- No backend, database, or localStorage — score is in-memory only (C-004)
- No feature flag (C-005)
- TypeScript strict mode — no `any` type
- No external state management library (ADR-003)
- CSS modules for styling — no Tailwind, styled-components, or inline styles (ADR-004)
- No `useEffect` for game logic — win/draw detection must be synchronous inline in state update
- No direct DOM manipulation — all updates via React state

**Non-Goals:** AI opponent (NG-001), networked multiplayer (NG-002), persistent score storage (NG-003).

## Figma Design Token Constraints

N/A — `figma.fetched` is `false` in pipeline state. No Figma link provided.

## Architecture Summary

**Pattern:** Container/Presenter (ADR-001). `GameContainer` (COMP-001) owns all state via the `useGameState` hook (COMP-007). All child components are purely presentational — they receive data and callbacks as props and hold no state. Game logic lives in pure functions in `gameLogic.ts` (COMP-008) with no React dependency. State is managed with `useState` only (ADR-003). CSS modules provide component-scoped styles (ADR-004).

**Component dependency order:** gameLogic → useGameState; Square → Board; StatusDisplay, ScoreBoard, NewGameButton (leaf presenters); GameContainer (aggregates all); App (root).

**Key hook contract:**
```
useGameState() returns:
  board: Mark[][]          — 3×3 grid
  currentPlayer: 'X' | 'O'
  gameStatus: 'playing' | 'won' | 'draw'
  winner: 'X' | 'O' | null
  score: { X: number, O: number, draws: number }
  handleSquareClick(row, col) — no-op if game over or square occupied
  handleNewGame()            — resets board+turn; score unchanged
```

**Key types:**
```typescript
type Mark = 'X' | 'O' | null
type GameStatus = 'playing' | 'won' | 'draw'
interface Score { X: number; O: number; draws: number }
```

## Design Review Conditions

No `ph3_design_review.md` present — Small Feature phase set does not include a dedicated design review phase. No conditions to address.

## Affected Repos

Single-repo change — greenfield React app (no existing repo). All files created under `src/`.

## Pre-Implementation Baseline

This is a greenfield app with no existing test suite. Create the React app scaffold first (e.g., `npx create-react-app . --template typescript` or `npm create vite@latest . -- --template react-ts`), then record the baseline:

- Run: `npm test -- --watchAll=false` (or `npx vitest run` if Vite is used) and record pass/fail counts before writing any implementation files.

## Implementation Steps

### Execution Mode: waves

22 files across 4 waves. Implement each wave completely and verify tests pass before starting the next wave.

---

### Wave 0 — Foundation (no dependencies)

---

### Step 1: src/utils/gameLogic.ts (new) [COMP-008]

- **Purpose:** Pure utility functions — `calculateWinner`, `checkDraw`, `getInitialBoard`. No React dependency. Exported as named exports.
- **Dependencies:** none
- **Key notes:**
  - `calculateWinner(board)` checks all 8 winning lines (3 rows, 3 cols, 2 diagonals). Returns `'X' | 'O' | null`.
  - `checkDraw(board)` returns `true` only when all cells are filled AND `calculateWinner` returns `null`. Never fires when a winner is present (TC-1234-09).
  - `getInitialBoard()` returns `[[null,null,null],[null,null,null],[null,null,null]]`.
  - Export a `WINNING_LINES` constant (8 lines of [row,col] triplets) — used by `calculateWinner`.
  - No `any` type. Use `Mark[][]` parameter types.
- **Figma CSS spec:** N/A
- **Acceptance criteria:** REQ-002 (AC-002), REQ-003 (AC-003)
- **Verify:** `npm test -- --watchAll=false --testPathPattern=gameLogic`

---

### Step 2: src/components/Square.tsx (new) [COMP-003]

- **Purpose:** Single clickable board cell. Renders the mark (`X`, `O`, or empty). Accepts `disabled` prop to prevent interaction.
- **Dependencies:** none
- **Key notes:**
  - Props: `value: Mark`, `onClick: () => void`, `disabled: boolean`
  - When `disabled` is true, the button should be `disabled` (HTML attribute) so it does not fire `onClick`.
  - Do NOT check `gameStatus` inside Square — rely entirely on the `disabled` prop passed from Board.
  - Use `Square.module.css` for styling.
- **Figma CSS spec:** N/A
- **Acceptance criteria:** REQ-004 (AC-004)
- **Verify:** `npm test -- --watchAll=false --testPathPattern=Square`

---

### Step 3: src/components/Square.module.css (new) [COMP-003]

- **Purpose:** Scoped styles for Square — fixed-size button cell, border, font size for X/O marks, cursor styles.
- **Dependencies:** none
- **Key notes:** Standard CSS; no Tailwind or inline styles. Keep it minimal.
- **Figma CSS spec:** N/A
- **Acceptance criteria:** REQ-001 (visual presentation)
- **Verify:** visual check only (no unit test for CSS)

---

### Step 4: src/components/StatusDisplay.tsx (new) [COMP-004]

- **Purpose:** Displays current game status — whose turn it is, win announcement, or draw message.
- **Dependencies:** none
- **Key notes:**
  - Props: `gameStatus: GameStatus`, `currentPlayer: 'X' | 'O'`, `winner: 'X' | 'O' | null`
  - Render logic:
    - `gameStatus === 'playing'` → "Player X's turn" / "Player O's turn"
    - `gameStatus === 'won'` → "Player X wins!" / "Player O wins!"
    - `gameStatus === 'draw'` → "Draw!"
  - Pure presentational — no state, no hooks.
  - Use `StatusDisplay.module.css`.
- **Figma CSS spec:** N/A
- **Acceptance criteria:** REQ-002 (AC-002), REQ-003 (AC-003), REQ-001 (AC-001 turn display)
- **Verify:** `npm test -- --watchAll=false --testPathPattern=StatusDisplay`

---

### Step 5: src/components/StatusDisplay.module.css (new) [COMP-004]

- **Purpose:** Scoped styles for StatusDisplay — font weight, color emphasis for win/draw states.
- **Dependencies:** none
- **Figma CSS spec:** N/A
- **Acceptance criteria:** visual only
- **Verify:** visual check only

---

### Step 6: src/components/ScoreBoard.tsx (new) [COMP-005]

- **Purpose:** Displays the running score: X wins, O wins, draws.
- **Dependencies:** none
- **Key notes:**
  - Props: `score: Score` — `{ X: number; O: number; draws: number }`
  - Pure presentational. Displays three counters.
  - Use `ScoreBoard.module.css`.
- **Figma CSS spec:** N/A
- **Acceptance criteria:** REQ-005 (AC-005)
- **Verify:** `npm test -- --watchAll=false --testPathPattern=ScoreBoard`

---

### Step 7: src/components/ScoreBoard.module.css (new) [COMP-005]

- **Purpose:** Scoped styles for ScoreBoard — layout of X/O/draws counters.
- **Dependencies:** none
- **Figma CSS spec:** N/A
- **Acceptance criteria:** visual only
- **Verify:** visual check only

---

### Step 8: src/components/NewGameButton.tsx (new) [COMP-006]

- **Purpose:** Renders the "New Game" button. Fires `onNewGame` callback on click.
- **Dependencies:** none
- **Key notes:**
  - Props: `onNewGame: () => void`
  - Single `<button>` element. No internal state.
  - Use `NewGameButton.module.css`.
- **Figma CSS spec:** N/A
- **Acceptance criteria:** REQ-006 (AC-006)
- **Verify:** `npm test -- --watchAll=false --testPathPattern=NewGameButton`

---

### Step 9: src/components/NewGameButton.module.css (new) [COMP-006]

- **Purpose:** Scoped styles for NewGameButton.
- **Dependencies:** none
- **Figma CSS spec:** N/A
- **Acceptance criteria:** visual only
- **Verify:** visual check only

---

### Wave 0 Tests

---

### Step 10: src/__tests__/gameLogic.test.ts (new) [COMP-008]

- **Purpose:** Unit tests for all pure logic functions in gameLogic.ts.
- **Dependencies:** COMP-008 (Step 1 must exist)
- **Key notes:**
  - Test `calculateWinner` for all 8 winning lines (3 rows × 2 players, 3 cols × 2 players, 2 diagonals × 2 players).
  - Test `calculateWinner` returns null on partial board and on full-board draw.
  - Test `checkDraw` returns true on full board with no winner.
  - Test `checkDraw` returns false when winner exists (TC-1234-09 guard).
  - Test `checkDraw` returns false on partial board.
  - Test `getInitialBoard` returns a 3×3 all-null array.
  - Target: ≥80% coverage on `gameLogic.ts`.
- **Figma CSS spec:** N/A
- **Acceptance criteria:** REQ-002 (AC-002), REQ-003 (AC-003)
- **Verify:** `npm test -- --watchAll=false --testPathPattern=gameLogic`

---

### Step 11: src/__tests__/Square.test.tsx (new) [COMP-003]

- **Purpose:** Unit tests for Square component.
- **Dependencies:** COMP-003 (Step 2 must exist)
- **Key notes:**
  - Renders with `value='X'` → displays "X".
  - Renders with `value=null` → renders empty.
  - `disabled=true` → button has `disabled` attribute; click does not fire `onClick` (AC-004).
  - `disabled=false` → click fires `onClick` once.
- **Figma CSS spec:** N/A
- **Acceptance criteria:** REQ-004 (AC-004)
- **Verify:** `npm test -- --watchAll=false --testPathPattern=Square`

---

### Step 12: src/__tests__/StatusDisplay.test.tsx (new) [COMP-004]

- **Purpose:** Unit tests for StatusDisplay component.
- **Dependencies:** COMP-004 (Step 4 must exist)
- **Key notes:**
  - `gameStatus='playing', currentPlayer='X'` → shows X's turn message.
  - `gameStatus='playing', currentPlayer='O'` → shows O's turn message.
  - `gameStatus='won', winner='X'` → shows X wins message.
  - `gameStatus='won', winner='O'` → shows O wins message.
  - `gameStatus='draw'` → shows Draw message.
- **Figma CSS spec:** N/A
- **Acceptance criteria:** REQ-001 (AC-001), REQ-002 (AC-002), REQ-003 (AC-003)
- **Verify:** `npm test -- --watchAll=false --testPathPattern=StatusDisplay`

---

### Step 13: src/__tests__/ScoreBoard.test.tsx (new) [COMP-005]

- **Purpose:** Unit tests for ScoreBoard component.
- **Dependencies:** COMP-005 (Step 6 must exist)
- **Key notes:**
  - Renders `{ X: 0, O: 0, draws: 0 }` correctly.
  - Renders `{ X: 3, O: 1, draws: 2 }` correctly — each counter independently updated.
- **Figma CSS spec:** N/A
- **Acceptance criteria:** REQ-005 (AC-005)
- **Verify:** `npm test -- --watchAll=false --testPathPattern=ScoreBoard`

---

### Wave 1 — Composite Components (depend on Wave 0)

---

### Step 14: src/hooks/useGameState.ts (new) [COMP-007]

- **Purpose:** React hook encapsulating all game state and actions. Calls `gameLogic` pure functions internally.
- **Dependencies:** COMP-008 (gameLogic — Step 1)
- **Key notes:**
  - Uses `useState` for `board`, `currentPlayer`, `score`. Derives `gameStatus` and `winner` synchronously in `handleSquareClick` — NOT in `useEffect`.
  - `handleSquareClick(row, col)`:
    1. Guard: `if (gameStatus !== 'playing') return`
    2. Guard: `if (board[row][col] !== null) return`
    3. Compute new board by spreading and setting `board[row][col] = currentPlayer`
    4. Run `calculateWinner(newBoard)` → derive `newWinner`
    5. Run `checkDraw(newBoard)` → derive `newDraw`
    6. Compute `newGameStatus`: 'won' if winner, 'draw' if draw, else 'playing'
    7. If game ends: increment appropriate `score` counter atomically in the same `setState` call
    8. Flip `currentPlayer` only if `newGameStatus === 'playing'`
  - `handleNewGame()`: resets board to `getInitialBoard()`, `currentPlayer` to `'X'`, `gameStatus` to `'playing'`, `winner` to `null`. Score is NOT reset (AC-006).
  - Export as named export: `export function useGameState()`
- **Figma CSS spec:** N/A
- **Acceptance criteria:** REQ-001 (AC-001), REQ-002 (AC-002), REQ-003 (AC-003), REQ-004 (AC-004), REQ-005 (AC-005), REQ-006 (AC-006)
- **Verify:** `npm test -- --watchAll=false --testPathPattern=useGameState`

---

### Step 15: src/components/Board.tsx (new) [COMP-002]

- **Purpose:** Renders the 3×3 grid of Square cells. Maps board state to Square components.
- **Dependencies:** COMP-003 (Square — Step 2)
- **Key notes:**
  - Props: `board: Mark[][]`, `onSquareClick: (row: number, col: number) => void`, `disabled: boolean`
  - Renders a 3×3 grid. For each cell at `[row][col]`, renders a `<Square>` with the correct `value`, `onClick={() => onSquareClick(row, col)}`, and `disabled` prop.
  - The `disabled` prop passed to each Square should be `disabled || board[row][col] !== null` — Square is disabled when game is over OR when the cell is occupied. This ensures the `disabled` HTML attribute is always set correctly for occupied cells (AC-004).
  - Use `Board.module.css` for the grid layout (CSS grid 3×3).
- **Figma CSS spec:** N/A
- **Acceptance criteria:** REQ-001 (AC-001), REQ-004 (AC-004)
- **Verify:** `npm test -- --watchAll=false --testPathPattern=Board`

---

### Step 16: src/components/Board.module.css (new) [COMP-002]

- **Purpose:** Scoped styles for Board — CSS grid 3×3 layout.
- **Dependencies:** none
- **Figma CSS spec:** N/A
- **Acceptance criteria:** REQ-001 (visual board layout)
- **Verify:** visual check only

---

### Wave 1 Tests

---

### Step 17: src/__tests__/useGameState.test.ts (new) [COMP-007]

- **Purpose:** Hook unit tests via `renderHook` from React Testing Library.
- **Dependencies:** COMP-007 (Step 14), COMP-008 (Step 1)
- **Key notes:**
  - Test initial state: board all-null, `currentPlayer='X'`, `gameStatus='playing'`, `score={X:0,O:0,draws:0}`.
  - Test `handleSquareClick`: clicking empty square updates board and flips player.
  - Test no-op on occupied square (TC-1234-10, TC-1234-11): `currentPlayer` unchanged.
  - Test no-op when `gameStatus !== 'playing'` (TC-1234-12).
  - Test win detection: after X completes top row, `gameStatus='won'`, `winner='X'`, `score.X=1`.
  - Test draw detection: after full board with no winner, `gameStatus='draw'`, `score.draws=1`.
  - Test `handleNewGame`: board reset to all-null, `currentPlayer='X'`, `gameStatus='playing'`, score unchanged.
  - Target: ≥80% coverage on `useGameState.ts`.
- **Figma CSS spec:** N/A
- **Acceptance criteria:** REQ-001–REQ-006
- **Verify:** `npm test -- --watchAll=false --testPathPattern=useGameState`

---

### Step 18: src/__tests__/Board.test.tsx (new) [COMP-002]

- **Purpose:** Integration tests for Board component.
- **Dependencies:** COMP-002 (Step 15), COMP-003 (Step 2)
- **Key notes:**
  - Renders 9 Square elements.
  - Clicking an empty square fires `onSquareClick` with correct (row, col).
  - With `disabled=true`, clicking any square does not fire `onSquareClick`.
- **Figma CSS spec:** N/A
- **Acceptance criteria:** REQ-001 (AC-001), REQ-004 (AC-004)
- **Verify:** `npm test -- --watchAll=false --testPathPattern=Board`

---

### Wave 2 — Container (depends on Wave 0 + Wave 1)

---

### Step 19: src/components/GameContainer.tsx (new) [COMP-001]

- **Purpose:** Container component. Owns all game state via `useGameState`. Renders Board, StatusDisplay, ScoreBoard, NewGameButton.
- **Dependencies:** COMP-007 (useGameState — Step 14), COMP-002 (Board — Step 15), COMP-004 (StatusDisplay — Step 4), COMP-005 (ScoreBoard — Step 6), COMP-006 (NewGameButton — Step 8)
- **Key notes:**
  - Calls `useGameState()` at the top.
  - Passes `disabled={gameStatus !== 'playing'}` to Board.
  - Does NOT duplicate any state — all state comes from the hook.
  - No `useEffect` for game logic.
  - Layout: StatusDisplay at top, Board in center, ScoreBoard below board, NewGameButton at bottom.
- **Figma CSS spec:** N/A
- **Acceptance criteria:** REQ-001–REQ-006 (all ACs — container integrates all functionality)
- **Verify:** `npm test -- --watchAll=false --testPathPattern=GameContainer`

---

### Wave 2 Tests

---

### Step 20: src/__tests__/GameContainer.test.tsx (new) [COMP-001]

- **Purpose:** Integration tests for GameContainer — exercises complete game flows through the rendered component.
- **Dependencies:** COMP-001 (Step 19) and all Wave 0/1 components
- **Key notes:**
  - Render GameContainer; verify 9 squares present, Player X turn shown, score 0-0-0.
  - Simulate complete X-wins game: verify win announcement and score X:1.
  - Click New Game after win: verify board cleared, Player X turn, score X:1 preserved (TC-1234-16, TC-1234-17).
  - Simulate draw game: verify "Draw!" shown and draws:1 (TC-1234-07, TC-1234-08).
  - Verify occupied square click is no-op (TC-1234-10): click same square twice, turn does not advance.
  - TC-1234-18: click New Game on fresh board — no errors, board still empty, score 0-0-0.
- **Figma CSS spec:** N/A
- **Acceptance criteria:** REQ-001–REQ-006 (all ACs)
- **Verify:** `npm test -- --watchAll=false --testPathPattern=GameContainer`

---

### Wave 3 — Root (depends on Wave 2)

---

### Step 21: src/App.tsx (new) [COMP-009]

- **Purpose:** Root component. Renders `GameContainer` within the app shell.
- **Dependencies:** COMP-001 (GameContainer — Step 19)
- **Key notes:**
  - Minimal — just renders `<GameContainer />` inside the app wrapper `<div>`.
  - Default export.
  - Uses `App.module.css` for any top-level layout.
- **Figma CSS spec:** N/A
- **Acceptance criteria:** all (root shell)
- **Verify:** `npm test -- --watchAll=false` (full suite)

---

### Step 22: src/App.module.css (new) [COMP-009]

- **Purpose:** App-level layout — centers the game container on screen.
- **Dependencies:** none
- **Figma CSS spec:** N/A
- **Acceptance criteria:** visual only
- **Verify:** visual check only

---

## Wave Plan

| Wave | Files | Dependencies Satisfied | Test Command |
| ---- | ----- | ---------------------- | ------------ |
| 0 | `src/utils/gameLogic.ts`, `src/components/Square.tsx`, `src/components/Square.module.css`, `src/components/StatusDisplay.tsx`, `src/components/StatusDisplay.module.css`, `src/components/ScoreBoard.tsx`, `src/components/ScoreBoard.module.css`, `src/components/NewGameButton.tsx`, `src/components/NewGameButton.module.css`, `src/__tests__/gameLogic.test.ts`, `src/__tests__/Square.test.tsx`, `src/__tests__/StatusDisplay.test.tsx`, `src/__tests__/ScoreBoard.test.tsx` | none | `npm test -- --watchAll=false` |
| 1 | `src/hooks/useGameState.ts`, `src/components/Board.tsx`, `src/components/Board.module.css`, `src/__tests__/useGameState.test.ts`, `src/__tests__/Board.test.tsx` | Wave 0 (gameLogic, Square) | `npm test -- --watchAll=false` |
| 2 | `src/components/GameContainer.tsx`, `src/__tests__/GameContainer.test.tsx` | Wave 1 (useGameState, Board, StatusDisplay, ScoreBoard, NewGameButton) | `npm test -- --watchAll=false` |
| 3 | `src/App.tsx`, `src/App.module.css` | Wave 2 (GameContainer) | `npm test -- --watchAll=false` |

## Risks

| Risk | Impact | Mitigation |
| ---- | ------ | ---------- |
| `checkDraw` fires when winner exists | Draw message shown alongside win (incorrect) | `checkDraw` must call `calculateWinner` internally and return false if winner found; add explicit unit test (TC-1234-09) |
| Game state not reset after `handleNewGame` | Score incorrectly zeroed or board not cleared | Verify `handleNewGame` resets board+player+status but leaves `score` unchanged; covered by TC-1234-16, TC-1234-17 |
| `useEffect` used for game logic | Stale state race conditions; ADR-002 violation | Win/draw detection must be computed inline in `handleSquareClick` using local variables, not derived in an effect |
| React app scaffold not initialized | No test runner or build available | Initialize `create-react-app --template typescript` or Vite+React-TS scaffold before Wave 0 |
| `currentPlayer` flipped on game-ending move | Player shows as winner's opponent after win | Only flip `currentPlayer` when `newGameStatus === 'playing'` |

## Edge Cases (from problem_spec)

| ID     | Scenario | Expected Behavior |
| ------ | -------- | ----------------- |
| EC-001 | Click occupied square | Silent no-op; turn unchanged; board unchanged (AC-004) |
| EC-002 | Board fills with no winner (last move) | `checkDraw` fires; "Draw!" shown; board locked; draws counter increments (AC-003, AC-005) |
| EC-003 | "New Game" clicked immediately on fresh board | Board stays empty; score 0-0-0; no errors; app stable (AC-006, TC-1234-18) |

## Post-Implementation Checklist

- [ ] All tests pass (no regressions from baseline)
- [ ] ≥80% coverage on `gameLogic.ts` and `useGameState.ts`
- [ ] `ph5_6_impl_manifest.md` written with all 22 files listed
- [ ] No `any` TypeScript type used
- [ ] No `useEffect` for game logic
- [ ] CSS modules used for all component styles (no inline styles)
- [ ] App renders correctly in a browser (manual smoke test)
- [ ] No PII in log statements (N/A — no logging in this app)

## Pipeline Continuation

**CRITICAL: This implementation is part of SDLC pipeline for 1234.**
After implementation completes, the pipeline MUST continue through:

- Phase 6: Simplify (`simplify`)
- Phase 7: Review (`spec-reviewer` + `test-engineer` + `security-auditor`)
- Phase 8: Verification (`sdlc-verify --ticket=1234`)
- Phase 9: Risk Assessment (`sdlc-risk --ticket=1234`)
- Phase 10: PR Creation (`create-pr`)

**DO NOT skip phases 6-10. DO NOT jump directly to PR creation.**

Resume command: `/client-master:00-sdlc-pipeline --ticket=1234 --resume`
