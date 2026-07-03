# Module 06 — Appeal & Reopen Model v1.0

## Principle

Decision is not final truth. It is the best conclusion based on current evidence.

## Difference

Appeal:
Objection to a decision.

Reopen:
Reopening a closed case because new evidence, error, fraud discovery or legal reason exists.

## Appeal

Fields:
- id
- trust_case_id
- related_case_decision_id
- related_enforcement_action_id
- appellant_type
- appellant_id
- appeal_reason
- appeal_category
- evidence_summary
- status
- reviewer_id
- decision
- created_at
- reviewed_at
- closed_at

## Appeal Status

```text
draft
→ submitted
→ accepted_for_review
→ under_review
→ need_more_evidence / decision_ready
→ approved / partially_approved / rejected
→ closed
```

## Appeal Decisions

- No Change
- Reduce Penalty
- Lift Restriction
- Lift Suspension
- Restore Review
- Refund Recommended
- Reopen Case
- Escalate
- Dismiss Appeal

## CaseReopenRequest

Fields:
- id
- trust_case_id
- requester_type
- requester_id
- reopen_reason
- new_evidence
- approval_required
- status
- approved_by
- created_at

## Lineage over Mutation

Decision, Evidence, Enforcement and Appeal must not be overwritten.  
New records must reference previous records.
