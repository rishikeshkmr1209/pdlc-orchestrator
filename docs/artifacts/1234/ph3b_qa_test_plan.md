## Meta
- Ticket: 1234
- Classification: Small Feature
- Phase: 3b (QA Test Generation, parallel to design-review)
- Generated at: 2026-06-04T10:00:00.000Z
- Inputs: ph1_problem_spec.md, ph2_design_spec.md, artifact-digest.md
- Platform knowledge: n/a (ensure-platform-knowledge.sh script not present; greenfield UI-only app with no backend service references — skipped per skill rule)

---

## Inputs Summary

**Acceptance Criteria covered (6):** AC-001 through AC-006.

**Components touched (all new — greenfield):**
- COMP-001 `GameContainer` — state owner
- COMP-002 `Board` — grid renderer
- COMP-003 `Square` — single cell
- COMP-004 `StatusDisplay` — game status text
- COMP-005 `ScoreBoard` — score display
- COMP-006 `NewGameButton` — reset action
- COMP-007 `useGameState` — state + actions hook
- COMP-008 `gameLogic` — pure logic functions (`calculateWinner`, `checkDraw`, `getInitialBoard`)
- COMP-009 `App` — root component

**No backend services / API endpoints** — purely client-side React app.
**No Figma link** — `figma.link` is null in pipeline state.

---

## Existing Zephyr Matches (JQL filter 28319)

> **Note:** Atlassian MCP is not configured in this environment. JQL query against filter 28319 could not be executed. All test cases are therefore marked `decision: new`. On rerun with Atlassian MCP available, this section will be populated with actual matches.

| AC | Matched test key | Match score | Decision |
|----|-----------------|-------------|----------|
| AC-001 | — (no query possible) | — | new |
| AC-002 | — (no query possible) | — | new |
| AC-003 | — (no query possible) | — | new |
| AC-004 | — (no query possible) | — | new |
| AC-005 | — (no query possible) | — | new |
| AC-006 | — (no query possible) | — | new |

---

## AC → Test Matrix

| AC-ID | Test IDs | Regression? | Decision |
|-------|----------|-------------|----------|
| AC-001 | TC-1234-01, TC-1234-02, TC-1234-03 | TC-1234-01: yes (R2), TC-1234-02: yes (R2), TC-1234-03: no | new |
| AC-002 | TC-1234-04, TC-1234-05, TC-1234-06 | TC-1234-04: yes (R2), TC-1234-05: yes (R2), TC-1234-06: no | new |
| AC-003 | TC-1234-07, TC-1234-08, TC-1234-09 | TC-1234-07: yes (R2), TC-1234-08: yes (R2), TC-1234-09: no | new |
| AC-004 | TC-1234-10, TC-1234-11, TC-1234-12 | TC-1234-10: yes (R2), TC-1234-11: yes (R2), TC-1234-12: no | new |
| AC-005 | TC-1234-13, TC-1234-14, TC-1234-15 | TC-1234-13: no, TC-1234-14: no, TC-1234-15: no | new |
| AC-006 | TC-1234-16, TC-1234-17, TC-1234-18 | TC-1234-16: no, TC-1234-17: no, TC-1234-18: no | new |

---

## Test Cases

### TC-1234-01 — Clicking an empty square places the current player's mark and passes the turn
**Type:** functional · **Priority:** P0 · **ACs:** AC-001

**Preconditions**
- The React app is rendered and in initial state (board empty, currentPlayer = 'X', gameStatus = 'playing')

**Steps**
1. Observe that `StatusDisplay` shows it is Player X's turn
2. Click any empty square (e.g., row 0, col 0)
3. Observe the square's rendered value
4. Observe the `StatusDisplay` text

**Expected**
The clicked square displays 'X'. The `StatusDisplay` now shows it is Player O's turn. No other squares have changed.

**Data:** n/a
**Regression:** yes (R2 — REQ-001 is P0; AC is critical-path)
**Decision:** new
**Automation:** skipped (qa-automation checkout absent)

---

### TC-1234-02 — Players alternate turns correctly across multiple moves
**Type:** functional · **Priority:** P0 · **ACs:** AC-001

**Preconditions**
- The app is rendered in initial state (board empty, currentPlayer = 'X', gameStatus = 'playing')

**Steps**
1. Click square (0, 0) — Player X's turn
2. Observe the board and status after the click
3. Click square (1, 1) — Player O's turn
4. Observe the board and status after the click
5. Click square (0, 1) — Player X's turn
6. Observe the board and status after the click

**Expected**
After step 1: square (0,0) = 'X', currentPlayer = 'O'.
After step 3: square (1,1) = 'O', currentPlayer = 'X'.
After step 5: square (0,1) = 'X', currentPlayer = 'O'.
Turn alternation is consistent with each move.

**Data:** n/a
**Regression:** yes (R2 — REQ-001 is P0; AC is critical-path)
**Decision:** new
**Automation:** skipped (qa-automation checkout absent)

---

### TC-1234-03 — Board renders 9 empty squares on initial load
**Type:** edge · **Priority:** P1 · **ACs:** AC-001

**Preconditions**
- The app is freshly mounted (no prior interaction)

**Steps**
1. Render the `Board` component
2. Count the number of `Square` elements rendered
3. Assert each `Square` has value = null (renders as empty)
4. Assert the `StatusDisplay` shows "Player X's turn" (or equivalent initial-turn text)

**Expected**
Exactly 9 Square elements are rendered. All 9 display no mark (empty). The turn indicator shows Player X is first.

**Data:** n/a
**Regression:** no (edge case; no existing surface — greenfield app, R1 not applicable; AC is P1 not P0 critical-path edge variant)
**Decision:** new
**Automation:** skipped (qa-automation checkout absent)

---

### TC-1234-04 — A player wins by completing a row and a win announcement is displayed
**Type:** functional · **Priority:** P0 · **ACs:** AC-002

**Preconditions**
- App is rendered in initial state
- No moves have been made

**Steps**
1. Click square (0, 0) — Player X places mark (row 0, col 0)
2. Click square (1, 0) — Player O places mark (row 1, col 0)
3. Click square (0, 1) — Player X places mark (row 0, col 1)
4. Click square (1, 1) — Player O places mark (row 1, col 1)
5. Click square (0, 2) — Player X places mark (row 0, col 2) completing top row [X, X, X]
6. Observe `StatusDisplay` text
7. Attempt to click any remaining empty square

**Expected**
After step 5: `StatusDisplay` announces "Player X wins!" (or equivalent). `gameStatus` = 'won', `winner` = 'X'. The click in step 7 has no effect — the board remains in its current state.

**Data:** n/a
**Regression:** yes (R2 — REQ-002 is P0; win detection is critical-path)
**Decision:** new
**Automation:** skipped (qa-automation checkout absent)

---

### TC-1234-05 — A player wins by completing a diagonal and the board is locked
**Type:** functional · **Priority:** P0 · **ACs:** AC-002

**Preconditions**
- App is rendered in initial state
- No moves have been made

**Steps**
1. Click square (0, 0) — X
2. Click square (0, 1) — O
3. Click square (1, 1) — X
4. Click square (0, 2) — O
5. Click square (2, 2) — X completes main diagonal [(0,0), (1,1), (2,2)]
6. Observe `StatusDisplay`
7. Click square (1, 0) (an empty square)
8. Observe the board after step 7

**Expected**
After step 5: `StatusDisplay` shows X wins. `gameStatus` = 'won'. The click in step 7 is silently ignored — board[1][0] remains null.

**Data:** n/a
**Regression:** yes (R2 — REQ-002 is P0; diagonal win detection is critical-path)
**Decision:** new
**Automation:** skipped (qa-automation checkout absent)

---

### TC-1234-06 — Win detection evaluates all 8 winning lines (column win)
**Type:** edge · **Priority:** P1 · **ACs:** AC-002

**Preconditions**
- App is rendered in initial state

**Steps**
1. Click (0, 0) — X
2. Click (0, 1) — O
3. Click (1, 0) — X
4. Click (1, 1) — O
5. Click (2, 0) — X completes left column [(0,0), (1,0), (2,0)]
6. Observe `StatusDisplay` and `gameStatus`

**Expected**
`StatusDisplay` announces Player X wins. `gameStatus` = 'won'. No further clicks are accepted. This confirms `calculateWinner` checks column win lines correctly.

**Data:** n/a
**Regression:** no (edge variant; R1 not applicable — greenfield; P1 priority variant of win detection)
**Decision:** new
**Automation:** skipped (qa-automation checkout absent)

---

### TC-1234-07 — All 9 squares filled with no winner produces a draw message
**Type:** functional · **Priority:** P0 · **ACs:** AC-003

**Preconditions**
- App is rendered in initial state

**Steps**
1. Play the following sequence of moves producing no winner:
   - Click (0,0) X, (0,1) O, (0,2) X
   - Click (1,0) O, (1,1) X, (1,2) O
   - Click (2,0) O, (2,1) X, (2,2) O
   (Final board: row0=[X,O,X], row1=[O,X,O], row2=[O,X,O] — no winning line)
2. After the 9th click, observe `StatusDisplay`
3. Attempt to click any square

**Expected**
`StatusDisplay` shows "Draw!" (or equivalent). `gameStatus` = 'draw'. The click in step 3 is silently ignored — board is locked. `checkDraw` returns true.

**Data:** n/a
**Regression:** yes (R2 — REQ-003 is P0; draw detection is critical-path)
**Decision:** new
**Automation:** skipped (qa-automation checkout absent)

---

### TC-1234-08 — Draw state locks the board and prevents further moves
**Type:** negative · **Priority:** P0 · **ACs:** AC-003

**Preconditions**
- App is in draw state (all 9 squares filled, no winner, `gameStatus` = 'draw')
- This can be reached by the sequence in TC-1234-07

**Steps**
1. Click square (0, 0) — already occupied
2. Click square (1, 0) — already occupied
3. Observe board state and currentPlayer after both clicks

**Expected**
Neither click changes board state. `currentPlayer` remains unchanged. No error is thrown. `gameStatus` remains 'draw'.

**Data:** n/a
**Regression:** yes (R2 — REQ-003 is P0; board-lock after draw is critical-path)
**Decision:** new
**Automation:** skipped (qa-automation checkout absent)

---

### TC-1234-09 — Board fills completely during a game that would have been a win — draw does not fire
**Type:** edge · **Priority:** P1 · **ACs:** AC-003

**Preconditions**
- App is in initial state

**Steps**
1. Play a sequence that results in X winning on the 7th move (not a full board):
   - Click (0,0) X, (1,0) O, (0,1) X, (1,1) O, (0,2) X (X wins, top row)
2. Observe `gameStatus` and `StatusDisplay`
3. Count filled squares (5 filled, 4 empty)

**Expected**
`gameStatus` = 'won', NOT 'draw'. `checkDraw` returns false when a winner exists even if remaining squares are empty. The "Draw!" message is NOT shown.

**Data:** n/a
**Regression:** no (edge case — verifies `checkDraw` does not fire when winner is present; greenfield app; not R2-critical-path)
**Decision:** new
**Automation:** skipped (qa-automation checkout absent)

---

### TC-1234-10 — Clicking an already-occupied square is silently ignored
**Type:** functional · **Priority:** P0 · **ACs:** AC-004

**Preconditions**
- App is rendered in initial state
- Player X has already clicked square (0, 0) — that square contains 'X'
- It is now Player O's turn

**Steps**
1. Click square (0, 0) (already occupied by X)
2. Observe square (0, 0) value
3. Observe `currentPlayer`
4. Observe all other squares

**Expected**
Square (0, 0) still displays 'X'. `currentPlayer` remains 'O' (turn did NOT advance). All other squares remain empty. No error or UI flicker occurs.

**Data:** n/a
**Regression:** yes (R2 — REQ-004 is P0; invalid-move prevention is critical-path)
**Decision:** new
**Automation:** skipped (qa-automation checkout absent)

---

### TC-1234-11 — Clicking an occupied square multiple times never changes the board
**Type:** negative · **Priority:** P0 · **ACs:** AC-004

**Preconditions**
- Square (1, 1) is occupied by 'O'
- It is Player X's turn
- `gameStatus` = 'playing'

**Steps**
1. Click square (1, 1) three times rapidly (or in sequence)
2. Observe square (1, 1) value after each click
3. Observe `currentPlayer` after all three clicks
4. Observe `gameStatus`

**Expected**
Square (1, 1) retains 'O' after all three clicks. `currentPlayer` remains 'X'. `gameStatus` remains 'playing'. No score change occurs.

**Data:** n/a
**Regression:** yes (R2 — REQ-004 is P0; idempotent invalid-move prevention)
**Decision:** new
**Automation:** skipped (qa-automation checkout absent)

---

### TC-1234-12 — Clicking an occupied square after game ends is also a no-op
**Type:** edge · **Priority:** P1 · **ACs:** AC-004

**Preconditions**
- X has won the game (`gameStatus` = 'won')
- Square (0, 0) is occupied by 'X'

**Steps**
1. Click square (0, 0)
2. Observe board state, `gameStatus`, `winner`, `currentPlayer`

**Expected**
No state changes. `handleSquareClick` returns early because `gameStatus !== 'playing'` (the first guard fires before the occupied-square guard). Board is unchanged.

**Data:** n/a
**Regression:** no (edge variant — guard ordering; not R2 critical-path; P1 priority)
**Decision:** new
**Automation:** skipped (qa-automation checkout absent)

---

### TC-1234-13 — Score tally increments for the winner when a game ends in a win
**Type:** functional · **Priority:** P1 · **ACs:** AC-005

**Preconditions**
- App is rendered in initial state
- Score is { X: 0, O: 0, draws: 0 }

**Steps**
1. Play a game where Player X wins (use top-row win: (0,0) X, (1,0) O, (0,1) X, (1,1) O, (0,2) X)
2. Observe `ScoreBoard` immediately after the winning move

**Expected**
`ScoreBoard` shows X: 1, O: 0, draws: 0. Score updated synchronously on the winning move.

**Data:** n/a
**Regression:** no (R1 not applicable — greenfield; REQ-005 is P1, not P0 critical-path for R2)
**Decision:** new
**Automation:** skipped (qa-automation checkout absent)

---

### TC-1234-14 — Draw counter increments when a game ends in a draw
**Type:** negative · **Priority:** P1 · **ACs:** AC-005

**Preconditions**
- App is rendered in initial state
- Score is { X: 0, O: 0, draws: 0 }

**Steps**
1. Play the draw sequence from TC-1234-07 (all 9 squares, no winner)
2. Observe `ScoreBoard` after the 9th move

**Expected**
`ScoreBoard` shows X: 0, O: 0, draws: 1. Score updates synchronously on the last move.

**Data:** n/a
**Regression:** no (R1 not applicable; REQ-005 is P1)
**Decision:** new
**Automation:** skipped (qa-automation checkout absent)

---

### TC-1234-15 — Score accumulates correctly across multiple consecutive games in a session
**Type:** edge · **Priority:** P1 · **ACs:** AC-005

**Preconditions**
- App is rendered in initial state
- Score starts at { X: 0, O: 0, draws: 0 }

**Steps**
1. Play Game 1: X wins (top-row win)
2. Click "New Game"
3. Play Game 2: O wins (play moves: (0,0) X, (1,0) O, (0,1) X, (1,1) O, (2,2) X, (2,0) O completing left column)
4. Click "New Game"
5. Play Game 3: draw (use draw sequence from TC-1234-07)
6. Observe `ScoreBoard` after game 3

**Expected**
`ScoreBoard` shows X: 1, O: 1, draws: 1 after all three games. Score is additive and never resets between games within the same session.

**Data:** n/a
**Regression:** no (R1 not applicable; accumulation edge case; P1 priority)
**Decision:** new
**Automation:** skipped (qa-automation checkout absent)

---

### TC-1234-16 — New Game button resets the board and turn without clearing the score
**Type:** functional · **Priority:** P1 · **ACs:** AC-006

**Preconditions**
- A complete game has just ended (X wins, score = { X: 1, O: 0, draws: 0 })
- `gameStatus` = 'won'

**Steps**
1. Observe the current score on `ScoreBoard`
2. Click the "New Game" button
3. Observe `Board` — all 9 squares
4. Observe `StatusDisplay`
5. Observe `ScoreBoard`

**Expected**
All 9 squares are empty. `StatusDisplay` shows it is Player X's turn. `ScoreBoard` still shows X: 1, O: 0, draws: 0 (score unchanged). `gameStatus` = 'playing'.

**Data:** n/a
**Regression:** no (R1 not applicable — greenfield; REQ-006 is P1)
**Decision:** new
**Automation:** skipped (qa-automation checkout absent)

---

### TC-1234-17 — New Game button works correctly mid-game (before any game ends)
**Type:** negative · **Priority:** P1 · **ACs:** AC-006

**Preconditions**
- A game is in progress: 3 moves made (X placed at (0,0), O at (1,1), X at (0,1))
- Score is { X: 0, O: 0, draws: 0 }

**Steps**
1. Click the "New Game" button while game is still in progress
2. Observe all 9 squares
3. Observe `StatusDisplay`
4. Observe `ScoreBoard`
5. Observe `currentPlayer`

**Expected**
All 9 squares are cleared and empty. `currentPlayer` = 'X'. `gameStatus` = 'playing'. Score remains { X: 0, O: 0, draws: 0 } (no partial game recorded). `StatusDisplay` shows Player X's turn.

**Data:** n/a
**Regression:** no (R1 not applicable; P1 priority; mid-game reset is a P1 scenario)
**Decision:** new
**Automation:** skipped (qa-automation checkout absent)

---

### TC-1234-18 — New Game clicked immediately after page load (no moves yet) has no adverse effect
**Type:** edge · **Priority:** P1 · **ACs:** AC-006

**Preconditions**
- App just mounted, no moves made yet
- Score is { X: 0, O: 0, draws: 0 }, board is all-null, `currentPlayer` = 'X'

**Steps**
1. Click the "New Game" button without having made any moves
2. Observe board state
3. Observe `StatusDisplay`
4. Observe `ScoreBoard`
5. Confirm no JavaScript errors in the console

**Expected**
Board remains empty (9 null squares). `currentPlayer` = 'X'. Score remains { X: 0, O: 0, draws: 0 }. `StatusDisplay` shows it is Player X's turn. No console errors thrown. Application is stable and ready for play. (Corresponds to EC-003.)

**Data:** n/a
**Regression:** no (EC-003 edge case; R1 not applicable; P1 priority)
**Decision:** new
**Automation:** skipped (qa-automation checkout absent)

---

## Regression Subset

| Test ID | Jira Key | Rule Fired | Repository Location |
|---------|----------|------------|---------------------|
| TC-1234-01 | pending Jira creation | R2 (REQ-001 is P0 — alternating turns is critical-path) | new spec — qa-automation absent |
| TC-1234-02 | pending Jira creation | R2 (REQ-001 is P0 — turn alternation is critical-path) | new spec — qa-automation absent |
| TC-1234-04 | pending Jira creation | R2 (REQ-002 is P0 — win detection is critical-path) | new spec — qa-automation absent |
| TC-1234-05 | pending Jira creation | R2 (REQ-002 is P0 — diagonal win detection is critical-path) | new spec — qa-automation absent |
| TC-1234-07 | pending Jira creation | R2 (REQ-003 is P0 — draw detection is critical-path) | new spec — qa-automation absent |
| TC-1234-08 | pending Jira creation | R2 (REQ-003 is P0 — board-lock after draw is critical-path) | new spec — qa-automation absent |
| TC-1234-10 | pending Jira creation | R2 (REQ-004 is P0 — occupied square prevention is critical-path) | new spec — qa-automation absent |
| TC-1234-11 | pending Jira creation | R2 (REQ-004 is P0 — idempotent invalid-move prevention) | new spec — qa-automation absent |

> **Stream:** This story has no backend service components. All components are React UI. The `qa-automation` stream would be `shared` (no brand-specific route, no matching service in the automation cookbook table). `e2e/tests/shared/` or `tests/shared/` would be the target once the checkout is available.

---

## Jira Issues Created / Linked

> **Note:** Atlassian MCP is not configured in this environment. No Jira Test issues could be created in this run. The `qa_jira_issues.json` state file records all 18 test cases with `action: "pending-creation"` for the next run with MCP access. No duplicate issues will be created on rerun (dedup keys are recorded below).

| Jira Key | Action | Parent Link | URL |
|----------|--------|-------------|-----|
| pending | pending-creation (TC-1234-01) | 1234 | — |
| pending | pending-creation (TC-1234-02) | 1234 | — |
| pending | pending-creation (TC-1234-03) | 1234 | — |
| pending | pending-creation (TC-1234-04) | 1234 | — |
| pending | pending-creation (TC-1234-05) | 1234 | — |
| pending | pending-creation (TC-1234-06) | 1234 | — |
| pending | pending-creation (TC-1234-07) | 1234 | — |
| pending | pending-creation (TC-1234-08) | 1234 | — |
| pending | pending-creation (TC-1234-09) | 1234 | — |
| pending | pending-creation (TC-1234-10) | 1234 | — |
| pending | pending-creation (TC-1234-11) | 1234 | — |
| pending | pending-creation (TC-1234-12) | 1234 | — |
| pending | pending-creation (TC-1234-13) | 1234 | — |
| pending | pending-creation (TC-1234-14) | 1234 | — |
| pending | pending-creation (TC-1234-15) | 1234 | — |
| pending | pending-creation (TC-1234-16) | 1234 | — |
| pending | pending-creation (TC-1234-17) | 1234 | — |
| pending | pending-creation (TC-1234-18) | 1234 | — |

---

## Automation PR

- Branch: feature/shared/1234/qa-auto-tests
- PR URL: not opened — qa-automation checkout absent at workspace root
- Files changed: 0 (skipped)
- Lint status: skipped

> Step 8 was skipped because `qa-automation` is not checked out at `$WORKSPACE_ROOT/qa-automation`. Steps 1–7 (test plan and Jira issue staging) are the primary deliverable. On next rerun with `qa-automation` present, the skill will create `tests/shared/game/<1234>-tic-tac-toe.spec.ts` targeting the 8 regression-classified test cases.

---

## Sign-Off

- Status: partial-(jira-only)
- Notes:
  1. **Atlassian MCP not configured** — Jira Test issues could not be created. All 18 test case records are staged in `qa_jira_issues.json` with `action: "pending-creation"`. Rerun with Atlassian MCP credentials configured to complete Steps 3, 5, and 9.
  2. **Zephyr dedup query skipped** — JQL filter 28319 not queried. On rerun, the query will run and any existing matching tests will be flagged for update rather than duplication.
  3. **qa-automation checkout absent** — Step 8 skipped as designed. The 8 regression tests are ready for automation once the checkout is present.
  4. **Platform knowledge unavailable** — `ensure-platform-knowledge.sh` not found at `claude-master-plugin/scripts/`. This is acceptable: the story has no backend service references and no service-specific knowledge was needed.
  5. **Link-type name unverified** — Jira link type "Tests" / "is tested by" used per cookbook §5b. Verify the exact name in the target Jira instance with `getIssueLinkTypes` on first MCP run.
