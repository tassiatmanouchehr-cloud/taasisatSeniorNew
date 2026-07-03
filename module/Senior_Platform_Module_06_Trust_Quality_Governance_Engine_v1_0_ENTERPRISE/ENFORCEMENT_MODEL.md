# Module 06 — Enforcement Model v1.0

## Principle

Decision without Enforcement is only an opinion.  
Enforcement without Decision is unsafe.

## EnforcementAction

Fields:
- id
- trust_case_id
- case_decision_id
- action_type
- target_type
- target_id
- scope
- starts_at
- ends_at
- status
- reason
- created_by
- approved_by
- metadata

## Action Types

- warning
- restriction
- suspension
- permanent_ban
- review_action
- payout_hold_request
- compliance_requirement
- quality_inspection
- risk_watchlist

## Warning

Warning does not restrict access. It creates history and education/notice.

## Restriction

Restriction must define restricted capability:
- receive_new_booking
- accept_assignment
- create_review
- withdraw_balance
- upload_document
- contact_customer
- access_dashboard

## Suspension

Suspension temporarily or indefinitely removes a party from marketplace participation. It does not delete account data.

## Permanent Ban

PermanentBan is the strongest enforcement and requires Platform Owner approval.

## Financial Enforcement Request

Module 06 may create:
- payout_hold
- refund_recommendation
- adjustment_recommendation
- wallet_freeze_request

Execution belongs to Module 05.

## Rules

ER-06-001 — EnforcementAction requires CaseDecision.  
ER-06-002 — EnforcementAction requires target, scope, reason, starts_at and status.  
ER-06-003 — Restriction must specify capability.  
ER-06-004 — Suspension must not delete historical data.  
ER-06-005 — PermanentBan requires strongest approval and audit.  
ER-06-006 — Financial enforcement is delegated to Module 05.  
ER-06-007 — Timed enforcement requires expires_at or lift_condition.  
ER-06-008 — Lift, cancel or extend must produce independent event and audit.
