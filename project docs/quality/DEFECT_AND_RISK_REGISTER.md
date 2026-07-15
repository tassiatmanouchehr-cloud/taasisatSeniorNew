# DEFECT AND RISK REGISTER

**Last verified HEAD:** a5dbaf28703142edaa1d770ea8f3c2a45a12640f
**Last verified date:** 2026-07-14

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
| KL-010 | ~~Caregiver gallery~~ delivered (Sprint 2.2); financial overview, orders + history still not implemented | Roadmap Phase 2's full scope; Phase 2.1 (2026-07-15) delivered the foundation slice (skills, experience, verified-credential summary, corrected public-profile eligibility); Sprint 2.2 (2026-07-15) delivered the caregiver gallery/media portfolio (`CaregiverGalleryItem`, `CaregiverGalleryService`, provider-portal management page, public-profile gallery section). Extended financial overview and orders + history remain open (Sprint 2.5). See `quality/COMPLETION_BACKLOG.md` BG-021. |
| KL-011 | ~~Directory/home-page caregiver listings do not require verification/account-active~~ — **RESOLVED (BG-022, 2026-07-15)** | `verification_status == VERIFIED` and account `is_active` are now part of the single canonical `common.is_publicly_visible_attrs()` rule, applied uniformly by the caregiver directory, home-page listings, and the single profile detail page — no more divergence between "found in a listing" and "profile page loads." See `quality/COMPLETION_BACKLOG.md` BG-022 and `ARCHITECTURE_DECISION_LOG.md` ADM-017's second remediation note. |
| KL-012 | Pre-existing per-candidate query cost in directory ranking/card-building (not eligibility) | Discovered during BG-022's query-count verification (2026-07-15): `DiscoveryRankingService.rank()` issues one `availability_capacity_rule` query per candidate, and `CaregiverDirectoryService._build_card()` issues one `reviews_reputation_snapshot` query and one `orders_order` completed-jobs count query per card — pre-existing, unrelated to the BG-022 eligibility fix (which is confirmed O(1): `common.bulk_supplier_attrs()` issues exactly 2 queries regardless of candidate count, verified by `apps.public_site.tests.test_public_visibility_policy.ListingQueryCountTest`). Not fixed here — touching `apps.discovery`'s ranking algorithm or the reputation/completed-jobs enrichment path is a separate, unrelated performance task outside BG-022's narrow eligibility-consistency scope. |
