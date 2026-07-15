# CURRENT IMPLEMENTATION STATE

**Last verified HEAD:** phase1-activation-completion-final (from main @ 860640e)
**Last verified date:** 2026-07-15

---

## Per-App Implementation Status

| App | Models | Services | Views | Tests | Status |
|-----|--------|----------|-------|-------|--------|
| **kernel** | 14 (Tenant, Person, UserAccount, Role, Permission, RoleAssignment, EventOutbox, AuditLog, ConfigurationKey, ConfigurationValue, FeatureFlag, PolicyDefinition, PolicyVersion, ServiceSupplier) | 11 | API: 1 | 232 | COMPLETE |
| **accounts** | 10 (OTPChallenge, CustomerProfile, ElderProfile, TrustedContact, CaregiverProfile, OrganizationProfile, OrganizationMembership, CompanyAffiliationRequest, PlatformTeamMember, VerificationDocument) | 24 (+VerificationReviewService, RequiredDocumentPolicy, ProfileVerificationRollupService, ActivationEligibilityService, document_ownership helpers — Phase 1.1/1.2; +ProfileCompletionService, ProfileActivationService — Phase 1.3) | 9 | 279 (+25 Phase 1.1, +47 Phase 1.2, +27 Phase 1.3) | COMPLETE (manual document verification + roll-up/activation rules + controlled activation added) |
| **orders** | 7 (ServiceCategory, ServiceType, Order, OrderStatusHistory, OrderShareLink, OrderOffer, OrderOrganizationEligibility) | 7 | 0 | 167 (incl. 40 OrderOffer + 8 BG-002) | COMPLETE (Offer Phase 1 committed in ce3b30e; BG-002 fix merged in eb51018) |
| **booking** | 1 (SupplierAssignment) | 5 | 0 | 67 | COMPLETE |
| **execution** | 1 (ExecutionSession) | 3 | 0 | 58 | COMPLETE |
| **matching** | 2 (MatchRound, MatchCandidate) | 4 | 0 | 33 | COMPLETE |
| **availability** | 3 (ProviderWorkingWindow, AvailabilityBlockedPeriod, CapacityRule) | 3 | 0 | 37 | COMPLETE |
| **finance** | 11 (FinancialParty, FinancialDocument, FinancialDocumentItem, FinancialObligation, PaymentTransaction, WalletAccount, WalletTransaction, EscrowRecord, EscrowMovement, LedgerEntry, SettlementBatch, SettlementItem) | 9+ | 0 | 75 | COMPLETE |
| **payments** | 3 (PaymentIntent, PaymentAttempt, PaymentCallback) | 7 | 0 | 54 | PARTIAL (fake PSP only) |
| **commission** | 11 (CommissionContract, PaymentDeadline, PaymentDeadlineExtension, CommissionSnapshot, ObjectionPeriod, ObjectionPeriodExtension, Dispute, DisputeLine, DisputeResolution, ReleaseInstruction, RefundInstruction) | 22 | 0 | 132 | COMPLETE |
| **pricing** | 6 (PricingRule, Quote, QuoteLine, Promotion, PromotionCondition, PromotionEffect) | 2 | 0 | 69 | COMPLETE |
| **wallet** | 3 (Wallet, WalletTransaction, WalletBalanceSnapshot) | 2 | 0 | 34 | COMPLETE |
| **reviews** | 3 (Review, ReviewRating, ReputationSnapshot) | 3 | 0 | 33 | COMPLETE |
| **notifications** | 2 (Notification, NotificationDeliveryAttempt) | 3 | 0 | 53 | PARTIAL (fake providers) |
| **discovery** | 0 | 6 | 0 | 42 | COMPLETE |
| **reporting** | 0 (DTOs only) | 5 | 0 | 37 | COMPLETE |
| **jobs** | 2 (JobDefinition, JobRun) | 1 | 0 | 35 | COMPLETE |
| **common** | 3 (abstract: TimestampedModel, TenantAwareModel, SoftDeleteMixin) | 0 | 0 | 0 | COMPLETE (no tests) |
| **portal** | 0 | 5 (presentation) | 30+ | 74 | COMPLETE |
| **provider_portal** | 0 | 1 (presentation) | 21 | 55 (+2 Phase 1.3) | COMPLETE |
| **organization_portal** | 0 | 1 (presentation) | 18 | 51 (+2 Phase 1.3) | COMPLETE |
| **admin_portal** | 0 | 0 | 20 (+4 document verification Phase 1.1, +4 activation Phase 1.3) | 54 (+16 Phase 1.1, +9 Phase 1.3) | COMPLETE |
| **api** | 0 | 0 | 12 | 97 | COMPLETE |
| **public_site** | 0 | 4 | 18 | 80 | COMPLETE |
| **showcase** | 0 | 0 | 15 | 0 | COMPLETE (no tests) |

## Offer Marketplace Current State

Phase 1 (domain model) is COMMITTED in `ce3b30e`:

- `OrderOffer` model: 7 lifecycle states, UUID PK, tenant/order/supplier FKs
- Constraints: unconditional `(order, supplier)` uniqueness + conditional one-selected-per-order
- Properties: can_edit, can_withdraw, can_select
- 40 unit tests
- Single migration: `orders/0008_orderoffer.py` (applies cleanly — verified by `manage.py migrate` on PostgreSQL 16)
- Admin: OrderOfferAdmin registered

OrderOfferService is NOT started — it is scheduled as roadmap Phase 5
(see `project docs/IMPLEMENTATION_ROADMAP.md`), after registration,
profiles, and portal completion phases.

## Key Metrics

| Metric | Value |
|--------|-------|
| Total Django apps | 25 + 1 config |
| Total concrete models | ~70 |
| Total migrations | ~45 |
| Total test files | 201 |
| Total test methods | 1,808 (full regression 1808/1808 green on phase1-activation-completion-final) |
| Total admin registrations | 20 |
| Total management commands | 15 |
| Total URL patterns | ~150 |
| Total Celery tasks | 4 |
| Total job handlers | 7 |
