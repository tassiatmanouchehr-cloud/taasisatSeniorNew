# Domain Model Specification

## Aggregates

### Campaign
Represents a business initiative containing one or more policy versions.
Fields: tenant_id, campaign_id, name, type, status, start_at, end_at, budget_limits, priority, stacking_mode, targeting_scope, created_by, published_by.

### IncentivePolicy
Immutable versioned rule set that defines eligibility, reward calculation, lifecycle triggers, settlement criteria, reversal criteria, and fraud gates.

### ReferralRelationship
Represents inviter/invitee linkage. It may be created by code, link, QR, manual admin assignment, external import, or partner integration.

### Reward
Represents a potential or realized benefit. Reward is never directly money until Module 05 posts ledger entries.

### PromotionApplication
Represents a discount or benefit applied to a request, booking, order, invoice, commission calculation, subscription, search exposure, or feature entitlement.

### CommissionAdjustment
Represents a policy-derived change to platform commission calculation.

### IncentiveEvaluation
Append-only explainability record containing inputs, policy version, decision, reason codes, result, conflicts, fraud score, and output effects.

## Key Entity States
Campaign: draft, scheduled, active, paused, expired, archived, cancelled.
Policy: draft, published, superseded, retired.
Reward: draft, pending, qualified, approved, locked, earned, payable, paid, expired, cancelled, reversed.
Referral: pending, accepted, locked, expired, rejected, invalidated.
PromotionApplication: proposed, applied, consumed, expired, removed, reversed.
