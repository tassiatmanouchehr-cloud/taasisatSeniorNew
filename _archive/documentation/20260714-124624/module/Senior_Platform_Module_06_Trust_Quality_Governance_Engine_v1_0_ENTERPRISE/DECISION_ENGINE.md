# Module 06 — Decision Engine v1.0

## Principle

Decision Engine recommends; it does not punish.

```text
Decision Engine → recommendation
Governance Engine → approval
Enforcement Engine → execution
Audit → record
```

## Flow

```text
Signal
→ TrustCase
→ Evidence Aggregation
→ Policy Evaluation
→ Risk Evaluation
→ DecisionRecommendation
→ Human Approval / Auto Approval
→ CaseDecision
→ EnforcementAction
```

## DecisionRecommendation

Fields:
- id
- trust_case_id
- recommendation_type
- confidence_score
- severity
- generated_by
- evidence_summary
- policy_rules_matched
- risk_signals_used
- recommended_action
- requires_human_approval
- approval_level_required
- expires_at
- status
- created_at

## Recommendation Types

- NoAction
- NeedMoreEvidence
- NeedHumanReview
- RecommendWarning
- RecommendRestriction
- RecommendSuspension
- RecommendPermanentBan
- RecommendRefund
- RecommendPayoutHold
- RecommendReviewRemoval
- RecommendComplianceVerification
- RecommendQualityInspection
- RecommendRiskWatchlist

## Rules

DR-06-001 — Recommendation requires TrustCase.  
DR-06-002 — Recommendation requires Evidence Summary.  
DR-06-003 — Critical recommendation requires human review unless auto safety lock applies.  
DR-06-004 — Financial recommendation is sent to Module 05.  
DR-06-005 — Suspension or Ban recommendation must support appeal.  
DR-06-006 — Policy versions used must be stored.  
DR-06-007 — Insufficient evidence must produce NeedMoreEvidence.  
DR-06-008 — Rule/Risk conflict produces NeedHumanReview.
