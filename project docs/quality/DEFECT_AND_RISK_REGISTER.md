# DEFECT AND RISK REGISTER

**Last verified HEAD:** a5dbaf28703142edaa1d770ea8f3c2a45a12640f (full sweep); re-evaluated for
Phase 3 closure approval / Phase 4 Customer Portal Architecture Assessment (a code-free
governance/readiness review, not a numbered sprint), recorded via PR #15 and **MERGED to
main @ `078e435fee2b2c6350c66be113c4e7e607178763`** (2026-07-16) — no new defect found;
KL-021 (already RESOLVED) confirmed accurate against the current template; KL-022
re-evaluated, still open, now explicitly scoped as cross-portal
infrastructure (see `traceability/ARCHITECTURE_DECISION_LOG.md` ADM-026); re-evaluated again
for the Phase 4 Closure Review (documentation-only, `main` @
`756c14dc25d9446eff73b209bfd85b3e0f4c6648`, 2026-07-17) — KL-022 remains open and does not
block Phase 4 closure; two new non-defect Sprint 4.1 engineering-improvement entries added
(KL-023, KL-024, see below), neither a Phase 4 closure blocker nor a Phase 5 prerequisite
(see `traceability/ARCHITECTURE_DECISION_LOG.md` ADM-028)
**Last verified date:** 2026-07-14 (full sweep); 2026-07-16 (targeted re-evaluation); 2026-07-17 (Phase 4 Closure Review)

---

## CRITICAL Findings

### FR-001: No Automated Tenant Isolation at ORM Level

**Severity:** CRITICAL
**Confidence:** HIGH
**Affected:** All apps
**Evidence:** `TenantScopedManager.for_tenant()` is opt-in, not default. `TenantAwareModel.tenant_id` is a UUIDField, not a ForeignKey. No middleware injects tenant_id.
**Runtime impact:** A single forgotten `tenant_id` parameter in a new service creates a cross-tenant data leak.
**Why it matters:** Multi-tenant isolation is the foundational security guarantee. Currently enforced only by developer discipline.
**Suggested action:** Consider middleware-based tenant injection or row-level security (PostgreSQL RLS).

### FR-002: RBAC Enforcement Can Be Disabled Per-Tenant

**Severity:** CRITICAL
**Confidence:** HIGH
**Affected:** All permission-gated operations
**Evidence:** `apps/kernel/services/permission_service.py:135` — if `RBACConfiguration.get_enforcement_enabled()` is False, `require()` returns immediately.
**Runtime impact:** Setting `rbac.enforcement.enabled=false` in ConfigurationValue table disables ALL RBAC for that tenant.
**Why it matters:** No audit alert when enforcement is toggled. A compromised config change silently bypasses all permissions.
**Suggested action:** Add audit logging when enforcement is toggled. Consider removing the toggle in production.

---

## HIGH Findings

### FR-003: ownership_authorized_by Bypass in PermissionService

**Severity:** HIGH
**Confidence:** HIGH
**Affected:** booking, execution, commission services
**Evidence:** `permission_service.py:157-188` — if `ownership_authorized_by` is set and actor has no RoleAssignment, authorization is granted. PermissionService trusts the caller.
**Runtime impact:** Any caller can bypass RBAC by passing `ownership_authorized_by`. Security depends on callers being correct.
**Why it matters:** Defense-in-depth violation. Service-level auth depends on caller integrity.

### FR-004: FakeProviderCallbackView Unauthenticated

**Severity:** HIGH
**Confidence:** HIGH
**Affected:** payments
**Evidence:** `api/views/payments.py:72-117` — no authentication. Queries `PaymentAttempt` by `provider_reference` without tenant scoping.
**Runtime impact:** Anyone with a valid `provider_reference` can trigger payment callbacks. Protected only by unguessable token.
**Why it matters:** Real PSP webhooks need signature verification. Currently mocked.

### FR-005: Pre-Existing Seed Test Random order_number Collision — **RESOLVED 2026-07-14**

**Severity:** HIGH (historical)
**Confidence:** HIGH (proven by repeated execution)
**Affected:** kernel/tests/test_seed_product_walkthrough.py (root cause in orders/models.py `_generate_order_number()`)
**Evidence:** 2026-07-14 verification at ce3b30e: failed 1/10 runs **in isolation** (duplicate `ORD-20260714-1003` within a single seed run) and 2 test classes in full regression (distinct colliding keys). The 4-digit random suffix collides randomly among same-day orders created by the seed walkthrough — an in-run birthday-problem collision, NOT an inter-test race as previously recorded.
**Runtime impact (historical):** Full regression exit code 1 intermittently; when `SeedProductWalkthroughDatasetTest.setUpClass` hit the collision, its 10 tests were skipped (e.g., 1662 of 1672 ran on 2026-07-14).
**Resolution:** BG-002 fix — bounded savepoint-wrapped retry in `Order.save()` (5 attempts, DB constraint remains the arbiter) + suffix widened to 6 digits. Regression tests in `orders/tests/test_order_number_generation.py`. Evidence: CHANGE_LEDGER CL-017, TEST_EXECUTION_LOG Run 009.

### FR-006: UserAccount Queries Not Tenant-Scoped

**Severity:** MEDIUM
**Confidence:** HIGH
**Affected:** accounts/views.py
**Evidence:** Lines 86, 124, 163, 241 — `UserAccount.objects.filter(phone=phone)` without tenant filter.
**Runtime impact:** Phone numbers are globally unique login identifiers. Cross-tenant coupling at auth layer.
**Why it matters:** Design decision, not bug. But means true multi-tenant auth isolation doesn't exist.

---

## MEDIUM Findings

### FR-007: SupplierRegistry Unscoped Queries

**Severity:** MEDIUM
**Confidence:** HIGH
**Affected:** kernel/services/supplier_registry.py
**Evidence:** `find_by_linked_entity()` at line 69-74 has no tenant filter.
**Runtime impact:** Caller must validate tenant independently.

### FR-008: No @login_required Anywhere

**Severity:** MEDIUM
**Confidence:** HIGH
**Affected:** All portal views
**Evidence:** Custom `require_authenticated()` in each portal module instead of Django's `@login_required`.
**Runtime impact:** No single enforcement point to audit. Each module maintains its own auth check.

### FR-009: TenantAwareModel.tenant_id Not a ForeignKey

**Severity:** MEDIUM
**Confidence:** HIGH
**Affected:** All business models
**Evidence:** `common/models.py:53` — `tenant_id = UUIDField(db_index=True)`, not FK to Tenant.
**Runtime impact:** No DB-level referential integrity. No CASCADE/PROTECT on tenant deletion.

### FR-010: Legacy Wallet Still in finance App

**Severity:** MEDIUM
**Confidence:** HIGH
**Affected:** finance/models/wallet.py
**Evidence:** `WalletAccount` and `WalletTransaction` exist in finance but are superseded by apps.wallet.
**Runtime impact:** Confusion for new developers. Potential for wrong-app usage.

---

## LOW Findings

### FR-011: common App Has Zero Tests

**Severity:** LOW
**Confidence:** HIGH
**Affected:** common (shared utilities)
**Evidence:** No test files in apps/common/
**Runtime impact:** Shared enums, managers, validators, and abstract models have no dedicated tests.

### FR-012: showcase App Has Zero Tests

**Severity:** LOW
**Confidence:** HIGH
**Affected:** showcase
**Evidence:** No test files in apps/showcase/
**Runtime impact:** UI component demos untested. Low risk since they render static content.

### FR-013: CI Pipeline Never Executed

**Severity:** MEDIUM
**Confidence:** HIGH
**Affected:** .github/workflows/ci.yml
**Evidence:** Workflow exists but never run.
**Runtime impact:** No automated test execution on PRs.

---

## Known Limitations (Not Defects)

| ID | Limitation | Impact |
|----|-----------|--------|
| KL-001 | Fake PSP only | Cannot process real payments |
| KL-002 | Fake notification providers | Cannot send real SMS/email/push |
| KL-003 | No production deployment config | Cannot deploy to production |
| KL-004 | Deadline expiry gated (disabled) | Payment deadlines don't auto-expire |
| KL-005 | Pre-service payment gated (disabled) | No escrow hold until payment |
| KL-006 | GIS disabled on Windows | No geospatial features in dev |
| KL-007 | No customer document verification | `VerificationDocument` has no customer owner FK; `CustomerProfile` has no `verification_status` field (confirmed 2026-07-15, Phase 1.1; unchanged by Phase 1.2). Phone/OTP verification is the current-phase mechanism for customers. See `quality/COMPLETION_BACKLOG.md` BG-016. |
| KL-008 | ~~No activation wiring / completion auto-recompute~~ — **RESOLVED (Phase 1.3, corrected in the PR #5 remediation)** | `ProfileActivationService.activate_caregiver()/activate_organization()` now calls `ActivationEligibilityService.evaluate()` and performs a real, audited, permission-gated `DRAFT -> ACTIVE` transition (BG-018, ARCHITECTURE_DECISION_LOG ADM-016). `profile.status` is the sole source of truth for current activation state — an earlier version of this fix used `AuditLog` existence as the activation signal, which was corrected before merge (PR #5 review). `ProfileCompletionService` is now the single deterministic source for completion percentage. Superseded item: profile `verification_status` roll-up itself is IMPLEMENTED (Phase 1.2), not a limitation. |
| KL-009 | No automatic deactivation on verification becoming invalid/expired | An already-ACTIVE profile's `status` is not automatically walked back when a required document later expires or a review is reversed — `ActivationEligibilityService.evaluate()` correctly reports `eligible=False` again, but nothing acts on that for an already-active profile. Explicitly deferred per Phase 1.3 task governance (no suspension/revalidation workflow exists to hook it into). See `quality/COMPLETION_BACKLOG.md` BG-019. |
| KL-010 | ~~Caregiver gallery~~ delivered (Sprint 2.2); ~~credentials/skills/experience presentation~~ delivered (Sprint 2.3); ~~availability~~ delivered (Sprint 2.4); financial overview, orders + history still not implemented | Roadmap Phase 2's full scope; Phase 2.1 (2026-07-15) delivered the foundation slice (skills, experience, verified-credential summary, corrected public-profile eligibility); Sprint 2.2 (2026-07-15) delivered the caregiver gallery/media portfolio; Sprint 2.3 (2026-07-15) delivered precise verification badges, skill/experience visibility management, an expiring-soon owner-facing credential state, and derived professional highlights; Sprint 2.4 (2026-07-15) delivered weekly working-hour intervals with overlap validation, time-off management, a canonical structured availability evaluator, and a privacy-safe public availability summary. Extended financial overview/orders + history (Sprint 2.5) remains open. See `quality/COMPLETION_BACKLOG.md` BG-021. |
| KL-011 | ~~Directory/home-page caregiver listings do not require verification/account-active~~ — **RESOLVED (BG-022, 2026-07-15)** | `verification_status == VERIFIED` and account `is_active` are now part of the single canonical `common.is_publicly_visible_attrs()` rule, applied uniformly by the caregiver directory, home-page listings, and the single profile detail page — no more divergence between "found in a listing" and "profile page loads." See `quality/COMPLETION_BACKLOG.md` BG-022 and `ARCHITECTURE_DECISION_LOG.md` ADM-017's second remediation note. |
| ~~KL-012 (pre-remediation)~~ | ~~Pre-existing per-candidate query cost in directory ranking/card-building (not eligibility)~~ — **RESOLVED (Sprint 2.6 PR #11 remediation, 2026-07-15)** | Discovered during BG-022's query-count verification (2026-07-15): `DiscoveryRankingService.rank()` issued one `availability_capacity_rule` query per candidate, and `CaregiverDirectoryService._build_card()` issued one `reviews_reputation_snapshot` query and one `orders_order` completed-jobs count query per card — pre-existing, unrelated to the BG-022 eligibility fix (which was already confirmed O(1)). Initially deferred as out of BG-022's and Sprint 2.6's own initial scope; a follow-up architecture review found this inconsistent with Sprint 2.6's own "query behavior is bounded" and "no unresolved Phase 2 blocker" acceptance criteria and required it resolved inside PR #11. **Fixed:** three independent per-candidate query sources batched — `CapacityService.bulk_is_capacity_exceeded()` (new, `apps.availability`) replaces the per-candidate `is_capacity_exceeded()` call inside `DiscoveryRankingService._score()`; `SupplierSearchService._filter_by_city()` now calls the pre-existing `resolve_supplier_entities_bulk()` instead of the per-candidate `resolve_supplier_entity()`; `CaregiverDirectoryService._build_card()` now consumes precomputed `rating_summaries_bulk()`/`completed_jobs_counts_bulk()` maps (both new) instead of querying per built card. Ranking formula, scoring weights, sort order, pagination, and public-visibility policy are all unchanged — only the underlying query pattern changed. Directory/search/home query counts are now fully flat from 1 to 100+ matching candidates (measured: directory 16, filtered search 17, home featured 17 — constant at every candidate count tested). Single-supplier call sites (`provider_portal`/`organization_portal`'s own capacity display, `resolve_supplier_entity()` elsewhere) were left unchanged — only the many-candidates code paths were batched. See `traceability/ARCHITECTURE_DECISION_LOG.md` ADM-022's remediation note. |
| ~~KL-013 (pre-remediation)~~ | ~~Gallery physical-file deletion ran before the database row deletion, inside the same transaction~~ — **RESOLVED (PR #7 review, 2026-07-15)** | `CaregiverGalleryService.remove_item()` originally deleted the stored file first, then the row — a later rollback of that (or an enclosing) transaction would have left a live row pointing at an already-deleted file, since filesystem operations aren't transactional. Fixed: the row is deleted first; physical deletion is scheduled via `transaction.on_commit()`, which Django discards entirely if the transaction rolls back. See `ARCHITECTURE_DECISION_LOG.md` ADM-018's remediation note. |
| KL-014 | Gallery orphan-file cleanup/retry not automated | If a post-commit physical file deletion itself fails (storage/filesystem error), the failure is logged (`CaregiverGalleryService._delete_stored_file()`), not retried — the database row stays deleted either way (correct, safe outcome), but the orphaned file itself is not automatically swept. No cleanup-job/retry infrastructure exists anywhere in this repository to hook this into (recorded, not built, per the PR #7 remediation's explicit "do not implement a broad background-cleanup subsystem" scope limit). Detectable via the `apps.accounts.services.caregiver_gallery_service` error log. |
| KL-015 | Gallery image decoded-dimension limits are fixed constants, not tenant-configurable | `MAX_IMAGE_WIDTH`/`MAX_IMAGE_HEIGHT`/`MAX_IMAGE_PIXELS` (`image_validation.py`) are explicit, hardcoded values (8000px/8000px/25M px) — matching every other numeric limit in this module's existing style (`MAX_IMAGE_BYTES`, `MAX_GALLERY_ITEMS_PER_CAREGIVER`). No product requirement or existing repo convention (e.g. `RequiredDocumentPolicy`'s `ConfigResolver`) calls for these to vary per tenant. Not a defect — a deliberate simplicity choice, recorded per `ARCHITECTURE_DECISION_LOG.md` ADM-018. |
| KL-016 | `CaregiverSkill.name` is free-text, no catalog/normalization | Two caregivers (or the same caregiver over time) can record spelling variants of the same skill (e.g. "پرستاری سالمندان" vs "مراقبت از سالمندان") as distinct rows — nothing merges them for search/filter purposes. Confirmed, not fixed, in Sprint 2.3 (2026-07-15): the model was deliberately kept free-text in Phase 2.1 (`ARCHITECTURE_DECISION_LOG.md` ADM-017) and Sprint 2.3's own governance explicitly warned against "silently redesigning" it. A skill catalog/taxonomy table would resolve this but is a genuinely new modeling decision, not a UI-completion task — recorded as a future migration risk, not attempted here. |
| ~~KL-017 (pre-remediation)~~ | ~~No duplicate/overlap validation on weekly working windows~~ — **RESOLVED (Sprint 2.4, 2026-07-15)** | `AvailabilityMutationService.add_working_window()`/`update_working_window()` previously accepted an exact duplicate or a partially overlapping active window on the same day for the same supplier with no rejection — the only validation was `start_time < end_time`. Fixed: a new `_validate_no_overlap()` check refuses both cases, excluding disabled windows on both sides. See `ARCHITECTURE_DECISION_LOG.md` ADM-020 Decision 3. |
| KL-018 | Per-caregiver time zone is not modeled | Every availability evaluation resolves through the single platform-wide `settings.TIME_ZONE` (`Asia/Tehran`) — a caregiver physically located elsewhere has their schedule interpreted against the platform default, not their own local time. Confirmed, not fixed, in Sprint 2.4 (2026-07-15) per that sprint's own explicit governance ("use the existing tenant/platform time-zone and document the limitation... do not invent a second time-zone source"). See `quality/COMPLETION_BACKLOG.md` BG-024. |
| ~~KL-019 (pre-remediation)~~ | ~~KL-017's overlap check was not concurrency-safe~~ — **RESOLVED (PR #9 review, 2026-07-15)** | KL-017's `_validate_no_overlap()` was a plain, unlocked `SELECT`, and `add_working_window()` took no lock at all before its check-then-insert — under PostgreSQL READ COMMITTED, two concurrent transactions creating overlapping windows for the same supplier/day could both read "no conflict" before either committed, then both insert (`transaction.atomic` alone does not serialize concurrent reads). `update_working_window()`'s pre-existing `select_for_update()` on the window row being updated did not close the gap either — it locks no row a concurrent `add_working_window()` touches, and two concurrent updates to two *different* windows of the same supplier/day each lock a different row. This was deferred as "multi-threaded concurrency race testing... not written" in the initial Sprint 2.4 report, and inspection during PR #9 review found it was a genuine implementation gap, not merely an untested-but-safe design. Fixed: both mutation methods now lock the owning `kernel.ServiceSupplier` row first, before any overlap check — mirroring `apps.accounts.services.caregiver_gallery_service.CaregiverGalleryService.add_item()`'s existing precedent for the same class of problem. Proven by 9 new `TransactionTestCase` tests in `apps.availability.tests.test_concurrency`, each asserting final database state. See `ARCHITECTURE_DECISION_LOG.md` ADM-020's remediation note. |
| KL-020 | No canonical bonus/penalty representation for caregivers | Confirmed by repository-wide inspection (Sprint 2.5, 2026-07-15): `apps.wallet.models.WalletTransactionType` has CREDIT/DEBIT/REFUND/PROMOTION/ADJUSTMENT/MANUAL, none carrying a bonus/penalty semantic; no dedicated adjustment/bonus/penalty model exists in `apps.commission` or elsewhere; the only other repository hits for "bonus"/"penalty" are an unrelated matching/discovery ranking-score concept and a comment referencing a never-built, reserved-for-a-future-PR cancellation-penalty engine. The Caregiver Professional Dashboard's financial overview documents this gap directly (`FinancialOverviewViewModel.bonus_penalty_note`) rather than inventing a CREDIT/DEBIT-based classification. See `quality/COMPLETION_BACKLOG.md` BG-026 and `ARCHITECTURE_DECISION_LOG.md` ADM-021 Decision 4. |
| KL-021 | **RESOLVED (Sprint 3.2, 2026-07-16).** `organization_profile.html` reused the caregiver-directory URL as its own SEO `page_url`/canonical target | Discovered during Sprint 2.6 (2026-07-15) while auditing `templates/public_site/caregiver_profile.html`'s identical defect (fixed in Sprint 2.6 — the caregiver page now passes its own `{% url 'public_site:caregiver-profile' %}` as both `page_url` and `canonical_url`). `templates/public_site/organization_profile.html` line 5 passed the generic `page_url="/find-an-organization/"` to `ui/components/public/seo_meta.html` instead of that organization's own detail URL. Deliberately left unfixed in Sprint 2.6 — organization-profile templates were out of that sprint's strict caregiver-public-profile-finalization scope. **Fixed in Sprint 3.2**, now this sprint's own scope: resolves `{% url 'public_site:organization-profile' supplier_id=profile.supplier_id %}` and passes it as both `page_url` and `canonical_url`, matching the caregiver page's own pattern exactly. See `quality/COMPLETION_BACKLOG.md` BG-030 and `ARCHITECTURE_DECISION_LOG.md` ADM-024 Decision 3. |
| KL-022 | No flash-message/error-surfacing framework for POST-action portal views | Confirmed by repository-wide inspection (Sprint 3.1, 2026-07-16): `django.contrib.messages` is used nowhere in `apps.organization_portal`/`apps.provider_portal`/`apps.portal`. Pre-existing POST-action buttons (`staff_approve_view`/`staff_suspend_view`) already had no error-surfacing path — a failed action just redirects back with no visible feedback. Sprint 3.1's new affiliation-lifecycle action views (`invite_caregiver_view`, `affiliation_request_approve_view`/`_reject_view`, `staff_terminate_view`, `invitation_cancel_view`, and the `provider_portal` company-page equivalents) deliberately match this existing convention (`except AccountsError: pass`, then redirect) rather than introducing flash messaging as a one-off for this sprint. Re-evaluated at the Phase 4 Closure Review (2026-07-17): still open, still explicitly cross-portal infrastructure — **does not block Phase 4 closure.** See `traceability/ARCHITECTURE_DECISION_LOG.md` ADM-023 and `quality/COMPLETION_BACKLOG.md` BG-029. |
| KL-023 | Favorites list fully materialized before Python-side pagination (engineering improvement, not a defect) | **Current behavior:** `CustomerFavoritesPresentationService.build_list_view()` (`apps/portal/services/favorites_service.py:44`) executes `favorites = list(favorites)`, materializing the customer's *entire* favorites queryset before offset/slice pagination in Python. Confirmed by direct code inspection during the Phase 4 Closure Review (2026-07-17). **Why non-blocking:** the query *count* stays bounded — `FavoritesViewQueryBudgetTest.test_query_count_bounded_at_representative_sizes` (`apps/portal/tests/test_favorites_view.py`) measures 0/1/5/20 favorites and asserts the query-count growth is `<= 8`, a small fixed bound, not per-row. Only row materialization/list-slicing scales with total favorite count, not query count. **Impact:** negligible at realistic scale — a customer's favorites list is self-curated preference data, not a system-generated unbounded collection; no production usage evidence suggests customers accumulate favorite counts large enough for this to matter. **Trigger for reconsideration:** real usage data showing customers with hundreds-plus favorites, or a future requirement to sort/filter server-side. **Disposition:** deferred. **Not a Phase 5 prerequisite** — Phase 5 (Marketplace Order Workflow) does not touch Favorites. See `traceability/ARCHITECTURE_DECISION_LOG.md` ADM-028. |
| KL-024 | Favorites concurrency test uses a mocked `IntegrityError` recovery path, not a genuine parallel-transaction test (test-hardening improvement, not a defect) | **Current behavior:** `test_add_favorite_survives_integrity_error_race` (`apps/accounts/tests/test_favorites.py:131-149`) uses `unittest.mock.patch(..., side_effect=IntegrityError("simulated race"))` inside a plain `TestCase`, proving the catch-and-refetch branch executes correctly — not that two genuinely concurrent, separately-committed database transactions resolve to one row. Confirmed by direct code inspection during the Phase 4 Closure Review (2026-07-17). Contrast with this repository's own stronger precedent for genuinely concurrency-sensitive mutations: `apps.availability.tests.test_concurrency` and `apps.accounts.tests.test_affiliation_lifecycle`, both real `TransactionTestCase`s with separately-committed transactions. **Why non-blocking:** the production code path (`get_or_create()` + the DB `UniqueConstraint uq_customer_favorite_supplier`) is the same idempotent pattern already proven safe elsewhere in this codebase (`CaregiverSkillService`'s own duplicate-handling precedent); the DB constraint, not the test, is the real serialization boundary regardless of how it is tested. **Impact:** a favorites double-click race has no financial, tenant-isolation, or data-integrity consequence beyond one extra idempotent request — categorically lower stakes than the working-window-overlap or membership-activation races that justified the prior `TransactionTestCase` additions. **Trigger for reconsideration:** any future change to `FavoritesService.add_favorite()`'s concurrency handling, or a decision to touch this service for an unrelated reason (cheap to fix opportunistically then). **Disposition:** deferred, not a standalone remediation sprint. **Not a Phase 5 prerequisite.** See `traceability/ARCHITECTURE_DECISION_LOG.md` ADM-028. |
