# Pull Request Description Template

The standard template for pull requests.

---

## Template

```markdown
### Jira Ticket Number
<!-- REQUIRED by the security team. Link the Jira ticket here. -->
<!-- The ticket ID must also appear in: -->
<!--   - Branch name:  TICKET-1234-some-new-feature -->
<!--   - PR title:     TICKET-1234: Add social login button for Google -->

[JIRA-TICKET-ID](https://your-org.atlassian.net/browse/JIRA-TICKET-ID)

---

### Type of Change
_Please delete options that are not relevant:_

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (change that causes existing functionality to break)
- [ ] Other (please explain):

---

### Context

<!-- Describe what this PR does. Explain the "why", not just the "what". -->
<!-- Include both BEFORE and AFTER behavior to make the change easy to understand and verify. -->

**Before:**
[Describe the previous behavior]

**After:**
[Describe the new behavior]

Include any relevant background or motivation for the change.

---

### Architecture Document (if applicable)
<!-- Link to an ADR, design doc, or architectural decision document if available. -->

N/A

---

### Evidence / Screenshots / Test Artifacts
<!-- Add screenshots, screen recordings, or artifacts that demonstrate the change. -->
<!-- Especially useful for frontend changes or user-facing features. -->

| Before | After |
| ------ | ----- |
| screenshot | screenshot |

---

### Postman Collection / SDK Update (if applicable)
<!-- If your change affects an API's request/response structure: -->

- [ ] Update the shared Postman collection
- [ ] Bump or update a relevant SDK if the change impacts a shared client library
- [ ] Notify any downstream consumers if needed

---

### How Has This Been Tested?
<!-- Describe the tests you ran to verify your changes. Include test tools, scenarios, and results. -->

- [ ] Unit tests added / updated and passing
- [ ] Integration tests added / updated and passing
- [ ] E2E tests added / updated and passing
- [ ] Manually tested locally
- [ ] Tested in staging / QA environment

---

### Checklist
_Note: Check only what's relevant. Use `[N/A]` where not applicable._

- [ ] My code follows the project's coding and PR guidelines
- [ ] I have added or updated unit/integration tests
- [ ] All new and existing tests pass locally
- [ ] I have commented complex or non-obvious areas of the code
- [ ] I have added appropriate metrics/logs and will create alerts if required
- [ ] My code does not send any PII data in logs
- [ ] I have updated documentation as needed
- [ ] I have added a feature flag if this needs to be toggled across markets
- [ ] I have updated downstream dependencies if needed (e.g. SDKs, Postman, configs)
- [ ] Performed a self-review of my own code
- [ ] Added labels to test cases covered under this PR: `Automated_QA`
- [ ] Run all related tests involved with my code changes
- [ ] Removed all unnecessary comments and logs
- [ ] Checked that PR and Ticket have the same CBA number
- [ ] Removed any unused or duplicate code; reused functions for repeated patterns
- [ ] Added tests in the correct folder
- [ ] Checked that the covered test case runs in both QA and PROD environments
- [ ] Copilot used to create unit test cases (if applicable)
- [ ] Copilot used to generate code snippets (if applicable)
- [ ] Copilot used to generate documentation (if applicable)
- [ ] [Your QA Tool] was used for QA Automation (if applicable)
- [ ] I have added/updated LaunchDarkly feature flags in this PR (if applicable)
- [ ] Observability: metrics, dashboards, monitors

---

### Anything else we should know?
<!-- Any additional context, caveats, or follow-up work. -->
```

---

## Filled Example

```markdown
### Jira Ticket Number
[TICKET-1234](https://your-org.atlassian.net/browse/TICKET-1234)

---

### Type of Change

- [x] Bug fix (non-breaking change that fixes an issue)
- [x] New feature (non-breaking change that adds functionality)

---

### Context

1. Restructured RulesError response in the middleware to separate concerns — `details` now only contains `ruleEvaluation`, while `balance`, `pointsEarned` and `pointsRedeemed` are moved to a new top-level `preview` field.
2. Updated `LoyaltyApiError` class and `ILoyaltyApiError` interface to support the new optional `preview` property, and updated `remapEngineError` to pass `preview` through from `parseEngineError`.
3. Updated the error middleware to conditionally include `preview` in the HTTP response payload only when it exists, with no impact on other error types.
4. Added test coverage across `parsers.spec.ts`, `loyalty.errors.spec.ts`, and `error-handling.spec.ts`.

**Before:**
`details` contained `ruleEvaluation`, `balance`, `pointsEarned`, and `pointsRedeemed` mixed together.

**After:**
`details` only contains `ruleEvaluation`; balance fields are in a separate `preview` top-level field.

---

### Architecture Document (if applicable)
N/A

---

### Evidence / Screenshots / Test Artifacts

| Before | After |
| ------ | ----- |
| ![before](url) | ![after](url) |

---

### Postman Collection / SDK Update (if applicable)

- [x] Bump or update a relevant SDK if the change impacts a shared client library

---

### How Has This Been Tested?

- [x] Unit tests added / updated and passing
- [x] Manually tested locally

---

### Checklist

- [x] My code follows the project's coding and PR guidelines
- [x] I have added or updated unit/integration tests
- [x] All new and existing tests pass locally
- [x] I have commented complex or non-obvious areas of the code
- [x] I have added appropriate metrics/logs and will create alerts if required
- [x] My code does not send any PII data in logs
- [x] I have updated documentation as needed
- [x] I have added a feature flag if this needs to be toggled across markets
- [x] I have updated downstream dependencies if needed (e.g. SDKs, Postman, configs)
- [x] Performed a self-review of my own code
- [ ] Added labels to test cases covered under this PR: `Automated_QA`
- [x] Run all related tests involved with my code changes
- [x] Removed all unnecessary comments and logs
- [x] Checked that PR and Ticket have the same CBA number
- [x] Removed any unused or duplicate code
- [x] Added tests in the correct folder
- [x] Checked that the covered test case runs in both QA and PROD environments
- [ ] Copilot used to create unit test cases
- [ ] Copilot used to generate code snippets
- [ ] Copilot used to generate documentation
- [ ] [Your QA Tool] was used for QA Automation
- [ ] I have added/updated LaunchDarkly feature flags in this PR
- [x] Observability: metrics, dashboards, monitors

---

### Anything else we should know?
N/A
```
