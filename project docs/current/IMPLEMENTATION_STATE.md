# CURRENT IMPLEMENTATION STATE

**Last verified HEAD:** phase2-caregiver-professional-dashboard (from main @ 125dd3b, PR #9 merged)
**Last verified date:** 2026-07-15

---

## Per-App Implementation Status

| App | Models | Services | Views | Tests | Status |
|-----|--------|----------|-------|-------|--------|
| **kernel** | 14 (Tenant, Person, UserAccount, Role, Permission, RoleAssignment, EventOutbox, AuditLog, ConfigurationKey, ConfigurationValue, FeatureFlag, PolicyDefinition, PolicyVersion, ServiceSupplier) | 11 | API: 1 | 232 | COMPLETE |
| **accounts** | 13 (OTPChallenge, CustomerProfile, ElderProfile, TrustedContact, CaregiverProfile, OrganizationProfile, OrganizationMembership, CompanyAffiliationRequest, PlatformTeamMember, VerificationDocument, CaregiverSkill, CaregiverExperience — Phase 2.1, CaregiverGalleryItem — Sprint 2.2) | 27 (+VerificationReviewService, RequiredDocumentPolicy, ProfileVerificationRollupService, ActivationEligibilityService, document_ownership helpers — Phase 1.1/1.2; +ProfileCompletionService, ProfileActivationService — Phase 1.3; +CaregiverSkillService, CaregiverExperienceService, PublicCredentialSelector — Phase 2.1; +CaregiverGalleryService, image_validation.validate_image() — Sprint 2.2; +CaregiverSkillService.toggle_visibility(), RequiredDocumentPolicy.is_expiring_soon() — Sprint 2.3) | 9 | 368 (+25 Phase 1.1, +47 Phase 1.2, +27 Phase 1.3, +14 Phase 1.3 remediation, +24 Phase 2.1, +21 Sprint 2.2, +14 Sprint 2.3) | COMPLETE (manual document verification + roll-up/activation rules + controlled activation + skills/experience/credential-summary + gallery/media portfolio + professional credibility layer added; profile.status is now the activation-state source of truth) |
| **orders** | 7 (ServiceCategory, ServiceType, Order, OrderStatusHistory, OrderShareLink, OrderOffer, OrderOrganizationEligibility) | 7 (+list_for_supplier()/count_by_status_for_supplier() on OrderQueryService — Sprint 2.5) | 0 | 175 (incl. 40 OrderOffer + 8 BG-002 + 8 Sprint 2.5) | COMPLETE (Offer Phase 1 committed in ce3b30e; BG-002 fix merged in eb51018) |
| **booking** | 1 (SupplierAssignment) | 5 | 0 | 67 | COMPLETE |
| **execution** | 1 (ExecutionSession) | 3 | 0 | 58 | COMPLETE |
| **matching** | 2 (MatchRound, MatchCandidate) | 4 | 0 | 33 | COMPLETE |
| **availability** | 3 (ProviderWorkingWindow, AvailabilityBlockedPeriod, CapacityRule) | 3 (+evaluate()/get_distinct_active_days() on AvailabilityQueryService, overlap/duplicate refusal + toggle_working_window() on AvailabilityMutationService — Sprint 2.4; supplier-row locking — PR #9 concurrency remediation) | 0 | 65 (+19 Sprint 2.4, +9 PR #9 concurrency remediation) | COMPLETE |
| **finance** | 11 (FinancialParty, FinancialDocument, FinancialDocumentItem, FinancialObligation, PaymentTransaction, WalletAccount, WalletTransaction, EscrowRecord, EscrowMovement, LedgerEntry, SettlementBatch, SettlementItem) | 9+ (+list_for_beneficiary_party()/count_by_status_for_beneficiary_party() on FinancialDocumentService — Sprint 2.5) | 0 | 81 (+6 Sprint 2.5) | COMPLETE |
| **payments** | 3 (PaymentIntent, PaymentAttempt, PaymentCallback) | 7 | 0 | 54 | PARTIAL (fake PSP only) |
| **commission** | 11 (CommissionContract, PaymentDeadline, PaymentDeadlineExtension, CommissionSnapshot, ObjectionPeriod, ObjectionPeriodExtension, Dispute, DisputeLine, DisputeResolution, ReleaseInstruction, RefundInstruction) | 22 | 0 | 132 | COMPLETE |
| **pricing** | 6 (PricingRule, Quote, QuoteLine, Promotion, PromotionCondition, PromotionEffect) | 2 | 0 | 69 | COMPLETE |
| **wallet** | 3 (Wallet, WalletTransaction, WalletBalanceSnapshot) | 2 | 0 | 34 | COMPLETE |
| **reviews** | 3 (Review, ReviewRating, ReputationSnapshot) | 3 (+list_recent_reviews_with_reviewer_names() on ReputationService — Sprint 2.5) | 0 | 39 (+6 Sprint 2.5) | COMPLETE |
| **notifications** | 2 (Notification, NotificationDeliveryAttempt) | 3 | 0 | 53 | PARTIAL (fake providers) |
| **discovery** | 0 | 6 | 0 | 42 | COMPLETE |
| **reporting** | 0 (DTOs only) | 5 | 0 | 37 | COMPLETE |
| **jobs** | 2 (JobDefinition, JobRun) | 1 | 0 | 35 | COMPLETE |
| **common** | 3 (abstract: TimestampedModel, TenantAwareModel, SoftDeleteMixin) | 0 | 0 | 0 | COMPLETE (no tests) |
| **portal** | 0 | 5 (presentation) | 30+ | 74 | COMPLETE |
| **provider_portal** | 0 | 2 (presentation — profile_service.py, +dashboard_service.py Sprint 2.5) | 33 (+5 skills/experience management Phase 2.1, +4 gallery management Sprint 2.2, +1 skill-visibility-toggle Sprint 2.3, +2 working-window update/toggle Sprint 2.4; dashboard_view extended, not new, Sprint 2.5) | 131 (+2 Phase 1.3, +13 Phase 2.1, +13 Sprint 2.2, +11 Sprint 2.3, +15 Sprint 2.4, +24 Sprint 2.5) | COMPLETE |
| **organization_portal** | 0 | 1 (presentation) | 18 | 51 (+2 Phase 1.3) | COMPLETE |
| **admin_portal** | 0 | 0 | 20 (+4 document verification Phase 1.1, +4 activation Phase 1.3) | 56 (+16 Phase 1.1, +9 Phase 1.3, +2 Phase 1.3 remediation) | COMPLETE |
| **api** | 0 | 0 | 12 | 97 | COMPLETE |
| **public_site** | 0 | 4 | 18 | 139 (+2 Phase 2.1 eligibility, +11 Phase 2.1 skills/experience/credentials, +13 BG-022 canonical visibility, +11 Sprint 2.2 gallery, +11 Sprint 2.3 highlights/badges, +6 Sprint 2.4 schedule summary, +5 Sprint 2.6 Phase 2 acceptance) | COMPLETE (Sprint 2.6 — public profile finalization: SEO/accessibility fixes, redundant-badge removal, query-count measurement, Phase 2 E2E acceptance tests; Phase 2 acceptance criteria satisfied) |
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
| Total concrete models | ~73 (+CaregiverSkill, CaregiverExperience — Phase 2.1; +CaregiverGalleryItem — Sprint 2.2) |
| Total migrations | ~47 |
| Total test files | 213 (+1 `apps.availability.tests.test_concurrency` — PR #9 remediation; +3 `apps.orders.tests.test_supplier_queries`/`apps.finance.tests.test_beneficiary_queries`/`apps.provider_portal.tests.test_professional_dashboard` — Sprint 2.5; +1 `apps.public_site.tests.test_phase2_acceptance` — Sprint 2.6) |
| Total test methods | 2,082 (full regression 2082/2082 green on phase2-caregiver-public-profile-finalization) |
| Total admin registrations | 20 |
| Total management commands | 15 |
| Total URL patterns | ~157 |
| Total Celery tasks | 4 |
| Total job handlers | 7 |
