# Module 06 — Domain Model v1.0

## Core Aggregate

```text
TrustCase
├── ComplaintCase
├── DisputeCase
├── ViolationCase
├── RiskCase
├── ComplianceCase
└── QualityCase
```

## Core Entities

```text
TrustCase
Review
Rating
ReputationProfile
TrustScore
Evidence
CaseNote
DecisionRecommendation
CaseDecision
EnforcementAction
Warning
Restriction
Suspension
PermanentBan
Appeal
CaseReopenRequest
ComplianceRecord
VerificationDocument
RiskSignal
RiskAssessment
QualityInspection
MarketplaceHealthMetric
AuditRecord
```

## TrustCase

Fields:
- id
- case_type
- subject_type
- subject_id
- reporter_type
- reporter_id
- accused_party_type
- accused_party_id
- related_booking_id
- related_payment_id
- severity
- priority
- status
- assigned_reviewer_id
- opened_at
- resolved_at
- closed_at
- metadata

Rule:
No Complaint, Dispute, Violation, Risk, Compliance or Quality issue may be managed outside TrustCase.

## Layer Separation

```text
Signal Layer:
Review, Rating, RiskSignal, Complaint, Evidence

Case Layer:
TrustCase, DisputeCase, ViolationCase, ComplianceCase

Decision Layer:
DecisionRecommendation, CaseDecision

Enforcement Layer:
Warning, Restriction, Suspension, PermanentBan
```

Rule:
Signal ≠ Case ≠ Decision ≠ Enforcement.
