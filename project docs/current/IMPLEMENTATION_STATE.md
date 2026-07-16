# CURRENT IMPLEMENTATION STATE

**Last verified HEAD:** main @ 078e435fee2b2c6350c66be113c4e7e607178763 (PR #12 merged — Sprint 3.1 CLOSED; PR #13 merged — Sprint 3.2 CLOSED; PR #14 merged — Sprint 3.3 CLOSED; PR #15 merged — **Phase 3 FORMALLY CLOSED**; Phase 4 Customer Portal Architecture Assessment complete (code-free, governance/readiness review, not a numbered sprint) — Customer Portal already substantially built under pre-existing Epic 07 work, one confirmed gap: Favorites, recommended as Phase 4 — Sprint 4.1: Customer Favorites and Saved Providers; **Phase 4 implementation has not started; Sprint 4.1 has not started**)
**Last verified date:** 2026-07-16 (Phase 3 formally closed via PR #15 merge; Phase 4 Customer Portal Architecture Assessment recorded)

---

## Per-App Implementation Status

| App | Models | Services | Views | Tests | Status |
|-----|--------|----------|-------|-------|--------|
| **kernel** | 14 (Tenant, Person, UserAccount, Role, Permission, RoleAssignment, EventOutbox, AuditLog, ConfigurationKey, ConfigurationValue, FeatureFlag, PolicyDefinition, PolicyVersion, ServiceSupplier) | 11 | API: 1 | 232 | COMPLETE |
| **accounts** | 13 (OTPChallenge, CustomerProfile, ElderProfile, TrustedContact, CaregiverProfile, OrganizationProfile — +headline Sprint 3.2, OrganizationMembership — +terminated_at/terminated_by/termination_reason Sprint 3.1, +closure_reason PR #12 remediation, CompanyAffiliationRequest, PlatformTeamMember, VerificationDocument, CaregiverSkill, CaregiverExperience — Phase 2.1, CaregiverGalleryItem — Sprint 2.2) | 28 (+VerificationReviewService, RequiredDocumentPolicy, ProfileVerificationRollupService, ActivationEligibilityService, document_ownership helpers — Phase 1.1/1.2; +ProfileCompletionService, ProfileActivationService — Phase 1.3; +CaregiverSkillService, CaregiverExperienceService, PublicCredentialSelector — Phase 2.1; +CaregiverGalleryService, image_validation.validate_image() — Sprint 2.2; +CaregiverSkillService.toggle_visibility(), RequiredDocumentPolicy.is_expiring_soon() — Sprint 2.3; `apps.accounts.services.affiliations` extended with 11 new functions + 6 read helpers — join-by-code, invitation, mutual termination — Sprint 3.1; PR #12 remediation: `approve_affiliation_request()`/`invite_caregiver()` changed from `update_or_create()` to always-`.create()`, `closure_reason` set on every terminal transition; Sprint 3.2: `OrganizationProfileUpdateService.update_profile()` gained `headline`, `ProfileMediaService`'s 4 organization media methods gained permission-gating (`actor` kwarg) and transaction-safe `_replace()`; Sprint 3.3: `OrganizationStaffService` gained `list_active_caregiver_counts_bulk()`, a batched counterpart of `list_active_caregivers().count()` for the public directory's per-page card rendering) | 9 | 405 (+25 Phase 1.1, +47 Phase 1.2, +27 Phase 1.3, +14 Phase 1.3 remediation, +24 Phase 2.1, +21 Sprint 2.2, +14 Sprint 2.3, +32 Sprint 3.1 `test_affiliation_lifecycle.py`, +5 PR #12 remediation; Sprint 3.3's `list_active_caregiver_counts_bulk()` is exercised indirectly by `apps.public_site`'s organization-directory tests, no new dedicated `apps.accounts` test file) | COMPLETE (manual document verification + roll-up/activation rules + controlled activation + skills/experience/credential-summary + gallery/media portfolio + professional credibility layer + full affiliation lifecycle, now with per-cycle history preservation, added; profile.status is now the activation-state source of truth) |
| **orders** | 7 (ServiceCategory, ServiceType, Order, OrderStatusHistory, OrderShareLink, OrderOffer, OrderOrganizationEligibility) | 7 (+list_for_supplier()/count_by_status_for_supplier() on OrderQueryService — Sprint 2.5) | 0 | 175 (incl. 40 OrderOffer + 8 BG-002 + 8 Sprint 2.5) | COMPLETE (Offer Phase 1 committed in ce3b30e; BG-002 fix merged in eb51018) |
| **booking** | 1 (SupplierAssignment) | 5 | 0 | 67 | COMPLETE |
| **execution** | 1 (ExecutionSession) | 3 | 0 | 58 | COMPLETE |
| **matching** | 2 (MatchRound, MatchCandidate) | 4 | 0 | 33 | COMPLETE |
| **availability** | 3 (ProviderWorkingWindow, AvailabilityBlockedPeriod, CapacityRule) | 3 (+evaluate()/get_distinct_active_days() on AvailabilityQueryService, overlap/duplicate refusal + toggle_working_window() on AvailabilityMutationService — Sprint 2.4; supplier-row locking — PR #9 concurrency remediation; +CapacityService.bulk_is_capacity_exceeded() — Sprint 2.6 PR #11 KL-012 remediation) | 0 | 65 (+19 Sprint 2.4, +9 PR #9 concurrency remediation) | COMPLETE |
| **finance** | 11 (FinancialParty, FinancialDocument, FinancialDocumentItem, FinancialObligation, PaymentTransaction, WalletAccount, WalletTransaction, EscrowRecord, EscrowMovement, LedgerEntry, SettlementBatch, SettlementItem) | 9+ (+list_for_beneficiary_party()/count_by_status_for_beneficiary_party() on FinancialDocumentService — Sprint 2.5) | 0 | 81 (+6 Sprint 2.5) | COMPLETE |
| **payments** | 3 (PaymentIntent, PaymentAttempt, PaymentCallback) | 7 | 0 | 54 | PARTIAL (fake PSP only) |
| **commission** | 11 (CommissionContract, PaymentDeadline, PaymentDeadlineExtension, CommissionSnapshot, ObjectionPeriod, ObjectionPeriodExtension, Dispute, DisputeLine, DisputeResolution, ReleaseInstruction, RefundInstruction) | 22 | 0 | 132 | COMPLETE |
| **pricing** | 6 (PricingRule, Quote, QuoteLine, Promotion, PromotionCondition, PromotionEffect) | 2 | 0 | 69 | COMPLETE |
| **wallet** | 3 (Wallet, WalletTransaction, WalletBalanceSnapshot) | 2 | 0 | 34 | COMPLETE |
| **reviews** | 3 (Review, ReviewRating, ReputationSnapshot) | 4 (+list_recent_reviews_with_reviewer_names() on ReputationService — Sprint 2.5; +get_reputation_summaries_bulk() — Sprint 2.6 PR #11 KL-012 remediation) | 0 | 39 (+6 Sprint 2.5) | COMPLETE |
| **notifications** | 2 (Notification, NotificationDeliveryAttempt) | 3 | 0 | 53 | PARTIAL (fake providers) |
| **discovery** | 0 | 6 (`SupplierSearchService._filter_by_city()` now batches its city filter via `resolve_supplier_entities_bulk()`, and `DiscoveryRankingService.rank()` now precomputes capacity via `CapacityService.bulk_is_capacity_exceeded()` instead of a per-candidate call — Sprint 2.6 PR #11 KL-012 remediation, no new service, existing services modified) | 0 | 42 | COMPLETE |
| **reporting** | 0 (DTOs only) | 5 | 0 | 37 | COMPLETE |
| **jobs** | 2 (JobDefinition, JobRun) | 1 | 0 | 35 | COMPLETE |
| **common** | 3 (abstract: TimestampedModel, TenantAwareModel, SoftDeleteMixin) | 0 | 0 | 0 | COMPLETE (no tests) |
| **portal** | 0 | 5 (presentation) | 30+ | 74 | COMPLETE |
| **provider_portal** | 0 | 2 (presentation — profile_service.py, +dashboard_service.py Sprint 2.5; nav items +"company" Sprint 3.1) | 39 (+5 skills/experience management Phase 2.1, +4 gallery management Sprint 2.2, +1 skill-visibility-toggle Sprint 2.3, +2 working-window update/toggle Sprint 2.4; dashboard_view extended, not new, Sprint 2.5; +6 company affiliation views Sprint 3.1) | 141 (+2 Phase 1.3, +13 Phase 2.1, +13 Sprint 2.2, +11 Sprint 2.3, +15 Sprint 2.4, +24 Sprint 2.5, +10 Sprint 3.1 `test_company_affiliation.py`) | COMPLETE |
| **organization_portal** | 0 | 1 (presentation — `OrganizationProfilePresentationService`/`OrganizationProfileFormViewModel` gained `headline` Sprint 3.2) | 23 (+5 affiliation-management views Sprint 3.1: invite, invitation-cancel, affiliation-request-approve, affiliation-request-reject, staff-terminate) | 66 (+2 Phase 1.3, +9 Sprint 3.1 `test_affiliation_management.py`, +6 Sprint 3.2 `test_profile.py`) | COMPLETE |
| **admin_portal** | 0 | 0 | 20 (+4 document verification Phase 1.1, +4 activation Phase 1.3) | 56 (+16 Phase 1.1, +9 Phase 1.3, +2 Phase 1.3 remediation) | COMPLETE |
| **api** | 0 | 0 | 12 | 97 | COMPLETE |
| **public_site** | 0 | 6 (+`_bulk_card_data()`/`rating_summaries_bulk()`/`completed_jobs_counts_bulk()` on directory_service.py/common.py — PR #11 KL-012 remediation; `OrganizationPublicProfileService.get_profile()` now uses the canonical `common.is_publicly_visible_attrs()` instead of a weaker local check, gained `headline`/`logo_url` — Sprint 3.2 + PR #13 remediation; **+`OrganizationDirectoryService` (new file, Sprint 3.3) — public Organization Directory, mirrors `CaregiverDirectoryService`'s architecture; `common.py` gained `parse_page()`/`build_pagination()`, extracted verbatim from `CaregiverDirectoryService`'s own former private methods, both directory services now call them as thin wrappers**) | 19 | 187 (+2 Phase 2.1 eligibility, +11 Phase 2.1 skills/experience/credentials, +13 BG-022 canonical visibility, +11 Sprint 2.2 gallery, +11 Sprint 2.3 highlights/badges, +6 Sprint 2.4 schedule summary, +5 Sprint 2.6 Phase 2 acceptance, +12 Sprint 2.6 PR #11 KL-012 remediation, +4 Sprint 3.2 organization-profile visibility/headline, +7 PR #13 remediation public logo, **+25 Sprint 3.3 — 18 `test_organization_directory_service.py` + 7 `test_views.py` `FindAnOrganizationViewTest`**) | COMPLETE (Sprint 2.6 — public profile finalization: SEO/accessibility fixes, redundant-badge removal, query-count measurement + PR #11 remediation resolving KL-012, Phase 2 E2E acceptance tests; Phase 2 acceptance criteria satisfied. **Sprint 3.3 — Company Public Directory and Discovery added and MERGED via PR #14; see ADM-025.**) |
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
| Total migrations | ~49 (+1 `accounts/0009_...` — PR #12 remediation: closure_reason field + conditional constraints; +1 `accounts/0010_organizationprofile_headline.py` — Sprint 3.2; Sprint 3.3 added no migration — no new model/field, confirmed by `makemigrations --check --dry-run`) |
| Total test files | 217 (+1 `apps.availability.tests.test_concurrency` — PR #9 remediation; +3 `apps.orders.tests.test_supplier_queries`/`apps.finance.tests.test_beneficiary_queries`/`apps.provider_portal.tests.test_professional_dashboard` — Sprint 2.5; +1 `apps.public_site.tests.test_phase2_acceptance` — Sprint 2.6, expanded in the PR #11 KL-012 remediation, no new file; +3 `apps.accounts.tests.test_affiliation_lifecycle`/`apps.organization_portal.tests.test_affiliation_management`/`apps.provider_portal.tests.test_company_affiliation` — Sprint 3.1; +1 `apps.public_site.tests.test_organization_directory_service` — Sprint 3.3) |
| Total test methods | 2,192 (2,167 baseline after PR #13 + 25 net from Sprint 3.3 — full regression run once and green, per this sprint's own policy: a cross-cutting refactor of shared `common.py` code paths used by three existing public_site services) |
| Total admin registrations | 20 |
| Total management commands | 15 |
| Total URL patterns | ~158 (+1 `find-an-organization/` list route — Sprint 3.3) |
| Total Celery tasks | 4 |
| Total job handlers | 7 |
