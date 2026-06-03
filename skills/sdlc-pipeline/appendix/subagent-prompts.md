# Subagent Dispatch Prompt Templates

Use these templates when launching Phase 7 (Review) subagents and Phase 5 (Wave Execution) subagents. Substitute `{{TICKET_ID}}`, `{{FILES_MODIFIED}}`, and `{{PHASE_MODEL}}` before dispatching.

**MODEL ENFORCEMENT:** Every template includes `model: "{{PHASE_MODEL}}"`. This MUST be substituted with the value from `pipeline_state_<ticket>.json phases.<name>.model` before the Agent tool call is made. Never omit it — defaulting to the conversation model defeats the pipeline model config.

---

## 0. Wave Executor (Phase 5 — Parallel Implementation)

**Purpose:** Implement one or more files from a single wave as an isolated subagent.
Each wave executor gets a fresh context window with only the files it needs.

**Dispatch:** One Task tool call per wave (all files in a wave run in one subagent).
If a wave has many files (>5), split into sub-waves of 3-5 files each.

```
Agent tool:
  subagent_type: general-purpose
  model: "{{PHASE_MODEL}}"   ← substitute from pipeline_state_<ticket>.json phases.implementation.model
  description: "Wave {{WAVE_NUMBER}} implementation for {{TICKET_ID}}"
  prompt: |
    You are implementing Wave {{WAVE_NUMBER}} of a multi-wave implementation plan.

    ## Context
    Ticket: {{TICKET_ID}}
    Artifacts dir: docs/artifacts/{{TICKET_ID}}/

    ## Your Files (implement ALL of these)
    {{WAVE_FILES}}

    Each file entry has:
    - path: exact file path to create or modify
    - component_id: COMP-### from design_spec
    - purpose: what this file does

    ## Implementation Steps for This Wave
    {{WAVE_STEPS}}

    ## Implementation Guidelines
    {{IMPLEMENTATION_GUIDELINES}}

    ## Instructions
    1. For MODIFIED files: Read the existing file first, then apply changes.
       For NEW files: Create the file at the exact path specified.
    2. Follow the patterns_to_use, patterns_to_avoid, and naming_conventions in the guidelines above.
    3. After writing each file, verify it is non-empty and syntactically valid.

    ## Prior Wave Outputs (already completed — you may depend on these)
    {{PRIOR_WAVE_FILES}}

    ## Rules
    - Do NOT modify files outside your wave assignment.
    - Do NOT add features not described in the design_spec component.
    - Do NOT skip any file in your assignment.
    - If a dependency from a prior wave is missing or broken, STOP and report
      which dependency is missing and which component needs it.

    ## Output
    When done, report:
    {
      "wave": {{WAVE_NUMBER}},
      "files_completed": ["path1", "path2"],
      "files_failed": [],
      "issues": [],
      "summary": "one-paragraph description of what was implemented"
    }
```

---

## 1. Spec Compliance Reviewer (FIRST GATE)

**Purpose:** Verify implementer built what was designed — nothing more, nothing less.
**Dispatch BEFORE other reviewers.** If `spec_compliant: false`, fix gaps before proceeding.

```
Agent tool:
  subagent_type: general-purpose
  model: "{{PHASE_MODEL}}"   ← substitute from pipeline_state_<ticket>.json phases.review.model
  description: "Spec compliance review for {{TICKET_ID}}"
  prompt: |
    You are reviewing whether an implementation matches its approved design spec.

    ## Approved Design
    {{SPEC_CONTEXT}}

    ## Files Implemented
    {{FILES_MODIFIED}}

    ## CRITICAL: Do Not Trust — Verify

    Read the actual code. Compare against the Approved Design above.

    **Check for each component in design_spec.components[]:**
    - [ ] File exists at the exact path specified in component.file_path
    - [ ] Component has exactly the responsibility described (not more, not less)
    - [ ] Component dependencies match COMP-### IDs listed

    **Check for each API contract in design_spec.api_contracts:**
    - [ ] Hook/function names match the design
    - [ ] Return shape matches the defined interface
    - [ ] Every mutation has error handling as specified

    **Check for over-building:**
    - Did they add features not in the design spec?
    - Did they add "nice to have" improvements not requested?
    - Did they over-engineer with unnecessary abstractions?

    **Check for under-building:**
    - Are there components in the design that have no implementation?
    - Are there acceptance criteria from the Approved Design above not covered?

    **Return JSON:**
    {
      "spec_compliant": boolean,
      "over_built": ["description of each extra feature with file:line"],
      "under_built": ["description of each missing item with design_spec reference"],
      "path_mismatches": ["expected path vs actual path"],
      "summary": "one-paragraph assessment"
    }
```

---

## 2. Security Auditor

**Purpose:** Security and compliance review scoped to changed files.

```
Agent tool:
  subagent_type: client-master:security-auditor
  model: "{{PHASE_MODEL}}"   ← substitute from pipeline_state_<ticket>.json phases.review.model
  description: "Security audit for {{TICKET_ID}}"
  prompt: |
    Security audit for ticket {{TICKET_ID}}.

    ## Design Context
    {{SECURITY_CONTEXT}}

    ## Files to Scan
    {{FILES_MODIFIED}}

    ## Mandatory Checks (all must pass)
    1. No PII (email, phone, name, address, payment data) in any log statement
    2. No raw user objects passed to logger — trace full data flow
    3. IP addresses use project IP address library
    4. User data not processed before consent confirmed (user clicked accept button)
    5. No hardcoded secrets (API keys, tokens, passwords, private certs)
    6. No .env files referenced directly in code (use env vars or SSM)

    ## OWASP Checks (scoped to changed files)
    - A01 Broken Access Control: authorization checks on all mutations/routes
    - A02 Crypto Failures: no weak algorithms, proper key management
    - A03 Injection: no user input in dynamic queries (SQL, NoSQL, command)
    - A07 Auth Failures: JWT verify() not just decode(), proper session management

    ## Platform-Specific
    - GraphQL: introspection disabled in production, query depth limiting, APQ
    - Capacitor/mobile: sensitive tokens in Keychain/Keystore not localStorage,
      certificate pinning, deep link validation
    - Lambda: each function has its own IAM role, no wildcard resources
    - S3: Block Public Access verified before any bucket policy changes

    ## Output
    Return JSON:
    {
      "critical": [{"file": "", "line": 0, "issue": "", "risk": "", "remediation": ""}],
      "high": [{"file": "", "line": 0, "issue": "", "risk": "", "remediation": ""}],
      "medium": [{"file": "", "line": 0, "issue": "", "risk": "", "remediation": ""}],
      "low": [{"file": "", "line": 0, "issue": "", "risk": "", "remediation": ""}],
      "pii_risks": ["any potential PII exposure paths found"],
      "clean_files": ["files with no findings"]
    }
```

---

## 3. Test Engineer

**Purpose:** Verify test coverage against requirements and assess test quality.

```
Agent tool:
  subagent_type: client-master:test-engineer
  model: "{{PHASE_MODEL}}"   ← substitute from pipeline_state_<ticket>.json phases.review.model
  description: "Test coverage review for {{TICKET_ID}}"
  prompt: |
    Review test coverage for ticket {{TICKET_ID}}.

    ## Requirements & Design Context
    {{TEST_CONTEXT}}

    ## Test Files
    {{FILES_MODIFIED}} (filter for *.test.ts, *.spec.ts, e2e/*.spec.ts)

    ## Check
    1. Requirement coverage: map each AC to a test case. Flag uncovered ACs.
    2. Edge case coverage: map each edge_case to a test case. Flag uncovered.
    3. Test quality:
       - Tests verify behavior, not mock behavior
       - No testing implementation details (private methods, internal state)
       - clearAllMocks/resetAllMocks in beforeEach
       - Descriptive test names matching "should [behavior] when [condition]"
       - No .skip() or .only() left in test files
       - No hardcoded timeouts (use jest.useFakeTimers or waitFor)
    4. Missing test types:
       - Happy path covered?
       - Error/exception paths covered?
       - Edge cases (empty, null, boundary values) covered?

    ## Output
    Return JSON:
    {
      "coverage_gaps": [{"requirement_id": "", "acceptance_criteria": "", "status": "covered|missing"}],
      "edge_case_gaps": [{"edge_case": "", "status": "covered|missing"}],
      "test_quality_issues": [{"file": "", "line": 0, "issue": "", "fix": ""}],
      "recommendation": "sufficient | needs_more_coverage | needs_quality_fixes"
    }
```
