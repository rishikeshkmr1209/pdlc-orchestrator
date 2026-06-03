---
name: 08-sdlc-verify
description: >
  Use when user says "verify implementation", "run verification",
  "check implementation", or when sdlc-pipeline invokes after review phase.
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
---

# SDLC Verify Skill

## Prime Directive

> **"Verify, don't validate. Find what's missing, not just what's wrong."**

Validation confirms that what exists is correct. Verification confirms that everything
required actually exists and functions as specified. Your job is the latter. You are
the final gate before a PR is created. Be thorough, be systematic, be fair.

---

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--ticket=TICKET-ID` | Yes | Jira ticket ID (e.g., `TICKET-1234`, `TICKET-567`). Used to locate checkpoint artifacts and tag the report. |

Usage examples:
- `/verify --ticket=TICKET-1234`
- `verify implementation --ticket=TICKET-567`
- `check implementation --ticket=TICKET-1234`
- `run verification --ticket=TICKET-1234`

---

## Prerequisites

Before verification can proceed, the following must exist:

1. **Artifacts directory**: `docs/artifacts/<TICKET-ID>/`
2. **ph1_problem_spec.md**: Requirements and acceptance criteria from the requirements phase
3. **ph2_design_spec.md**: Technical design from the architecture phase
4. **ph5_6_impl_manifest.md**: Implementation manifest from the implementation phase

If any are missing, stop and report which artifacts are absent. Do not proceed with
partial inputs — the verification report would be incomplete and misleading.

---

> **Before reading any files:** Read `skills/_shared/parallel-reads-rule.md` and follow it for all file reads in this phase.

## Process Overview

```
1. Load checkpoint artifacts
2. Aggregate subagent review results (if available)
2.5. Verify component wiring (existence, substance, imports)
2.6. Design fidelity check (Figma token vs implementation CSS — only when figma.fetched == true)
3. Build requirement coverage matrix
4. Run test analysis
5. Check edge case coverage
6. Generate prioritized recommendations
7. Calculate overall score
8. Apply quality gates
9. Save ph8_verification_report.md
```

---

## Step 1: Load Checkpoint Artifacts

Extract only the required sections from each artifact using the extraction script:

```bash
python3 claude-master-plugin/scripts/extract-sections.py \
  docs/artifacts/<TICKET-ID>/ph1_problem_spec.md \
  "Requirements" "Acceptance Criteria" "Constraints" "Edge Cases"

python3 claude-master-plugin/scripts/extract-sections.py \
  docs/artifacts/<TICKET-ID>/ph2_design_spec.md \
  "Meta" "Architecture" "API Contracts" "Data Models"

python3 claude-master-plugin/scripts/extract-sections.py \
  docs/artifacts/<TICKET-ID>/ph3_design_review.md \
  "Summary" "Sign-Off"

# ph5_6_impl_manifest.md — full file (wiring verification needs everything)
python3 claude-master-plugin/scripts/extract-sections.py \
  docs/artifacts/<TICKET-ID>/ph5_6_impl_manifest.md "*"
```

(See `claude-master-plugin/config/phase-artifact-map.json → Ph8_verification`.)

CRITICAL: The `## Meta` section of `ph2_design_spec.md` contains `codebase_location` — required for wiring verification. If missing, STOP and ask the user for the codebase path.

Also read `docs/artifacts/<TICKET-ID>/.state/artifact-digest.md` in full for overview.
(See `claude-master-plugin/config/phase-artifact-map.json → Ph8_verification`.)
Optional inputs (from Phase 7 parallel agents, if present):
- `docs/artifacts/<TICKET-ID>/test_report.json`
- `docs/artifacts/<TICKET-ID>/security_audit.json`

Extract from the **Requirements** and **Acceptance Criteria** sections of `ph1_problem_spec.md`:
- All `REQ-###` requirements with their priority (P0, P1, P2)
- All `AC-###` acceptance criteria under each requirement
- All `EC-###` edge cases
- Constraints and non-functional requirements

Extract from **ph2_design_spec.md**:
- Component architecture and file structure
- API contracts and data models
- State management approach
- `meta.codebase_location` — the root path of the implementation

Extract from **ph5_6_impl_manifest.md**:
- List of files created and modified
- Entry points and exports
- Dependencies added or changed
- Test files created

**Preflight check**: `design_spec` must contain a `## Meta` section with `codebase_location`.
If missing or null, stop and ask the user for the codebase path before proceeding.

---

## Step 2: Aggregate Subagent Review Results

If the SDLC pipeline ran parallel subagent reviews, their outputs may be available
in the checkpoint directory. Aggregate findings from each source:

### From test-engineer (test_report.json)
- Test execution results (pass/fail/skip counts)
- Coverage percentages
- Failed test details
- Merge into `test_results`

### From security-auditor (security_audit.json)
- OWASP findings
- PII exposure risks
- Authentication/authorization gaps
- Merge into `security_findings` with source attribution

### Deduplication Rules
When merging findings from multiple sources:
- Same file + same line + same category = deduplicate, keep the higher severity
- Same file + different line + same category = keep both (different instances)
- Different file + same pattern = keep both but note the pattern
- Add `source` field to each finding indicating origin (e.g., `"spec-reviewer"`, `"security-auditor"`, `"test-engineer"`, `"verifier"`)

If no subagent results are available, perform all analyses directly. The verifier
must be self-sufficient and able to produce a complete report independently.

---

## Step 2.5: Wiring Verification (REQ-004)

After aggregating subagent results (or independently if no subagents ran), perform a
3-level verification of every component listed in `ph2_design_spec.md`:

### Level 1: Existence Check

For each component in `design_spec.architecture.components[]`:
- Use Glob to verify the file exists at the exact `file_path` specified.
- Status: `exists` | `not_found`

### Level 2: Substantive Check

For each file that exists:
- Read the file. Verify it contains real implementation, not just stubs.
- A file is a **stub** if: it only contains empty class/function bodies, placeholder
  comments like `// TODO`, `// implement`, `throw new Error('not implemented')`,
  or has fewer than 5 non-comment, non-blank lines of code.
- Status: `substantive` | `stub` | `empty`

### Level 3: Wiring Check

For each substantive file:
- Search the codebase (excluding the file itself and test files) for imports of this
  component. Use Grep to find `import.*from.*<file_path_stem>` patterns.
- Check that the component is actually called/used, not just imported.
- For entry points (components with no dependents in the dependency graph), verify
  they are referenced in a configuration file, route definition, hook registration,
  or equivalent integration point.
- Status: `wired` | `imported_not_used` | `not_imported`

### Wiring Report

Produce a wiring summary as part of the verification report:

```json
{
  "wiring_verification": {
    "total_components": N,
    "fully_wired": N,
    "exists_but_not_wired": N,
    "stubs": N,
    "missing": N,
    "details": [
      {
        "component_id": "COMP-001",
        "file_path": "src/foo.ts",
        "existence": "exists",
        "substantive": "substantive",
        "wiring": "wired",
        "imported_by": ["src/bar.ts:3", "src/baz.ts:7"]
      }
    ]
  }
}
```

### Wiring Score Impact

Wiring findings deduct from the Requirement Coverage dimension (60 points max):

| Finding | Deduction | Blocking? |
|---------|-----------|-----------|
| Component `not_found` | -3 per component | Yes (if P0 requirement) |
| Component is `stub` | -2 per component | Yes (if P0 requirement) |
| Component `imported_not_used` | -1 per component | No |
| Component `not_imported` | -2 per component | Conditional (if entry point) |
| Circular import chain | 0 (warning only) | No |

These deductions reduce the Requirement Coverage score. The score floor remains 0.

---

## Step 2.6: Design Fidelity Check (runs only when `figma.fetched == true`)

**Trigger check:**
```bash
python3 -c "
import json
state = json.load(open('docs/artifacts/<TICKET-ID>/.state/pipeline_state_<ticket>.json'))
fetched = (state.get('figma') or {}).get('fetched') is True
print('run' if fetched else 'skip')
"
```
If output is `skip`: skip this step and proceed to Step 3.

If output is `run`:

### 2.6a. Load Design Tokens

Read the `## Design Tokens` section from `docs/artifacts/<TICKET-ID>/ph1_problem_spec.md`.
Extract all specified values into a structured token map:
```
token_map = {
  "border_radius": [{"node": <name>, "value": "<Npx>"}],
  "spacing":       [{"node": <name>, "padding": ..., "gap": ...}],
  "colors":        [{"node": <name>, "hex": "#rrggbb"}],
  "typography":    [{"node": <name>, "fontSize": "Npx", "fontWeight": N, ...}],
  "borders":       [{"node": <name>, "width": "Npx", "color": "#rrggbb"}],
  "shadows":       [{"node": <name>, "css": "<box-shadow value>"}],
}
```
If the `## Design Tokens` section is empty or absent: log `⚠️ No design tokens found in spec — skipping design fidelity check.` and proceed to Step 3.

### 2.6b. Locate CSS Files for New Components

Read `docs/artifacts/<TICKET-ID>/ph5_6_impl_manifest.md → ## Files Created` and `## Files Modified`.
Filter to CSS files: `*.module.css`, `*.css`, `*.scss`. Also include TypeScript files that contain inline styles (`styled-components`, `style={{...}}`).

**Component-to-CSS matching algorithm:**

For each named component in `## Design Tokens`, locate its CSS file using this ordered strategy (stop at first match):

1. **Exact name match** — find a manifest path whose filename stem matches the component name exactly (case-insensitive):
   - `PausedDeliveryBanner` → `PausedDeliveryBanner.module.css`
2. **Kebab-case match** — convert `PascalCase` → `kebab-case` and search manifest paths:
   ```python
   import re
   def to_kebab(name): return re.sub(r'(?<!^)(?=[A-Z])', '-', name).lower()
   # PausedDeliveryBanner → paused-delivery-banner
   # Search for: paused-delivery-banner.module.css, paused-delivery-banner.css, etc.
   ```
3. **Directory match** — if a manifest entry is a directory path containing the component name, look for any `*.module.css`, `styles.css`, or `index.css` inside it.
4. **Inline styles fallback** — search `.tsx` manifest files for `style={{ ... }}` blocks or `styled-components` template literals referencing the component name.

If no CSS file is found after all four strategies: record `no_css_found` and add a finding — the component may rely on global styles or the Figma spec was not implemented.

For each located CSS file, read its full content.

### 2.6c. Check Each Component Spec Against Implementation

The `## Design Tokens` section contains per-component CSS specs. For EACH named component:

1. Locate the component's CSS file using the algorithm in Step 2.6b.
2. Read the CSS file.

**Known Conflicts pre-check (run before any property comparison):**

Read `ph5_6_impl_manifest.md → ## Known Conflicts` (if the section exists). This section documents CSS variable substitutions and intentional deviations that are confirmed correct matches. Build a lookup table:

```
known_matches = {
  (component_name, css_property): confirmed_match_note
}
# e.g. ("PausedDeliveryBanner", "background-color"): "var(--color-surface) = #f5f5f5 ✓"
```

For each entry in `## Known Conflicts`, parse: component name, CSS property, Figma value, CSS variable/override, and resolution note. Example table row:

```
| PausedDeliveryBanner | background-color | #f5f5f5 | var(--color-surface) | Resolves to #f5f5f5 ✓ |
```

When checking a property that appears in `known_matches`: mark it as `match` with note `via var(--name) = <resolved value>`. **Do NOT flag as deviation.** Skip the grep comparison for this property.

3. Check every CSS property listed in the Figma spec against what's in the file — skipping any properties already resolved as matches by the Known Conflicts table.

**Property check table:**

| CSS property | How to check | Blocking? |
|-------------|-------------|-----------|
| `border-radius` | Grep for `border-radius:` — compare value exactly. `4px` ≠ `8px` ≠ `0px` (square). | Yes (P0 component) |
| `padding` | Grep for `padding` variants — verify all four values match Figma. Extra padding = wrong spacing. | Yes |
| `gap` | Grep for `gap:` — verify itemSpacing matches. Missing gap = children collapse. | Yes |
| `display: flex` | Grep for `display: flex` — if Figma has layoutMode HORIZONTAL/VERTICAL, this is required. | Yes |
| `flex-direction` | Grep for `flex-direction:` — row/column must match Figma layoutMode. | Yes |
| `justify-content` | Grep for `justify-content:` — must match Figma primaryAxisAlignItems. | Yes |
| `align-items` | Grep for `align-items:` — must match Figma counterAxisAlignItems. | Yes |
| `width` / `height` | Check for fixed dimensions when Figma spec is FIXED sizing. Check for `fit-content`/`100%` for HUG/FILL. | Yes (FIXED) |
| `background-color` | Grep for background color — compare hex/rgba. CSS variable: resolve and compare. | Yes |
| `background` (gradient) | Grep for `background: linear-gradient` or `radial-gradient` — compare stop colors and direction. | Yes |
| `color` (text) | Grep for `color:` on text elements — compare against Figma text fill. | Yes |
| `overflow: hidden` | Grep for `overflow: hidden` — must be present when Figma `clipsContent: true`. Missing = content overflow bug. | Yes |
| `font-size` | Grep for `font-size:` — compare value. | Yes |
| `font-weight` | Grep for `font-weight:` — compare value. | Yes |
| `font-family` | Grep for `font-family:` — compare family name. | No |
| `line-height` | Grep for `line-height:` — compare value (±1px tolerance). | No |
| `letter-spacing` | Grep for `letter-spacing:` — compare value. | No |
| `text-align` | Grep for `text-align:` — must be present when Figma specifies non-LEFT alignment. | No |
| `text-transform` | Grep for `text-transform:` — must match textCase from Figma. | No |
| `text-decoration` | Grep for `text-decoration:` — underline/line-through when specified. | No |
| `border` | Grep for `border:` — compare width, color. | Yes |
| `border-radius` (per-corner) | When Figma has mixed radii, check all four corner values. | Yes |
| `box-shadow` | Grep for `box-shadow:` — compare offset, blur, spread, color. Flag if completely absent. | Yes (P0) |
| `box-shadow: inset` | Grep for `inset` in box-shadow — required for Figma INNER_SHADOW. | Yes |
| `filter: blur` | Grep for `filter: blur` — required for Figma LAYER_BLUR. | No |
| `backdrop-filter` | Grep for `backdrop-filter: blur` — required for BACKGROUND_BLUR. | No |
| `opacity` | Grep for `opacity:` — must match when Figma opacity < 1.0. | No |
| `mix-blend-mode` | Grep for `mix-blend-mode:` — required for non-NORMAL blend modes. | No |
| `transform: rotate` | Grep for `transform: rotate` — required when Figma rotation != 0. | No |
| `position: absolute` | Grep for `position: absolute` — required for ABSOLUTE-positioned Figma nodes. | Yes (layout) |
| `flex-wrap` | Grep for `flex-wrap: wrap` — required when Figma layoutWrap = WRAP. | No |

**Tolerance rules:**
- Values within ±1px: `match` (rounding acceptable for px values)
- Different unit but numerically equivalent (e.g., `0.5rem` vs `8px` at 16px base): `match`
- `border-radius: 0` and no `border-radius` property at all: both are `match` for `0px` Figma radius
- Any other mismatch: `deviation`
- Property in Figma spec but absent from all checked CSS files: `missing`

**CSS variable resolution — concrete algorithm:**

When a CSS property value is `var(--some-variable)`, resolve it before comparing:

```bash
# Step 1: Find the variable definition across CSS/SCSS/token files
VAR_NAME="--color-primary"   # extracted from the var() call
grep -r "$VAR_NAME\s*:" <codebase_root> \
  --include="*.css" --include="*.scss" --include="*.ts" \
  --exclude-dir=node_modules \
  | grep -v "var($VAR_NAME)"   # exclude uses, keep definitions
```

```bash
# Step 2: Extract the resolved value (first match)
# Example output: "src/styles/tokens.css:  --color-primary: #ff6b00;"
# Resolved value: #ff6b00
```

```bash
# Step 3: Compare resolved value to Figma spec value
# If resolved value matches Figma hex within tolerance → 'match'
# If no definition found → treat as 'missing' (variable undefined)
# If resolved value differs → 'deviation'
```

Common variable file locations to search:
- `src/styles/tokens.css`, `src/styles/variables.css`, `src/styles/theme.css`
- `src/tokens/*.ts` (design token JS/TS files)
- `:root { }` blocks in any CSS file
- `packages/@your-org/*/src/styles/` (shared design system)

If the variable is found and resolves correctly: mark as `match` and note `via var(--name)` in the report.
If the variable cannot be found anywhere in the codebase: mark as `missing` — an undefined CSS variable silently falls back to the browser default, which is almost certainly wrong.

### 2.6d. Produce Design Fidelity Report

```json
{
  "design_fidelity": {
    "tokens_checked": N,
    "matched": N,
    "deviations": N,
    "missing": N,
    "details": [
      {
        "token_category": "border_radius",
        "figma_node": "<node name>",
        "figma_value": "<Npx>",
        "css_file": "src/components/foo/foo.module.css",
        "css_value": "<found value or null>",
        "status": "match | deviation | missing",
        "deviation_note": "<optional: what differs>"
      }
    ]
  }
}
```

### 2.6e. Design Fidelity Score Impact

Design fidelity deducts from the Requirement Coverage dimension.
Properties are grouped by severity for scoring:

**Critical (blocking — wrong value causes visible layout/style break):**
`border-radius`, `padding`, `gap`, `display`, `flex-direction`, `justify-content`,
`align-items`, `width` (FIXED), `background-color`, `color`, `overflow`, `border`,
`box-shadow`, `position`

**Standard (non-blocking but flagged):**
`font-size`, `font-weight`, `line-height`, `text-align`, `text-transform`,
`background` (gradient), `box-shadow: inset`, `flex-wrap`, `opacity`

**Advisory (info-level):**
`font-family`, `letter-spacing`, `text-decoration`, `filter`, `backdrop-filter`,
`mix-blend-mode`, `transform`

| Finding | Deduction | Blocking? |
|---------|-----------|-----------|
| `deviation` on Critical property | -3 per property per component | Yes |
| `missing` Critical property | -4 per property per component | Yes |
| `deviation` on Standard property | -1 per property per component | No |
| `missing` Standard property | -2 per property per component | No |
| `deviation` or `missing` on Advisory | 0 (info only) | No |
| All properties `match` | 0 | — |

The deduction floor is 0. Maximum deduction is 20 points from the Requirement Coverage dimension.

**Automatic failure trigger:** If more than 3 Critical properties are `missing` across all new components, force status = `failed` regardless of numeric score — the implementation did not use the Figma spec at all.

---

## Step 3: Build Requirement Coverage Matrix

For each `REQ-###` in `ph1_problem_spec.md`:

### 3a. Map Requirements to Implementation Files

Search the codebase at `design_spec.meta.codebase_location` for files that implement
each requirement:

```
For REQ-001:
  - Search for identifiers, component names, and patterns from design_spec
  - Trace data flow from entry points to implementation
  - Map: REQ-001 -> [file1.ts, file2.ts, component.tsx]
```

### 3b. Map Acceptance Criteria to Test Cases

For each `AC-###` under the requirement:

```
For AC-001:
  - Search test files for describe/it blocks referencing AC-001 or its description
  - Check if test assertions match the acceptance criteria
  - Map: AC-001 -> [test1.test.ts:L42, test2.test.ts:L18]
```

### 3c. Determine Coverage Status

**Per Acceptance Criterion:**
- `passed` — At least one test exists AND passes AND meaningfully validates the criterion
- `failed` — Test exists but fails or does not match the criterion
- `skipped` — Test exists but is skipped (`.skip`, `xit`, `xdescribe`)
- `not_implemented` — No test exists for this criterion

**Per Requirement:**
- `fully_covered` — All ACs are `passed`
- `partially_covered` — At least one AC is `passed`, but not all
- `not_covered` — No ACs are `passed`
- `not_testable` — Requirement is architectural or procedural (e.g., "use Redis for caching")

### 3d. Output Format

For the JSON structure of each requirement coverage entry, see `appendix/examples.md`.

---

## Step 4: Run Test Analysis

### 4a. Discover Test Files

Search for test files in the implementation:
- Pattern: `**/*.test.{ts,tsx,js,jsx}`, `**/*.spec.{ts,tsx,js,jsx}`
- Also check `__tests__/` directories
- Cross-reference with `ph5_6_impl_manifest.md` test files

### 4b. Execute Tests (if possible)

Attempt to run the test suite:
```bash
# Try project-specific test commands in order
npx jest --json --outputFile=docs/artifacts/<TICKET>/.state/test-output.json 2>&1
# OR
yarn test --json 2>&1
# OR
npm test -- --json 2>&1
```

If tests cannot be executed (missing dependencies, environment issues), perform
static analysis of test files instead and note `"execution": "static_analysis_only"`.

### 4c. Aggregate Test Results

Structure results by test type (unit, integration, e2e) with: total, passed, failed, skipped, coverage, duration_ms, and failures array. For the full JSON structure, see `appendix/examples.md`.

### 4d. Cross-Reference Failures with Requirements

For each test failure, determine:
- Which `REQ-###` / `AC-###` it relates to
- Whether the failure is a test bug or an implementation bug
- Severity impact on the overall verification

---

## Step 5: Check Edge Case Coverage

For each `EC-###` in `ph1_problem_spec.md`:

### Search Strategy

1. Search test files for the edge case ID (e.g., `EC-001`)
2. Search test descriptions for keywords matching the edge case description
3. Check implementation code for explicit handling of the edge case

### Status Determination

- `tested` — A test exists that explicitly exercises this edge case AND passes
- `not_tested` — No test covers this edge case
- `failed` — A test exists but fails for this edge case

### Output Format

Each entry has: `edge_case_id`, `status` (tested/not_tested/failed), `test_id`, `notes`. For full structure, see `appendix/examples.md`.

---

## Step 6: Generate Recommendations

Produce a prioritized list of actions. Each recommendation must be actionable,
specific, and traceable to a finding or gap.

### Priority Levels

| Priority | Meaning | Blocking? |
|----------|---------|-----------|
| 1 | Must fix before PR — security critical or requirement not met | Yes |
| 2 | Must fix before PR — high-severity quality or failing tests | Yes |
| 3 | Should fix before PR — medium issues, missing tests | No (but recommended) |
| 4 | Should fix soon — low-severity improvements | No |
| 5 | Nice to have — info-level suggestions | No |

### Recommendation Structure

Each recommendation has: `priority` (1-5), `action`, `rationale`, `blocking`, `category`. For full structure, see `appendix/examples.md`.

### Category Values

- `coverage` — Addresses a requirement or edge case gap
- `wiring` — Addresses a component wiring issue
- `performance` — Addresses a performance concern
- `design_fidelity` — Addresses a Figma design token mismatch or missing CSS value

### Ordering Rules

1. All `blocking: true` recommendations come first
2. Within blocking, sort by priority (1 before 2)
3. Within same priority, coverage before wiring before performance
4. Non-blocking recommendations follow, sorted by priority

---

## Step 7: Calculate Overall Score

The verification score is a weighted composite of two dimensions:

### Scoring Formula

```
Total Score = Requirement Coverage (60) + Test Pass Rate (40)
```

- **Requirement Coverage**: `(passed_acs / total_acs) * 60`. If 0 ACs, award 60.
- **Test Pass Rate**: `(passed_tests / total_tests) * 40`. If 0 tests, award 0.

Score = sum of both dimensions, clamped to [0, 100]. Round each dimension to nearest integer.

For the full scoring formulas with examples, see `appendix/scoring-reference.md`.

---

## Step 8: Apply Quality Gates

Quality gates are hard requirements that override the numeric score. Even if the
score is high, failing a quality gate forces a lower status.

### Gate 1: P0 Requirement Coverage

Every requirement with priority `P0` in `ph1_problem_spec.md` must have at least
one acceptance criterion with status `passed`.

**Failure**: Any P0 requirement with zero passed ACs -> `failed`

### Gate 2: Test Pass Rate >= 80%

The overall test pass rate (across unit + integration + e2e) must be at least 80%.

**Failure**: Pass rate < 80% -> `failed` (or `passed_with_warnings` if >= 60%)

### Gate 3: Edge Case Coverage

All edge cases from `ph1_problem_spec.md` must have status `tested` or `not_tested`
with documented justification. No `failed` edge cases are acceptable.

**Failure**: Any edge case with status `failed` -> `passed_with_warnings` at best

### Gate 4: Design Fidelity (only when `figma.fetched == true`)

When a Figma link was fetched and design tokens are available, CSS values for NEW
components must match Figma specifications within the defined tolerance rules.

**Failure conditions (apply in order, first match wins):**
- More than 3 Critical properties `missing` across all new components → `failed` (implementation ignored Figma spec)
- Any `missing` Critical property (`border-radius`, `padding`, `display`, `overflow`, `background-color`, `border`) on any new component → `passed_with_warnings`
- More than 2 Critical property `deviation` findings → `passed_with_warnings`
- Only Standard/Advisory deviations → `passed` (score deduction applied but status not downgraded)

**Gate 4 adds `design_fidelity` to the recommendation category list.** Each deviation
or missing token produces a recommendation with priority 2 (deviation on P0) or 3 (other).

### Status Determination

Apply in order (first match wins):

```
1. IF any P0 requirement has zero passed ACs              -> "failed"
2. IF score < 50                                          -> "failed"
3. IF test pass rate < 60%                                -> "failed"
4. IF score >= 70 AND no blocking recommendations
   AND test pass rate >= 80%                              -> "passed"
5. IF score >= 50                                         -> "passed_with_warnings"
6. ELSE                                                   -> "failed"
```

---

## Step 9: Save Verification Report

Write the complete report to `docs/artifacts/<TICKET-ID>/ph8_verification_report.md`.

### LLM Self-Validation: Required Sections

Before saving ph8_verification_report.md, verify these sections exist and are non-empty:
- [ ] `## Meta` -- ticket ID, date, verifier
- [ ] `## Summary` -- overall verification score and status
- [ ] `## Requirement Coverage` -- each requirement mapped to verification evidence
- [ ] `## Test Results` -- test execution results and coverage
- [ ] `## Recommendations` -- top recommendations for improvement

### Post-Save Verification

After writing the file:
1. Re-read the file to confirm it was written correctly
2. Confirm all required sections listed above are present and non-empty

---

## Output Format (Terminal Summary)

After saving the report, display a human-readable summary with: status, score/100, score breakdown table (2 dimensions), requirement coverage table (per-REQ), blocking issues list, edge case coverage count, and top 3-5 recommendations.

For the exact template format, see `appendix/scoring-reference.md`.

---

## Integration with SDLC Pipeline

When invoked by the `sdlc-pipeline` skill:

1. **Input**: Receives `--ticket` and expects checkpoint artifacts to be populated
   by prior pipeline stages (requirements, architecture, implementation, simplify, review)
2. **Subagent results**: May receive aggregated results from parallel review agents
   (spec-reviewer, test-engineer, security-auditor) via checkpoint files
3. **Output**: Writes `ph8_verification_report.md` and updates `pipeline_state_<ticket>.json`
4. **Gate decision**: The pipeline reads `summary.status` to decide whether to
   proceed to PR creation or loop back for remediation

### Pipeline Status Mapping

| Verification Status | Pipeline Action |
|--------------------|----------------|
| `passed` | Proceed to PR creation |
| `passed_with_warnings` | Proceed to PR creation with warnings in PR description |
| `failed` | Loop back to implementation phase with blocking recommendations |
| `blocked` | Cannot verify — missing prerequisites |

---

## Error Handling

### Missing Checkpoint Directory
```
Error: Artifacts directory not found at docs/artifacts/<TICKET>/
Resolution: Run the SDLC pipeline from the requirements phase first, or create the
artifacts directory manually with the required artifacts.
```

### Missing Artifacts
```
Error: Required artifact missing: <artifact_name>
Resolution: The <phase> phase must complete before verification.
  - ph1_problem_spec.md -> requirements phase
  - ph2_design_spec.md -> architecture phase
  - ph5_6_impl_manifest.md -> implementation phase
```

### Test Execution Failure
```
Warning: Could not execute tests. Falling back to static analysis.
Reason: <error message>
Impact: Test pass rate will be scored as 0. Recommendation added to fix test setup.
```

---

## References

- Read `references/verification-checklist.md` only if you need checklist items beyond the category tables in this file
- `appendix/examples.md` — Output examples for steps 3-6 and report structure
- `appendix/scoring-reference.md` — Detailed scoring formulas, category tables, terminal output template
- `appendix/evaluation.md` — Trigger testing table

For related skills:
- `skills/security-scan/SKILL.md` — Security audit (provides SF findings for review phase)
- `skills/generate-tests/SKILL.md` — Test generation (provides test coverage)
