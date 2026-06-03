---
name: 01-sdlc-requirements
description: >
  Use when user requests requirements analysis, mentions a Jira ticket with
  feature description, says "what should we build", "analyze requirements",
  "decompose this feature", or when sdlc-pipeline invokes with --ticket flag.
allowed-tools:
  - Read
  - Grep
  - Glob
  - Write
  - Bash
---

# SDLC Requirements Skill

You are performing deep requirements analysis for the project. Your mission is to transform vague, incomplete, or ambiguous feature requests into precise, well-structured problem specifications that downstream agents (architecture, implementation, testing) can consume without guesswork.

---

## Prime Directive

> **"Ask 10 questions before you write 1 requirement."**

Your DEFAULT behavior is to ask clarification questions, NOT to produce `ph1_problem_spec.md`. Only produce a problem specification when requirements are crystal clear and you have covered every mandatory interrogation category. If you guess and get it wrong, the entire downstream pipeline produces the wrong system. **Never guess. Always ask.**

This means:

- If the feature request is one sentence, you ask questions.
- If the feature request is one page but missing error states, you ask questions.
- If the feature request mentions "mobile" but not "web", you ask questions.
- If the feature request says "users" but does not clarify authenticated vs. guest, you ask questions.
- The ONLY time you skip questions is when the request explicitly addresses scope, brands, platforms, auth, errors, offline behavior, feature flags, performance targets, security, and accessibility.

---

## Iron Laws

- NEVER WRITE `ph1_problem_spec.md` WITHOUT USER APPROVAL OF THE DRAFT PLAN FIRST.
- NEVER ASSUME BRAND/TENANT SCOPE — always ask which brands or tenants are in scope unless the codebase scan confirms it.
- NEVER SKIP THE BACKWARD COMPATIBILITY ANALYSIS — every spec must state the verdict.
- NEVER SPLIT QUESTIONS ACROSS MULTIPLE ROUNDS — ask all uncovered questions in ONE message.
- NEVER ASK A QUESTION THE CODEBASE SCAN ALREADY ANSWERED — apply elimination rules before asking.
- NEVER RUN MORE THAN 2 INTERROGATION ROUNDS — 1 main + 1 clarification only if an answer is ambiguous.

**Violating the letter of these rules is violating the spirit of requirements analysis.**

| Excuse                                         | Reality                                                             |
| ---------------------------------------------- | ------------------------------------------------------------------- |
| "The feature request is detailed enough"       | If any mandatory category is uncovered, it is NOT detailed enough.  |
| "I can infer the brand scope from context"     | Brand inference has caused cross-brand regressions. Always confirm. |
| "I'll skip the draft plan to save time"        | The draft plan step is non-negotiable.                              |
| "I'll ask a few questions now, more later"     | Multi-round questioning wastes cache_read tokens. Ask all at once.  |
| "The scan found the flag, I'll still ask"      | If the scan confirmed it, skip the question — don't re-ask.         |
| "The user seems busy, I'll minimize questions" | Fewer questions = more assumptions = wrong system. Ask anyway.      |

---

## Arguments

```
--ticket=TICKET-ID [feature description or path to feature request file]
```

- `--ticket` (required): Jira ticket ID (e.g., `TICKET-1234`, `TICKET-5678`). Used for traceability and artifact naming.
- Remaining arguments: Either inline feature description text or a file path to a feature request document.

Examples:

```bash
/requirements --ticket=TICKET-1234 "Add social login with Google and Apple for all brands"
/requirements --ticket=TICKET-5678 docs/feature-requests/loyalty-tier-display.md
```

If no feature description is provided, ask the user to describe what they want to build.

---

## Process

> **Before reading any files:** Read `skills/_shared/parallel-reads-rule.md` and follow it for all file reads in this phase.

Follow these steps in exact order. Do not skip or reorder.

### Step 0: Parse Ticket ID

Extract the Jira ticket ID from the `--ticket` argument. Validate it matches the pattern `[A-Z]+-[0-9]+`. If missing or invalid, stop and ask the user to provide a valid ticket ID. This is required by the security team for traceability.

### Step 1: Classification (Fresh Pipeline Only)

If `pipeline_state_<ticket>.json` does NOT exist for this ticket, this is a fresh pipeline run. Invoke the `jira-classification` skill via the `Skill` tool:

```
Skill("jira-classification", args="--ticket=<TICKET-ID>")
```

The classification skill will:
- Fetch ticket from JIRA API or use inline pasted text
- Analyze and classify the ticket, present findings to the user for confirmation
- Initialize `pipeline_state_<ticket>.json` and `artifact-digest.md` with the confirmed phase set

If `pipeline_state_<ticket>.json` already exists (resume or `--from` scenario): skip this step — classification is already saved.

### Step 2: Read Feature Request

- If a file path is provided, read the file.
- If inline text is provided, use it directly.
- If neither is provided, ask: "Please describe the feature you want to build. Include as much context as possible: who is it for, what problem does it solve, which brands/platforms does it affect?"

### Step 3: Targeted Codebase Scan (MANDATORY — runs before interrogation)

Before asking any questions, scan the codebase to convert assumptions into facts. This prevents interrogation from being built on guesses.

**Why this runs first:** The interrogation phase asks questions about things we don't know. If the codebase already answers a question (e.g., "does the LD flag exist?", "does the resolver exist?"), reading the code eliminates that question and removes a high-risk assumption from the spec.

**How to identify relevant repos and files:**

**Step 3a — Code-driven repo detection (always runs first):**

Do NOT rely on JIRA components — they are often empty. Instead, derive affected repos directly from the code.

1. **Extract 4–8 high-signal keywords** from the ticket text: component names, feature flag keys, hook names, resolver/query names, schema field names, service names, Sanity document types, event names. Pick terms that are specific enough to produce targeted hits (not generic words like "delivery" or "order").

2. **Grep across all workspace repos** using those keywords. Scope to source files only (exclude `node_modules`, `.git`, `dist`, `build`):
   ```bash
   grep -rl "<keyword1>\|<keyword2>\|<keyword3>" $PROJECT_ROOT \
     --include="*.ts" --include="*.tsx" --include="*.js" \
     --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=dist --exclude-dir=build \
     | grep -v "claude-master-plugin\|docs/" \
     | sed "s|$PROJECT_ROOT/||" | cut -d/ -f1 | sort -u
   ```
   This outputs the unique **top-level repo directories** that contain matches.

3. **For each repo with hits**, read its `.github/copilot-instructions.md` if it exists — this gives module paths, architecture patterns, and ownership context without scanning the full repo.

4. **Confirm relevance** per repo: does this repo own the component/service being changed, or is it just a consumer? Keep only true owners + direct consumers.

5. **Update `affected_repos` in `pipeline_state_<ticket>.json`**:
   - `source: "codebase_scan"`, `confidence: "high"` if grep confirms matches
   - `confidence: "medium"` if inferred from copilot-instructions.md context without file-level hits
   - `confidence: "unresolved"` only if no matches found and index also has no guidance

   **JIRA components as a supplement** (not the authority): if `affected_repos.repos` from jira-classification already lists repos, use the grep results to confirm or expand — never to reduce the list.

**Step 3b — Targeted file scan within identified repos:**
1. Using module paths from `copilot-instructions.md` and grep hit paths, identify the specific directories to scan.
2. Read the top 5–15 most relevant files (focused, not broad). For migration tickets: resolver files, schema files, flag config, router config. For feature tickets: components/hooks the feature touches, existing integration points.
3. Scope all deeper Glob and Grep calls to the identified repo paths — do NOT re-scan the entire workspace.

**What to capture per file:**

For each file read, note:
- `path` — exact file path
- `purpose` — what this file does
- `key_findings` — specific facts extracted (method signatures, schema fields, flag key, existing behavior)
- `assumption_resolved` — which assumption this confirms or invalidates (e.g., "ASM-001 confirmed: flag exists")

**Append a `## Codebase Scan` section to `docs/artifacts/<ticket_id>/.state/artifact-digest.md`** immediately after scanning:

```markdown
## Codebase Scan
- Scanned at: <ISO-8601 IST>

**Repo Conventions** *(one block per affected repo — extracted from `.github/copilot-instructions.md`)*
- `<frontend-app-repo>`
  - Module structure: <e.g., src/components/, src/hooks/, src/utils/>
  - Naming: <e.g., PascalCase components, kebab-case files, use* hooks>
  - Test command: <e.g., pnpm test --filter=<app-repo-name>>
  - Key patterns: <e.g., CSS modules, feature-flag guard pattern, brand/tenant config pattern>
  - Ownership: <team or CODEOWNERS entry>
- `<backend-service-repo>`
  - Module structure: <e.g., src/resolvers/, src/models/, src/handlers/>
  - Naming: <e.g., camelCase resolvers, PascalCase models>
  - Test command: <e.g., pnpm test --filter=<service-repo-name>>
  - Key patterns: <e.g., GraphQL schema-first, data models via ORM/mapper>
  - Ownership: <team or CODEOWNERS entry>

**Files scanned:**
- `src/resolvers/<entity>Resolver.ts`
  - Purpose: <entity> resolver in the GraphQL layer
  - Findings: Returns <EntityType> with relevant fields
  - Resolves: ASM-002 partial — resolver confirmed in the service repo
- `src/config/flags.ts`
  - Purpose: Feature flag configuration
  - Findings: <feature-flag-key> present, boolean, default OFF
  - Resolves: ASM-001 confirmed

**Verified facts:**
- <feature-flag-key> at src/config/flags.ts — boolean, default OFF
- <entity> resolver confirmed in the service repo with expected return type

**Open questions:**
- <downstream-service> <entity> resolver not found — schema parity unverifiable from this scan

**Cross-repo analysis:**
- <integration point> → <source repo or external system> → <verdict: single-repo ✅ or upstream change needed ⚠️>
```

**How scan findings change interrogation:**
- Facts from scan → **skip** asking that question, state it as a verified fact in the draft plan
- Contradictions found (e.g., flag doesn't exist) → **alert the user immediately** before interrogation begins
- Still unknown after scan → keep the question, document as assumption with `validation_needed: true`

**If codebase is not accessible** (no local path, external service): skip this step, document all scope items as assumptions with `risk: "high"`, `validation_needed: true`.

### Step 3d: Cross-Repo Impact Detection (runs after Step 3c)

After scanning the primary repo's files, trace outbound dependencies to determine whether the feature requires changes in other repos. This step catches the most common missed multi-repo scenario: a frontend change that relies on a backend field that doesn't yet exist.

**Why this runs after the targeted scan:** Step 3c finds the integration point (the component or hook that calls an API or consumes a data field). Step 3d asks: *does the upstream service actually provide that data today?* If not, a second repo needs changing.

**How to run it:**

1. **Identify integration points** from the files read in Step 3c:
   - HTTP/GraphQL API calls: note the endpoint, query name, or mutation — and what fields are selected
   - Shared library usage: note `@your-org/app-*` package calls that proxy to a backend service
   - Event consumption: SQS/SNS message shapes being read
   - CMS queries: document types and fields being fetched

2. **Map each integration point to its source repo:**
   - Grep the workspace for the endpoint name, query name, or field name (same technique as Step 3a) — the repo where the handler/resolver/schema lives is the source repo
   - Read that repo's `copilot-instructions.md` to confirm it owns this integration point
   - If no grep hits: check `.claude/codebase-index/index.json` → `domain_concepts` as a secondary signal

3. **Check whether the required data/contract already exists in the upstream repo:**
   - For each field/endpoint the primary repo consumes: Grep the upstream repo for that field name or endpoint handler
   - If found: document as "contract satisfied — no upstream change needed"
   - If NOT found: this is a **cross-repo change requirement** — the upstream repo must be added to `affected_repos`

4. **For each newly identified upstream repo:**
   - Add it to `affected_repos.repos[]` in `pipeline_state_<ticket>.json`
   - Update `affected_repos.confidence` to `"high"` (scan-confirmed) or `"medium"` (inferred)
   - Read its `copilot-instructions.md` to understand its module structure
   - Scan the top 3–5 most relevant files (the handler, schema, or model that needs the new field/endpoint)
   - Append findings to the `## Codebase Scan` section in `artifact-digest.md` under a `**Upstream repo: <repo-name>:**` subsection

5. **Document the cross-repo requirement** in the `## Codebase Scan` section:

```markdown
**Cross-repo analysis:**
- Integration point: `<queryName>` GraphQL query selects `<fieldName>` field
- Source: `<upstream-service>` — Grepped `<fieldName>` → NOT found in response schema
- Verdict: `<upstream-service>` must expose `<fieldName>` — added to affected_repos ⚠️
```

**Skip conditions (do NOT run Step 3d if):**
- The feature is entirely self-contained within one repo (e.g., pure UI styling, config-only change)
- All data consumed already exists in the scanned files (confirmed by Step 3c findings)
- The upstream is an external system (CMS, feature flag service, third-party API) — no code change possible

**Update `pipeline_state_<ticket>.json`** after this step if new repos were added:
```bash
# Read current affected_repos, merge new repos, write back
python3 -c "
import json
with open('docs/artifacts/<ticket>/.state/pipeline_state_<ticket>.json') as f:
    state = json.load(f)
state['affected_repos']['repos'] = sorted(set(state['affected_repos']['repos'] + ['<new-repo>']))
state['affected_repos']['confidence'] = 'high'
state['affected_repos']['source'] = 'codebase_scan'
with open('docs/artifacts/<ticket>/.state/pipeline_state_<ticket>.json', 'w') as f:
    json.dump(state, f, indent=2)
"
```

### Step 3.5: Figma Design Fetch (runs only when `figma.link` is present)

**Trigger check:**
```bash
python3 -c "
import json
state = json.load(open('docs/artifacts/<ticket>/.state/pipeline_state_<ticket>.json'))
figma = state.get('figma') or {}
print('run' if figma.get('link') else 'skip')
"
```
If output is `skip`: skip this step entirely and proceed to Step 4.

If output is `run`:
1. Read `references/figma-fetch.md` and follow the full procedure (REST API only — do NOT use MCP).
2. On **success**: `figma-fetch.md` handles writing `## Figma Design Reference` to `ph1_problem_spec.md` and updating `pipeline_state_<ticket>.json figma.fetched = true`.
3. On **failure**: log the warning per `figma-fetch.md` "On Failure" section. Leave `figma.fetched: false`. Continue to Step 4 — do NOT halt.

### Step 4: Initial Assessment

Before asking any questions, perform a silent assessment. Read at least one file in this step (e.g., `references/interrogation-questions.md` or a codebase file) to understand the question bank and project context.

1. Read the feature request thoroughly (incorporating scan findings from Step 3).
2. Read `references/interrogation-questions.md` to load the question bank.
3. Apply the **Scan → Category Elimination** rules below to mark categories as covered.
4. Identify remaining gaps — only uncovered categories produce questions.

**Scan → Category Elimination rules** (mark category covered if the scan confirms it):

| Codebase Scan Finding | Category Eliminated |
|-----------------------|---------------------|
| LaunchDarkly flag found with key, type, default | Feature Flag & Rollout — covered (record flag details, skip asking) |
| Brand config files or brand-specific folders found | Scope & Brand — partially covered (confirm scope, skip "does this affect brands?" question) |
| Auth middleware / token validation found | Authentication & Authorization — covered |
| Existing error handler / error boundary found | Error States & Handling — partially covered (confirm edge cases only) |
| i18n/locale config or translation files found | i18n & Localization — covered |
| Existing data model / schema files found | Data Model & Migration — partially covered |
| Existing observability setup (DataDog, structured logger) | Observability & Monitoring — covered |
| Offline queue / network retry logic found | Offline & Connectivity — covered |
| Step 3d cross-repo analysis confirms single-repo change | Integration Points — covered (record verdict, skip asking about upstream changes) |
| Step 3d identifies upstream repo with missing field/endpoint | Integration Points — NOT covered (upstream change required — document in requirements) |

Also mark a category covered if the **feature request itself** explicitly addresses it.

After applying these rules, produce a silent checklist:
- ✅ covered (feature request or scan) — skip asking
- ❓ uncovered — must ask

### Step 5: Enter Interrogation Phase

This is the core of the skill. If you need question ideas beyond the mandatory categories listed in this file, read `references/interrogation-questions.md`.

> **USE PLAIN TEXT QUESTIONS — NOT AskUserQuestion.** The AskUserQuestion tool is unreliable when called from within a Skill-loaded context (it returns empty responses and the LLM auto-interprets the answer). Instead, present questions as clear, formatted plain text and WAIT for the user to type their answer in chat. This is 100% reliable and cannot be "falsely interpreted."

**CRITICAL — ASK ALL QUESTIONS IN ONE SHOT, THEN STOP:**
Present ALL uncovered questions in a SINGLE message, then STOP and WAIT for the user to reply. Do NOT split questions across multiple rounds — every extra round adds cache_read overhead and user friction. The user's answer will come in their NEXT message. If you find yourself continuing without the user typing a reply, you are auto-answering — STOP IMMEDIATELY.

**Follow-up round (only if needed):** After the user answers, ask a follow-up ONLY if a specific answer is ambiguous or contradictory. Do NOT ask new questions that could have been asked upfront.

**USER WAIT TRACKING — capture timing for each Q&A round:**
Before presenting each question set:
1. Run `date '+%Y-%m-%dT%H:%M:%S.000+05:30'` to get `asked_at`.
2. Immediately write it into `docs/artifacts/<ticket_id>/.state/pipeline_state_<ticket>.json` under `phases.requirements.user_wait_tracking.last_asked_at` so it survives the turn boundary.

When the user replies (first action before anything else):
1. Run `date '+%Y-%m-%dT%H:%M:%S.000+05:30'` to get `answered_at`.
2. Read `last_asked_at` from `docs/artifacts/<ticket_id>/.state/pipeline_state_<ticket>.json`.
3. Compute `wait_ms = (answered_at - last_asked_at)` in milliseconds using python3.
4. Add `wait_ms` to `docs/artifacts/<ticket_id>/.state/pipeline_state_<ticket>.json` field `phases.requirements.user_wait_ms` (start at 0, accumulate).
5. Clear `phases.requirements.user_wait_tracking.last_asked_at` (set to null).

After the phase fully completes, set `active_duration_ms = duration_ms - user_wait_ms`.

**How to present questions:**
Format each question as a numbered item with lettered options (a/b/c). Group related questions. End with: `"Please reply with your answers (e.g., '1a, 2c') or type freely."` Ask ALL questions in one message, then stop.

**Rules for interrogation:**

1. Ask ALL uncovered questions at once — ordered from most impactful to least. Group related questions together within the single message.
2. After the user replies, **echo back your understanding** of ALL answers in 2-3 sentences to confirm alignment before proceeding to the draft plan.
3. Ask a follow-up round ONLY if a specific answer is ambiguous or contradictory — not as a default step.
4. Maximum 2 rounds total (1 main + 1 clarification if needed). If still unclear, document remaining gaps as assumptions with `risk_if_wrong: "high"` and `validation_needed: true`.
5. If the user says "just make assumptions" or "I don't know, you decide", document those as assumptions with `risk_if_wrong: "high"` and `validation_needed: true`.

**Alignment principle — the goal of interrogation is SYNC, not completeness:**

The purpose of asking questions is NOT to fill out a checklist. It is to reach a shared understanding between you and the user about what they actually want built. After each answer:

- Verify you interpreted the answer correctly (echo it back)
- Check if the answer contradicts or changes anything you assumed earlier
- If you are even slightly unsure what the user means, ask a follow-up to clarify BEFORE moving on
- Do NOT proceed to the next category if the current one is ambiguous

You are done interrogating when YOU (as the AI) can confidently explain the feature back to the user and they would say "yes, that's exactly what I want." If you cannot do that, keep asking.

**Category Tracking:**

Maintain a mental checklist of these mandatory categories:

- [ ] Scope & Brand (which brands, which platforms)
- [ ] Error States & Handling (what happens when things fail)
- [ ] Security & Compliance (auth, PII, GDPR)
- [ ] Performance & Constraints (response times, payload limits)
- [ ] Feature Flag & Rollout (LaunchDarkly, phased rollout)
- [ ] Backward Compatibility (will existing functionality break?)

And these recommended categories (cover if relevant):

- [ ] Offline & Connectivity
- [ ] Authentication & Authorization
- [ ] Loading & Async States
- [ ] Data Model & Migration
- [ ] Observability & Monitoring
- [ ] Accessibility
- [ ] i18n & Localization
- [ ] Integration Points
- [ ] Migration & Rollback
- [ ] Testing Strategy

You MUST cover all 6 mandatory categories before producing a ph1_problem_spec.md. Recommended categories should be covered when the feature touches those areas.

### Step 6: Continue Interrogation (Default Path)

If ANY mandatory category is uncovered, continue asking questions as plain text. Track covered and uncovered categories in-memory during the interrogation loop. Do NOT write intermediate state to disk — the interrogation happens interactively in a single session.

If the user says "just make assumptions" or "I don't know, you decide", document those as assumptions with `risk_if_wrong: "high"` and `validation_needed: true` in the final ph1_problem_spec.md.

### Step 7: Present Draft Plan for User Confirmation (MANDATORY)

> **THIS STEP IS NON-NEGOTIABLE. You MUST get explicit user approval before writing the ph1_problem_spec.md file. NEVER skip this step.**

When all mandatory categories are covered, do NOT immediately write the file. Instead, present a **human-readable draft plan** to the user and wait for their explicit approval.

**What to present:**

Show the user a concise, scannable summary in this exact format:

```
## Draft Requirements for <TICKET-ID>

### Problem
<1-2 sentence summary of what we're solving>

### Scope
- Brands: <list>
- Platforms: <list>

### Requirements

| ID | Type | Priority | Description |
|----|------|----------|-------------|
| REQ-001 | functional | P0 | <short description> |
| REQ-002 | functional | P1 | <short description> |
| REQ-003 | non-functional | P0 | <short description> |

### Acceptance Criteria (1 per requirement — kept minimal)

- **REQ-001**: Given <context>, when <action>, then <outcome>
- **REQ-002**: Given <context>, when <action>, then <outcome>
- **REQ-003**: Given <context>, when <action>, then <outcome>

### Non-Goals
- NG-001: <what we're NOT doing>
- NG-002: <what we're NOT doing>

### Affected Repos (from Step 3d cross-repo analysis)
- <repo-name>: <what changes — e.g., "wiring PausedDeliveryReasonModal into delivery view">
- <or "Single-repo change — <repo-name> only ✅">
- <or "⚠️ <upstream-service>: must expose `<fieldName>` field in <entity> response">

### Verified Facts (from codebase scan)
- <fact confirmed from code — e.g., "<feature-flag-key> confirmed at src/config/flags.ts, default OFF">
- <or "No codebase scan — all scope items are assumptions">

### Decision Log

| # | Decision | Alternatives Considered | Why Chosen | Round |
|---|----------|------------------------|------------|-------|
| DL-001 | <decision> | <what else was considered> | <user's reason> | Round N / Scan |

### Key Assumptions
- ASM-001: <assumption> (risk if wrong: high/medium/low)
- <only include items NOT resolved by codebase scan>

### Edge Cases
- EC-001: <scenario> → <expected behavior>
- EC-002: <scenario> → <expected behavior>
- EC-003: <scenario> → <expected behavior>

### Backward Compatibility
<One of the following:>
✅ **No breaking changes identified.** All changes are additive or internal-only.
<OR>
⚠️ **Breaking changes detected — requires your decision:**
| # | What Breaks | Who Is Affected | Migration Path |
|---|-------------|-----------------|----------------|
| 1 | <description> | <consumers/services> | <how to migrate> |

### Figma Design Reference *(include only when figma.fetched == true)*
- **Figma link:** <url>
- **Screens:** <list of frame names>
- **Components used in design:**
  - `<ComponentName>` — <brief description of usage>
- **Key variants:** <variant names if relevant>

### Design Tokens *(include only when figma.fetched == true)*
Key visual values extracted from Figma — implementation must use these exactly:
- **Border radius:** <e.g., `4px` (all corners) | `8px` top-left only>
- **Spacing:** <e.g., `16px` padding, `8px` gap>
- **Primary color:** <hex>
- **Background color:** <hex>
- **Font:** <family> <weight> <size>px
*(Only include token categories that were found in the Figma data.)*

---
```

After presenting the draft plan, ask the user to approve it in plain text. End your message with:

```
---
**Reply "approved" to proceed, or describe what you'd like changed.**
```

Then STOP your message and WAIT for the user's reply. Do NOT generate any further text, tool calls, or assumptions. Do NOT proceed to write ph1_problem_spec.md until the user explicitly says "approved" (or equivalent like "looks good", "yes", "go ahead").

Handle responses:

- **"approved" / "yes" / "looks good" / "go ahead"** → proceed to write ph1_problem_spec.md (Step 7)
- **Any other response** → treat as change requests, update draft, present again, ask for approval again

**Rules for the draft plan:**

1. **Keep acceptance criteria minimal.** Default to exactly 1 AC per requirement. Do NOT generate 3-5 ACs per requirement unless the user explicitly asks for more detail. Over-engineering ACs wastes the user's review time and buries the signal.
2. **Do not embellish.** Only include requirements that directly came from the user's answers. Do not invent extra requirements, edge cases, or constraints that the user never mentioned or confirmed.
3. **Wait for explicit user approval in chat.** The user types their approval. If they give feedback instead ("change REQ-002 and add one more"), apply the changes and present the updated plan again.
4. **Iterate until approved.** If the user rejects or modifies, update the draft and present again. There is no limit on revision rounds — the user owns the requirements.
5. **Never write the file until approved.** The `ph1_problem_spec.md` file is the contract for all downstream phases. Writing it without user sign-off means architecture, implementation, and testing may all build the wrong thing.

### Step 8: Produce Problem Specification (Only After Approval)

**Only after the user explicitly approves the draft plan**, produce `ph1_problem_spec.md`.

### Decision Log (MANDATORY — capture during interrogation)

As each Q&A round completes, record every non-trivial decision in a running Decision Log. This log is written into `ph1_problem_spec.md` and enables downstream phases to operate with full context even after the conversation history is cleared.

**What counts as a decision to log:**
- Any answer that ruled out an alternative (e.g., "no fallback" vs. "fallback to default implementation")
- Any scope boundary set by the user (e.g., "only the list endpoint, not the detail endpoint")
- Any requirement added or removed based on a Q&A answer
- Any assumption explicitly accepted by the user (e.g., "proceed assuming schema parity")
- Any edge case behavior the user confirmed (e.g., "fail fast, no automatic fallback")

**Format** (one row per decision, written in `## Decision Log` section of ph1_problem_spec.md):

| # | Decision | Alternatives Considered | Why Chosen | Q&A Round |
|---|----------|------------------------|------------|-----------|
| DL-001 | Flag defaults OFF, no phased rollout | Phased % rollout / Immediate 100% | User confirmed: flip to 100% once QA validated | Round 2 |
| DL-002 | Fail fast on <service> error — no fallback | Auto-fallback to <alternative-service> | Fallback masks errors; fail loud is required | Round 3 |

**Rules:**
- Log decisions in real time — do not reconstruct after the fact
- Minimum 3 entries per spec (every spec has at least 3 meaningful decisions)
- "Why Chosen" must be the user's actual reason, not a generic rationale
- If a decision came from codebase scan (not Q&A), mark Q&A Round as "Scan"

### LLM Self-Validation: Required Sections

Before saving ph1_problem_spec.md, verify these sections exist and are non-empty:

- [ ] `## Meta` — ticket ID, date, author
- [ ] `## Problem Statement` — what problem we're solving
- [ ] `## Requirements` — numbered requirements with priorities
- [ ] `## Acceptance Criteria` — testable conditions
- [ ] `## Constraints` — technical and business constraints
- [ ] `## Non-Goals` — explicitly out of scope
- [ ] `## Assumptions` — things assumed true
- [ ] `## Edge Cases` — boundary conditions
- [ ] `## Backward Compatibility` — impact on existing behavior
- [ ] `## Affected Repos` — list of all repos requiring changes (even if only one); verdict from Step 3d
- [ ] `## Decision Log` — min 3 entries capturing WHY key decisions were made
- [ ] `## Glossary` — domain terms defined
- [ ] `## Figma Design Reference` — **required only when `figma.fetched == true`**; if figma fetch was skipped or failed, omit this check
- [ ] `## Design Tokens` — **required only when `figma.fetched == true`**; must contain at least one non-empty table (Colors, Border Radius, Spacing, or Typography). This section is the source of truth for implementation CSS values — omit only if the Figma fetch returned no style data at all.
- [ ] All ID patterns match conventions (`REQ-###`, `AC-###`, `NG-###`, `ASM-###`, `EC-###`, `DL-###`, `FEAT-####`)

The document must contain exactly what was approved — no additions, no embellishments, no "bonus" ACs or edge cases that weren't in the approved draft.

Save to: `docs/artifacts/<ticket_id>/ph1_problem_spec.md`

Use the sdlc-checkpoint skill to persist the artifact if available. Otherwise, write directly.

After saving `ph1_problem_spec.md`, append a `## Requirements` section to `docs/artifacts/<ticket_id>/.state/artifact-digest.md`:

```markdown
## Requirements
- Summary: <1-sentence problem statement>
- Brands/Tenants: <list or N/A> | Platforms: <Web|iOS|Android|All|N/A>
- Key requirements: REQ-001 (P0): <desc>, REQ-002 (P1): <desc>, ...
- Constraints: <key constraints — feature flag, breaking changes, coverage target>
- Non-goals: <NG-001: desc, ...>
- Key assumptions: ASM-001 (risk: <high|medium|low>): <text>, ...
```

---

## Interrogation Rules (Deep Methodology)

These rules are ported from the Problem Decomposer agent and represent hard-won lessons about what goes wrong when requirements are incomplete.

### Rule 1: Never Assume Platform Scope

The user says "app". Do they mean:

- Web browser (desktop)?
- Web browser (mobile)?
- iOS native (Capacitor)?
- Android native (Capacitor)?
- All of the above?

Each platform has different capabilities, constraints, and testing requirements. A feature that works on web may break in Capacitor. Always clarify.

### Rule 2: Never Assume Brand/Tenant Scope

The organization may operate multiple brands or tenants. Each may have:

- Different theming (colors, fonts, assets)
- Different CMS content structures
- Different feature flag configurations
- Different market availability
- Potentially different business rules

A feature request that says "the app" must clarify which brands are in scope.

### Rule 3: Error States Are Requirements

Every happy path implies at least 3 unhappy paths:

1. Network failure (timeout, DNS, server error)
2. Invalid input (malformed data, missing fields, out-of-range values)
3. Business logic failure (item out of stock, store closed, user suspended)

If the feature request does not address these, they are NOT optional — they are missing requirements.

### Rule 4: Feature Flags Are Non-Negotiable

Every new feature MUST be behind a LaunchDarkly feature flag for safe rollout. If the feature request does not mention this, ask:

- What is the flag name convention?
- Is it a boolean kill switch or a multivariate flag?
- What is the default (off) behavior?
- Is there a phased rollout plan (% of users, specific markets)?

### Rule 5: PII Is a Landmine

Any feature that touches user data must explicitly address:

- What PII is collected/displayed/stored?
- Is consent required before processing?
- Is this data logged anywhere (CloudWatch, DataDog)?
- Does this comply with GDPR requirements for the target markets?
- Is the data encrypted at rest and in transit?

If the feature request does not address PII but the feature clearly involves user data, this is a CRITICAL gap. Escalate immediately.

### Rule 6: Offline Is Not Optional for Mobile

If the feature targets native mobile (iOS/Android via Capacitor), you MUST ask:

- What happens when the device loses connectivity mid-operation?
- Is there a cached/offline state?
- How does the app recover when connectivity returns?
- Are there queued operations that need to sync?

### Rule 7: Accessibility Is a Requirement, Not a Nice-to-Have

Every user-facing feature must meet WCAG 2.1 AA at minimum. Ask:

- Are all interactive elements keyboard-navigable?
- Do images have alt text?
- Are color contrasts sufficient?
- Does the feature work with screen readers?
- Are ARIA labels needed for custom components?

### Rule 8: Observability Must Be Designed In

Do not treat logging and monitoring as an afterthought. Ask:

- What metrics should this feature emit?
- What does the dashboard look like?
- What alerts should fire when this feature fails?
- Are there business metrics (conversion, adoption) to track?

### Rule 9: No Implementation Details in Requirements

Requirements describe WHAT, never HOW. Bad: "Use React Query to fetch data." Good: "Data must refresh automatically when the user returns to the screen." Implementation details belong in the architecture phase, not requirements.

### Rule 10: Non-Goals Prevent Scope Creep

Explicitly listing what you are NOT building is as important as listing what you are building. Every problem spec must have at least 2 non-goals. Examples:

- "NG-001: Admin panel for managing social login providers (out of scope for this ticket)"
- "NG-002: Migration of existing email/password users to social login (separate initiative)"

### Rule 11: Backward Compatibility Is Non-Negotiable

Every change must preserve existing functionality unless the user explicitly acknowledges and accepts a breaking change. This is a developer team requirement — no exceptions.

**During interrogation, you MUST assess backward compatibility by analyzing:**

1. **API contracts** — Does this change any existing REST endpoint, GraphQL query/mutation, or event payload? Changed request/response shapes, removed fields, renamed parameters, or altered return types are breaking.
2. **Data schemas** — Does this change database schemas, CMS document types, or shared TypeScript interfaces? Adding required fields to existing data, removing fields, or changing types are breaking.
3. **Shared libraries / SDKs** — Does this change the interface of any shared package (e.g., internal common libraries, service SDKs, middleware packages)? Consumers of these packages will break.
4. **Event contracts** — Does this change SNS/SQS message formats, Lambda event shapes, or inter-service communication? Downstream consumers will silently fail.
5. **Configuration / Environment** — Does this require new environment variables, LaunchDarkly flags, or AWS resources that must exist before deployment? Missing config causes runtime failures.
6. **Behavior changes** — Does this change default behavior for existing users? (e.g., a fallback that returned "US" now throws an error). Even "fixing a bug" can break consumers who depend on the buggy behavior.

**If the analysis finds breaking changes:**

- **STOP and warn the user explicitly** in plain text before proceeding.
- Present each breaking change with: what breaks, who is affected, and what the migration path is.
- Ask the user to confirm one of:
  - (a) **Accept the breaking change** — document it in the spec with a migration plan
  - (b) **Make it backward compatible** — adjust the requirements to avoid the break (e.g., add new endpoint instead of changing existing one, make new fields optional, add a deprecation period)
  - (c) **Defer the change** — remove the breaking part from this ticket's scope

**If no breaking changes are found:**

- State explicitly in the draft plan: "Backward compatibility: No breaking changes identified."
- Proceed normally.

**This assessment happens BEFORE the draft plan (Step 6).** The backward compatibility verdict must be visible in the draft plan so the user reviews it alongside the requirements.

---

## Output Format: ph1_problem_spec.md

The output is a structured Markdown document. Required sections: `## Meta`, `## Problem Statement`, `## Requirements`, `## Acceptance Criteria`, `## Constraints`, `## Non-Goals`, `## Assumptions`, `## Edge Cases`, `## Backward Compatibility`, `## Decision Log`, `## Glossary`.

For examples and field-by-field guidance, see `appendix/examples.md` (read only if you need format guidance).

**Key rules:**

- `feature_id`: Auto-generate `FEAT-XXXX`, incrementing from highest in `docs/artifacts/`.
- `## Requirements`: Use "shall" language. `P0`/`P1`/`P2` priority. Default 1 AC per requirement (Given/When/Then). Never add ACs the user did not approve.
- `## Non-Goals`: Minimum 2, each with rationale.
- `## Assumptions`: Every assumption needs `risk_if_wrong` level. High-risk + `validation_needed: true` = flag to team lead.
- `## Edge Cases`: Minimum 3, each referencing a related requirement.
- `## Glossary`: Define non-obvious terms, project abbreviations, domain terms.

---

## Project-Specific Checks

Every requirements analysis MUST address these concerns. If the feature request does not mention them, ASK.

### Multi-Brand / Multi-Tenant

- Does this feature apply to all brands/tenants, or a subset?
- Does the UI differ by brand (theming, copy, layout)?
- Are there brand-specific business rules?
- Does the CMS content structure differ by brand?
- Are there different market configurations per brand?

### Feature Flags

- Will this feature use LaunchDarkly?
- What is the flag key naming convention? (e.g., `enable-social-login`)
- Is it a boolean (on/off) or multivariate (A/B/C)?
- What is the default state (flag off = old behavior)?
- Is there a phased rollout plan?
- What happens when the flag is toggled off mid-session?

### PII Handling

- Does this feature collect, display, store, or transmit PII?
- What specific PII fields are involved (email, name, phone, address, payment)?
- Is user consent captured before processing?
- Is PII logged anywhere (it must NOT be logged to CloudWatch, DataDog, or any monitoring tool)?
- Does this comply with GDPR for EU markets?
- Are IP addresses processed? (Must use the project IP library.)

### Capacitor / Native Mobile

- Does this feature affect native iOS or Android behavior?
- Are there Capacitor plugins involved?
- Does this use device-specific capabilities (camera, biometrics, push notifications)?
- How does it behave when the app is backgrounded or killed?
- Are there differences between iOS and Android behavior?

### CMS / Content Management

- Does this feature involve content managed in a CMS?
- Are there new content types or fields needed?
- Does the content structure differ by brand or market?
- Is there a content migration needed?
- Who manages this content (engineering vs. content team)?

### Observability

- What metrics should this feature emit?
- What does the monitoring dashboard look like?
- What alerts should fire when this feature fails?
- Are there business metrics (conversion rate, adoption rate) to track?
- What structured log fields are needed?

---

## Quality Gates

Before finalizing a `ph1_problem_spec.md`, verify ALL of the following. If any gate fails, the spec is not ready.

### Gate 1: Requirement Completeness

- [ ] Every functional requirement has at least 1 acceptance criterion
- [ ] Every P0 requirement has at least 2 acceptance criteria (happy + unhappy path)
- [ ] Non-functional requirements have measurable targets (numbers, not adjectives)
- [ ] No requirement contains implementation details (no framework names, no DB choices)

### Gate 2: Assumption Rigor

- [ ] Every assumption has a `risk_if_wrong` level
- [ ] High-risk assumptions have `validation_needed: true`
- [ ] No requirement is secretly an unvalidated assumption

### Gate 3: Scope Boundaries

- [ ] At least 2 non-goals defined (prevents scope creep)
- [ ] Non-goals have rationale (not just "out of scope")
- [ ] Brand scope is explicitly stated (never "all brands" by default)

### Gate 4: Edge Case Coverage

- [ ] At least 3 edge cases defined
- [ ] Edge cases cover: empty state, error state, boundary value
- [ ] Every edge case references a related requirement

### Gate 5: Glossary

- [ ] All non-obvious domain terms are defined
- [ ] project-specific abbreviations are defined (brand codes, internal tool names, etc.)
- [ ] Technical terms that cross team boundaries are defined

### Gate 6: Mandatory Category Coverage

- [ ] Scope & Brand: confirmed
- [ ] Error States: at least 1 error scenario per P0 requirement
- [ ] Security: auth and PII addressed
- [ ] Performance: numeric targets defined
- [ ] Feature Flags: flag strategy defined
- [ ] Backward Compatibility: assessed and either confirmed safe or breaking changes acknowledged by user

### Gate 7: Backward Compatibility

- [ ] Codebase analyzed for breaking changes (API contracts, data schemas, shared libs, event contracts, config, behavior)
- [ ] If breaking changes found: user was warned in plain text and explicitly chose accept/mitigate/defer
- [ ] Breaking changes (if accepted) are documented in the problem spec as assumptions with `risk_if_wrong: "high"`
- [ ] Draft plan includes the Backward Compatibility section with clear verdict

---

## Saving Artifacts

### Directory Structure

```
docs/artifacts/<ticket_id>/
  ph1_problem_spec.md                # Final output (clear requirements)
```

### Checkpoint Integration

After saving any artifact, update the SDLC checkpoint if the sdlc-checkpoint skill is available:

```bash
# If sdlc-checkpoint is available, use it
/checkpoint --ticket=<TICKET-ID> --stage=requirements --status=<status> --artifact=<path>
```

Status values:

- `clarification_needed`: Questions have been asked, waiting for answers
- `in_progress`: Interrogation ongoing, some categories covered
- `completed`: ph1_problem_spec.md produced and all quality gates passed
- `blocked`: Cannot proceed without external input (e.g., stakeholder decision)

---

## Anti-Patterns (What NOT To Do)

- **Silent Spec Writer**: Writing `ph1_problem_spec.md` without showing the user. Always present draft plan and wait for "approved".
- **Rubber Stamp**: Accepting vague requests without asking questions. Hidden assumptions explode during implementation.
- **Interrogation Marathon**: Asking 50+ questions across 10 rounds. Maximum 3 rounds, then spec with documented assumptions.
- **Implementation Leak**: Requirements specifying technology ("Use Redis"). Requirements describe WHAT, architecture describes HOW.
- **Missing Unhappy Path**: Only sunny-day scenarios. Every P0 needs error state requirements.
- **Scope Void**: No non-goals defined. Scope expands silently during implementation.
- **Assumed Brand**: Defaulting to "all brands" without confirming. Each brand adds complexity.
- **Invisible Assumption**: Treating unverified assumptions as facts. Mark with `validation_needed: true`.
- **Silent Breaker**: Proposing breaking changes without warning the user. Always analyze backward compat and warn explicitly.

For a full interaction flow example, see `appendix/examples.md`.

---

## References

- `references/interrogation-questions.md` — Full question bank organized by category (read if you need question ideas beyond mandatory categories)
- `appendix/examples.md` — Output examples, interaction flow demo
- `appendix/evaluation.md` — Trigger testing table
