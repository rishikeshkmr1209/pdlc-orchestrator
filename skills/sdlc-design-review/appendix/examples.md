# Design Review Skill — Examples & Output Templates

This file contains example findings and output format details for the sdlc-design-review skill.
Read this file only if you need format guidance for producing `ph3_design_review.md`.

---

## Dimension C: Assumption Challenge Example

```markdown
### ASM-001

- **Assumption:** Users will have < 50 favorites on average
- **Challenge:** No data supports this. Power users may have 200+.
- **Likelihood of being wrong:** medium
- **Impact if wrong:** high
- **Evidence:** No user research or analytics cited
- **Recommendation:** Design for pagination from day 1
- **Validation strategy:** Add analytics to track favorites count distribution
- **Fallback plan:** If > 100 common, implement virtual scrolling
- **Blocking:** no
```

**Blocking rule**: `impact_if_wrong: critical` with no adequate mitigation is blocking.

---

## Output Format Field Descriptions

### meta

`feature_id` (from ticket), `created_at` (ISO 8601), `review_type` ("design_review"),
`design_spec_version`, `reviewer` ("sdlc-design-review"), `review_mode` ("pure_design" |
"retroactive_with_codebase"), `codebase_reviewed` (boolean), `codebase_location` (Mode B).

### summary

`overall_assessment`, `confidence_score` (0-100), `critical_issues` (count),
`major_concerns` (count), `minor_suggestions` (count), `recommendation` (string).

### sign_off

`ready_for_implementation` (boolean), `blocking_issues` (list of strings),
`recommended_actions` (list of strings), `estimated_refinement_time`,
`next_review_needed` (boolean), `caveat` (optional string).

### positive_aspects

Always include at least two positive observations. Acknowledge what the architect did well.

### review_history

If re-reviewing (previous `ph3_design_review.md` exists), document version history with
date, assessment, and key changes per version. Always overwrite the file -- never create
versioned copies like `design_review_v2.md`.
