# Requirements Skill — Evaluation Table

Use this table for testing skill trigger behavior. Not needed during normal operation.

| Scenario | Input | Expected behavior |
|----------|-------|-------------------|
| Trigger - positive | "analyze requirements for this feature" | Skill activates, enters interrogation |
| Trigger - positive | "what should we build for TICKET-1234?" | Skill activates, asks for feature description |
| Trigger - positive | "decompose this feature request" | Skill activates |
| Trigger - negative | "review this code" | Skill does NOT activate (code-review handles this) |
| Vague request | "Add login" | Produces clarification questions with 5+ questions |
| Detailed request | Full spec covering all categories | Produces ph1_problem_spec.md directly |
| Missing ticket | No --ticket argument | Asks user for Jira ticket ID before proceeding |
| project-specific gap | Feature mentions "the app" without brand | Asks which brands are in scope |
| PII detected | Feature involves user email display | Asks about GDPR, consent, logging restrictions |
| Quality gate fail | Spec with 0 non-goals | Adds non-goals before finalizing |
| Format validation | Output produced | Validates required Markdown section headers are present |
| Breaking change | Feature removes existing API field | Warns user in plain text, presents accept/mitigate/defer options |
| No breaking change | Feature adds new optional field | States "No breaking changes" in draft plan, proceeds normally |
