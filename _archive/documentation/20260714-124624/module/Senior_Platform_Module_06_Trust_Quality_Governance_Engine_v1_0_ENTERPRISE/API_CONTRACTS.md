# Module 06 — API Contracts v1.0

## Review APIs
- POST /reviews
- GET /reviews/{id}
- PATCH /reviews/{id}
- POST /reviews/{id}/submit
- POST /reviews/{id}/dispute
- POST /reviews/{id}/hide
- POST /reviews/{id}/remove
- POST /reviews/{id}/restore

## Trust Case APIs
- POST /trust-cases
- GET /trust-cases
- GET /trust-cases/{id}
- POST /trust-cases/{id}/assign
- POST /trust-cases/{id}/add-evidence
- POST /trust-cases/{id}/escalate
- POST /trust-cases/{id}/resolve
- POST /trust-cases/{id}/close
- POST /trust-cases/{id}/reopen

## Complaint APIs
- POST /complaints
- GET /complaints/{id}
- POST /complaints/{id}/evidence
- POST /complaints/{id}/resolve
- POST /complaints/{id}/reject
- POST /complaints/{id}/close

## Dispute APIs
- POST /disputes
- GET /disputes/{id}
- POST /disputes/{id}/evidence
- POST /disputes/{id}/assign-mediator
- POST /disputes/{id}/decision
- POST /disputes/{id}/appeal
- POST /disputes/{id}/close

## Decision APIs
- POST /decision-recommendations
- GET /decision-recommendations/{id}
- POST /decision-recommendations/{id}/approve
- POST /decision-recommendations/{id}/reject
- POST /case-decisions
- GET /case-decisions/{id}

## Enforcement APIs
- POST /warnings
- POST /restrictions
- POST /suspensions
- POST /permanent-bans
- POST /enforcement-actions/{id}/lift
- POST /enforcement-actions/{id}/extend
- POST /enforcement-actions/{id}/cancel

## Compliance APIs
- POST /compliance-records
- GET /compliance-records/{id}
- POST /compliance-records/{id}/upload-document
- POST /compliance-records/{id}/verify
- POST /compliance-records/{id}/reject
- POST /compliance-records/{id}/revoke

## Risk APIs
- POST /risk-signals
- GET /risk-signals
- POST /risk-cases
- GET /risk-cases/{id}
- POST /risk-cases/{id}/dismiss
- POST /risk-cases/{id}/escalate
- POST /risk-cases/{id}/close

## Appeal APIs
- POST /appeals
- GET /appeals/{id}
- POST /appeals/{id}/add-evidence
- POST /appeals/{id}/approve
- POST /appeals/{id}/partial-approve
- POST /appeals/{id}/reject
- POST /appeals/{id}/close

## Reporting APIs
- GET /reports/trust-dashboard
- GET /reports/review-reputation
- GET /reports/complaints
- GET /reports/disputes
- GET /reports/compliance
- GET /reports/risk
- GET /reports/enforcement
- GET /reports/marketplace-health
