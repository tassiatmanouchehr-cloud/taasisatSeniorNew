# CURRENT GAPS AND COMPLETION BACKLOG

**Last verified HEAD:** phase1-verification-activation-rules (from main @ 278098b)
**Last verified date:** 2026-07-15

---

## P0 — Prevents Safe Continuation or Merge

### BG-001: Commit Phase 1 OrderOffer Implementation — **COMPLETE**

**Resolution:** OrderOffer model, migration `orders/0008_orderoffer.py`, tests,
and admin were committed in `ce3b30e` ("Repository documentation
reorganization"). Verified by `git log -- src/apps/orders/migrations/0008_orderoffer.py`
and clean working tree. Closed 2026-07-14.

### BG-002: Fix Pre-Existing Seed Test order_number Collision — **COMPLETE**

**Root cause:** Random in-run collision of the 4-digit suffix in
`orders/models.py:_generate_order_number()` (10,000 numbers/day); proven by a
1/10 isolated-run failure and two full-suite errors on 2026-07-14 at ce3b30e.
**Resolution (2026-07-14):** `Order.save()` now retries auto-generation up to
`ORDER_NUMBER_MAX_ATTEMPTS` (5) times when the database unique constraint
rejects a generated number, each attempt in its own savepoint; suffix widened
to 6 digits (10^6/day). Caller-supplied duplicates still raise immediately.
No migration required. Regression tests:
`orders/tests/test_order_number_generation.py` (8 tests incl. concurrency).
See CHANGE_LEDGER CL-017 and TEST_EXECUTION_LOG Run 009.
**MERGED to main** via PR #1, merge commit `eb51018` (2026-07-14), full
regression 1680/1680 green.

### BG-015: Manual Document Verification Workflow (Phase 1.1) — **COMPLETE (caregiver + organization)**

**Resolution (2026-07-15):** `VerificationReviewService` (approve/reject/request_correction,
row-locked, tenant-scoped, self-review refused, idempotent same-outcome
no-op, audited via `AuditLog`), `accounts.document.review` permission,
`DocumentStatus.CORRECTION_REQUIRED`, admin_portal review queue/detail/
file/review views, owner-facing reason display. 41 tests (25 service +
16 view). **MERGED to main** via PR #3, merge commit `278098b` (2026-07-15),
full regression 1721/1721 green at merge.
See traceability/IMPLEMENTATION_JOURNAL.md and ARCHITECTURE_DECISION_LOG ADM-014.
**Not included:** customer document verification (see BG-016), profile
verification_status roll-up (see BG-017 — now COMPLETE, see below).

---

## P1 — Blocks First Complete Internal Product Workflow

### BG-016: Customer Document Verification (Domain Model Gap)

**Current evidence:** `VerificationDocument.caregiver`/`.organization` are the only
two owner FKs (CHECK-constrained exactly-one-of-two); `CustomerProfile` has no
`verification_status` field. Confirmed by repository-wide inspection during
Phase 1.1 (2026-07-15) — customer identity verification does not exist as a
domain concept anywhere in the repository.
**Why needed:** Task governance for Registration & Verification names customer
identity verification as in-scope; current domain model does not support it.
**Dependencies:** A scoped decision on whether/how to extend `VerificationDocument`'s
owner CHECK constraint (a real architectural change, not a bug fix).
**Affected modules:** accounts
**Suggested implementation size:** Medium (new FK + constraint migration + service/view work)
**Risk:** Low-medium — additive to an existing, deliberately-designed constraint
**Not in scope:** Profile roll-up (BG-017)

### BG-017: Profile Verification Status Roll-Up — **COMPLETE**

**Resolution (2026-07-15, Phase 1.2):** `RequiredDocumentPolicy` (Part A —
the previously-missing policy: caregiver = IDENTITY + BACKGROUND_CHECK
required, organization = REGISTRATION + OPERATING_LICENSE required,
tenant-overridable via `ConfigResolver`, no migration) +
`ProfileVerificationRollupService` (Part B — derives the existing 4-value
`VerificationStatus` enum from required-document state; wired into
`VerificationReviewService`/`DocumentService.resubmit()`, never a view/
signal). Also delivered in the same slice: `DocumentService.resubmit()`
(Part C — owner-authorized correction/resubmission, blocks silent
replacement of a VERIFIED document) and `ActivationEligibilityService`
(Part D — read-only, structured eligibility for caregiver/organization).
47 new tests, zero new migrations. Branch
`phase1-verification-activation-rules`, PR pending merge. See
traceability/IMPLEMENTATION_JOURNAL.md and ARCHITECTURE_DECISION_LOG ADM-015.
**Not included:** wiring `ActivationEligibilityService` into an actual
activation/publishing action (currently read-only — see BG-018);
`profile_completion_percent` auto-recompute on every mutation (see BG-018).

### BG-018: Activation Wiring and Profile Completion Auto-Recompute — **COMPLETE**

**Resolution (2026-07-15, Phase 1.3):** `ProfileCompletionService` (Part A —
single source of truth for the base-profile-field checklist per profile
type; `calculate_caregiver_profile_completion()`/
`calculate_organization_profile_completion()` now delegate to it instead of
duplicating field lists — deterministic, called live on every read, no
persisted staleness to auto-recompute) and `ProfileActivationService`
(Part B/C — `activate_caregiver()`/`activate_organization()`, calls
`ActivationEligibilityService.evaluate()`, refuses when ineligible with
structured reasons, permission-gated via new `ACCOUNTS_PROFILE_ACTIVATE`,
row-locked, idempotent, audited). Minimum usable platform-operator and
owner-facing UI delivered (Part D). 40 new tests, zero new migrations.
Branch `phase1-activation-completion-final`, PR pending merge. See
`traceability/IMPLEMENTATION_JOURNAL.md` and `ARCHITECTURE_DECISION_LOG`
ADM-016.
**Not included:** automatic deactivation of an already-active profile when
verification later becomes invalid/expired (see BG-019 — no
suspension/revalidation workflow exists to hook it into).
**Remediated (2026-07-15, PR #5 review):** the initial implementation used
`AuditLog` existence, not `profile.status`, as the activation signal —
because registration left profiles `ACTIVE` by default, activation never
performed a real status transition in the common case. Fixed: caregiver/
organization registration now creates `ProfileStatus.DRAFT` profiles;
`ActivationEligibilityService` no longer requires `status == ACTIVE`
(removed the resulting circularity); `ProfileActivationService` now
performs a real `DRAFT -> ACTIVE` transition and judges idempotency from
`profile.status` directly. See `traceability/ARCHITECTURE_DECISION_LOG.md`
ADM-016's remediation note.

### BG-019: Automatic Deactivation on Verification Becoming Invalid/Expired

**Current evidence:** `ProfileActivationService` (BG-018/Phase 1.3) never
walks an already-ACTIVE profile's `status` back to a blocked state when its
verification later becomes invalid (e.g. a required document expires).
`ActivationEligibilityService.evaluate()` itself correctly reports
`eligible=False` again in that case (unchanged Phase 1.2 behavior) — only
the persisted `status` field is not automatically revised.
**Why needed:** Task governance for Phase 1.3 explicitly named this as an
acceptable deferral ("do NOT automatically deactivate an already-active
profile in this slice unless an explicit suspension/revalidation workflow
already exists") — recorded here rather than silently dropped.
**Dependencies:** A scoped decision on a suspension/revalidation workflow
(does not exist anywhere in the repository today).
**Affected modules:** accounts
**Suggested implementation size:** Medium (new workflow, likely a
scheduled job re-evaluating eligibility for ACTIVE profiles)
**Risk:** Medium — a real behavior change to already-active, customer-
facing profiles; needs its own product decision, not a guess
**Not in scope:** Marketplace visibility wiring (`is_publicly_visible()` is
a separate, existing, unrelated concern — see `traceability/IMPLEMENTATION_JOURNAL.md`)

### BG-020: Caregiver Professional Profile — Foundation Complete, Gallery/Financial/Orders Remain

**Resolution (2026-07-15, Phase 2.1):** `CaregiverSkill`/`CaregiverExperience` (new
models), `CaregiverSkillService`/`CaregiverExperienceService` (owner-authorized CRUD),
`PublicCredentialSelector` (safe public credential summary derived from approved,
unexpired `VerificationDocument` rows), corrected public-profile eligibility
(`verification_status == VERIFIED` + account `is_active`, added locally to
`CaregiverPublicProfileService.get_profile()`), provider-portal skill/experience
management pages, and public-profile skills/experience/credentials sections. Biography,
headline (`specialty`), services-offered (`ServiceSupplier.service_categories`), the
public profile route, and the provider-portal profile edit pages were already implemented
(Epic 06 Sprint 2) and reused, not rebuilt. 50 new tests, one new migration (2 new tables
only), full regression 1874/1874 green. Branch
`phase2-caregiver-professional-profile-foundation`, PR pending merge. See
`traceability/IMPLEMENTATION_JOURNAL.md` and `ARCHITECTURE_DECISION_LOG` ADM-017.
**Not included (roadmap Phase 2 remains open):** gallery (new model + upload service +
moderation flag), certificates-as-gallery presentation, extended financial overview,
orders + history pages — see BG-021.

### BG-021: Caregiver Profile — Gallery, Financial Overview, Orders + History

**Current evidence:** Roadmap Phase 2's full scope (`IMPLEMENTATION_ROADMAP.md`) includes
an Instagram-like gallery, certificates surfaced as a visual gallery (distinct from
Phase 2.1's plain verified-credential badges), an extended financial/earnings overview,
and an orders + history page. None of these were implemented in Phase 2.1 — explicitly
out of that slice's scope per its own governance ("Do not implement: Instagram-style
gallery... caregiver financial dashboard... caregiver order dashboard...").
**Why needed:** Roadmap Phase 2 acceptance criteria are not met until these exist.
**Dependencies:** BG-020 (done — foundation this work builds on). Gallery specifically
also depends on the still-open media storage strategy for production (currently local
`FileField` — a pre-existing, acknowledged roadmap blocking item).
**Affected modules:** accounts, provider_portal, public_site
**Suggested implementation size:** Medium-High (new GalleryItem model + upload/moderation
service; financial overview extension; orders/history read views)
**Risk:** Medium — new public-facing media upload surface; must not weaken the private/
public document boundary this and prior phases established
**Not in scope:** Marketplace offer workflow, invoice workflow, payment/settlement
changes (unrelated to gallery/financial-overview/orders-history display work)

### BG-022: Directory/Home-Page Listing Eligibility Does Not Match the Public Profile Page's Stricter Rule

**Current evidence:** Phase 2.1 added `verification_status == VERIFIED` and account
`is_active` checks to `CaregiverPublicProfileService.get_profile()` (the single caregiver
profile page) only — deliberately not to the shared `apps.public_site.services.common
.is_publicly_visible()` function the caregiver directory (`directory_service.py`) and
home-page featured-caregiver listing (`home_service.py`) also call. A caregiver can now
appear in directory/home-page listings while their own profile page 404s (unverified or
inactive account).
**Why needed:** Consistency between "discoverable in a listing" and "profile page loads"
is a reasonable product expectation, though not one Phase 2.1's own governance asked to
fix — tightening it was judged out of this slice's scope (see
`ARCHITECTURE_DECISION_LOG.md` ADM-017 Decision 2 for the full reasoning, including that
~80 pre-existing directory/home-page tests currently depend on the looser rule).
**Dependencies:** A scoped decision on whether directory/home-page listing eligibility
should be tightened to match, and if so, updating the ~80 affected pre-existing tests'
fixtures.
**Affected modules:** public_site
**Suggested implementation size:** Small (the check itself is a one-line addition to
`is_publicly_visible_attrs()`); Medium overall once the fixture/test update cost is
included
**Risk:** Low-medium — a real, visible behavior change to who appears in public listings
**Not in scope:** Any change to `CaregiverPublicProfileService.get_profile()` itself
(already correct as of Phase 2.1)

### BG-003: OrderOfferService (Phase 2)

**Current evidence:** Phase 1 model exists. No service layer.
**Why needed:** Offer Marketplace cannot function without services to submit/edit/withdraw/select offers.
**Dependencies:** BG-001 (commit Phase 1)
**Affected modules:** orders
**Suggested implementation size:** Medium (1 service class + tests)
**Required tests:** Unit tests with PostgreSQL, concurrency tests
**Risk:** Medium — must not break existing assignment flow
**Not in scope:** Discovery, views, templates, APIs, payment integration

### BG-004: Implement Real PSP Adapter

**Current evidence:** Only `FakePaymentProviderAdapter` exists. All payment flows are mocked.
**Why needed:** Cannot process real payments without a real PSP.
**Affected modules:** payments
**Suggested implementation size:** Large (adapter + integration tests + configuration)
**Required tests:** Integration tests with sandbox PSP
**Risk:** High — financial correctness critical
**Not in scope:** Multiple PSP support, payment method diversity

### BG-005: Implement Real Notification Providers

**Current evidence:** Only fake SMS/email/push providers exist.
**Why needed:** Cannot send real notifications to users.
**Affected modules:** notifications
**Suggested implementation size:** Medium (per-provider adapter)
**Required tests:** Integration tests with sandbox providers
**Risk:** Medium — operational requirement
**Not in scope:** Multi-channel notification preferences

---

## P2 — Blocks External Pilot

### BG-006: Production Deployment Configuration

**Current evidence:** No docker-compose production config, no production settings beyond security headers.
**Why needed:** Cannot deploy to production.
**Affected modules:** config
**Suggested implementation size:** Medium
**Risk:** Medium
**Not in scope:** Kubernetes, auto-scaling

### BG-007: Enable Deadline Expiry Gate

**Current evidence:** `deadline_activation_enabled` defaults to DISABLED. Payment deadlines are created but don't auto-expire.
**Why needed:** Orders will remain in limbo if deadlines don't expire.
**Affected modules:** commission
**Suggested implementation size:** Small (config change + verification)
**Risk:** Medium — must verify expiry cascade works correctly
**Not in scope:** Deadline extension UI

### BG-008: Enable Pre-Service Payment Gate

**Current evidence:** `preservice_payment_enabled` defaults to DISABLED. No escrow hold before service.
**Why needed:** Financial protection for providers requires escrow.
**Affected modules:** commission, finance
**Suggested implementation size:** Medium (gate enablement + integration verification)
**Risk:** High — financial flow change
**Not in scope:** Customer payment UI

---

## P3 — Blocks Production Launch

### BG-009: Tenant Isolation Hardening

**Current evidence:** No middleware-level tenant injection. Depends on developer discipline.
**Why needed:** Cross-tenant data leak is the highest-severity security risk.
**Affected modules:** All
**Suggested implementation size:** Large (middleware + audit + row-level security)
**Risk:** High — architectural change
**Not in scope:** Multi-region deployment

### BG-010: CI Pipeline Activation

**Current evidence:** `.github/workflows/ci.yml` exists but never executed.
**Why needed:** No automated test execution on PRs.
**Affected modules:** DevOps
**Suggested implementation size:** Small
**Risk:** Low
**Not in scope:** Full CI/CD pipeline

### BG-011: RBAC Enforcement Audit Logging

**Current evidence:** No audit when `rbac.enforcement.enabled` is toggled.
**Why needed:** Security compliance.
**Affected modules:** kernel
**Suggested implementation size:** Small
**Risk:** Low
**Not in scope:** RBAC redesign

---

## P4 — Post-Launch or Optimization

### BG-012: Remove Legacy Wallet from finance App

**Current evidence:** `finance.WalletAccount`/`WalletTransaction` superseded by `apps.wallet`.
**Why needed:** Reduce confusion.
**Affected modules:** finance
**Suggested implementation size:** Small
**Risk:** Low
**Not in scope:** Data migration

### BG-013: Add Tests for common App

**Current evidence:** Zero tests for shared utilities imported across apps.
**Why needed:** Regression protection for foundational code.
**Affected modules:** common
**Suggested implementation size:** Small
**Risk:** Low
**Not in scope:** Full coverage

### BG-014: Extract Shared Auth Guard

**Current evidence:** Each portal independently implements `_guard()`.
**Why needed:** DRY principle, single enforcement point.
**Affected modules:** All portals
**Suggested implementation size:** Medium
**Risk:** Low
**Not in scope:** Middleware redesign
