# Enterprise Architecture Specification

## Bounded Context
Module 11 owns policies, campaigns, referral relationships, incentive evaluations, reward state, promotion application, commission adjustment policies, fraud decision inputs related to incentive abuse, and settlement eligibility for incentives.

It does not own orders, users, payments, wallets, search, maps, messaging, or dispute adjudication. It consumes authoritative state from other modules and emits decisions and events.

## Architectural Style
- Event-driven
- Policy-driven
- Versioned rule evaluation
- Multi-tenant isolated
- Ledger-integrated
- Audit-first
- Explainability-first
- Extensible reward types

## Core Services
- ReferralRegistrationService
- ReferralValidationService
- CampaignManagementService
- PolicyEvaluationService
- EligibilityService
- RewardLifecycleService
- PromotionApplicationService
- CommissionPolicyService
- IncentiveFraudRiskService
- SettlementQualificationService
- RewardReversalService
- IncentiveAuditService
- IncentiveReportingService

## Storage Principles
Policies are immutable after publication. A new business rule creates a new policy version. Historical evaluations must retain the policy version, input snapshot hash, output decision, reason codes, and actor context.

## Runtime Evaluation Flow
1. Receive event or API request.
2. Resolve tenant and actor context.
3. Load active campaigns and policy versions.
4. Check global and tenant configuration.
5. Evaluate eligibility predicates.
6. Run conflict and stacking rules.
7. Create evaluation record.
8. Create or update reward/promotion/commission effect.
9. Emit CES events.
10. Defer financial posting until settlement criteria are satisfied.
