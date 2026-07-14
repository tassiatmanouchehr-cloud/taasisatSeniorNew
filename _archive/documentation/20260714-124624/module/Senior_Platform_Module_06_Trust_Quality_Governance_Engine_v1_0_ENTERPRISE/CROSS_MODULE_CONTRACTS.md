# Module 06 — Cross-Module Contracts v1.0

## Module 01 — Request Engine

Consumes:
- RequestCreated
- RequestCancelled
- RequestAbuseReported

Produces:
- CustomerRestricted
- RiskSignalGenerated
- ComplaintOpened

## Module 02 — Matching Engine

Consumes:
- MatchGenerated
- ProviderRanked
- ProviderRejected
- MatchingRepeated

Produces:
- AccountHealthChanged
- RiskScoreUpdated
- ProviderRestricted
- ProviderSuspended
- ComplianceExpired

Contract:
Matching must exclude or downgrade suspended, restricted or non-compliant providers.

## Module 03 — Booking & Assignment Engine

Consumes:
- BookingCreated
- BookingAssigned
- AssignmentChanged
- BookingCancelled
- NoShowDetected

Produces:
- RestrictionApplied
- SuspensionStarted
- ComplaintOpened
- ViolationDetected

Contract:
Repeated cancellations, suspicious assignment changes or no-show events may create RiskSignal or ViolationCase.

## Module 04 — Service Execution Engine

Consumes:
- ServiceStarted
- ServiceCompleted
- ServiceFailed
- LateArrivalDetected
- QualityIssueReported

Produces:
- QualityCaseOpened
- ComplaintOpened
- ViolationConfirmed
- QualityInspectionRequested

Contract:
Execution quality issues must be linked to TrustCase.

## Module 05 — Financial Operations Engine

Consumes:
- PaymentReceived
- RefundRequested
- PayoutRequested
- WalletAdjusted
- FinancialDisputeRaised

Produces:
- RefundRecommended
- PayoutHoldRequested
- WalletFreezeRequested
- FraudConfirmed

Contract:
Module 06 never moves money. It only recommends or requests financial control. Module 05 executes financial operations.
