# IMPLEMENTATION JOURNAL

**Repository:** taasisatSenior
**Session:** Offer Marketplace Phase 1 — Domain Foundation

---

## Initial Phase 1 Implementation

**Date:** July 13, 2026
**Status:** COMPLETE

Created OrderOffer model, migration 0008, admin registration, 24 tests.
Initial migration had conditional UniqueConstraint (active-only per supplier).
Had premature PaymentIntent reference in docstring.
Had temporary cleanup tooling (cleanup_test_db.py).

---

## Architecture Review Findings

**Date:** July 13, 2026
**Status:** ADDRESSED

Identified 5 issues:
1. Premature PaymentIntent reference in model docstring
2. Active-only uniqueness policy (should be canonical)
3. Temporary cleanup tooling (cleanup_test_db.py)
4. Missing domain properties
5. Documentation inconsistencies

---

## First Remediation Attempt

**Date:** July 13, 2026
**Status:** SUPERSEDED

Applied 5 remediations but introduced two problems:
1. Created two migrations (0008 + 0009) instead of squashing into one
2. Had complex loop test that failed due to order_number collision

---

## Completion Remediation

**Date:** July 14, 2026
**Status:** COMPLETE

### Changes Applied
1. Squashed 0008+0009 into single 0008 with canonical constraint
2. Added can_edit, can_withdraw, can_select domain properties
3. Replaced complex loop test with 7 individual status tests
4. Verified admin (supplier__display_name valid)
5. Removed temporary cleanup tooling

---

## Final Verified Phase 1 State

**Date:** July 14, 2026
**Status:** VERIFIED

### Migration
- Single migration: `orders/0008_orderoffer.py`
- Dependencies: kernel.0011, orders.0007, AUTH_USER_MODEL
- No 0009 migration exists
- No phantom kernel migration exists

### Database Constraints
- Unconditional UniqueConstraint: `(order, supplier)` — one canonical offer per supplier per order
- Conditional UniqueConstraint: `(order)` WHERE status='selected' — one selected offer per order

### Domain Properties
- `can_edit` → True only when status == SUBMITTED
- `can_withdraw` → True only when status == SUBMITTED
- `can_select` → True only when status == SUBMITTED
- All 7 status values tested for all 3 properties

### Test Results (with real exit codes)

| Command | Exit Code | Discovered | Passed | Failed | Errors | Duration |
|---------|-----------|-----------|--------|--------|--------|----------|
| manage.py check | 0 | — | — | 0 | 0 | — |
| makemigrations --check | 1 | — | — | — | — | — |
| OrderOffer targeted | 0 | 40 | 40 | 0 | 0 | 1.494s |
| Full Orders | 0 | 119 | 119 | 0 | 0 | 9.037s |
| Full regression | 1 | 1672 | 1671 | 0 | 1 | 351.569s |

**Note:** The full regression error (exit code 1) is in `test_seed_product_walkthrough.py` — a pre-existing order_number collision race condition, NOT related to OrderOffer or Phase 1 changes.

### Files Implemented

| File | Purpose | Lines |
|------|---------|-------|
| `src/apps/orders/models.py` | OrderOfferStatus, OFFER_TERMINAL_STATUSES, OrderOffer | +115 |
| `src/apps/orders/admin.py` | OrderOfferAdmin | +8 |
| `src/apps/orders/migrations/0008_orderoffer.py` | Database migration | 52 |
| `src/apps/orders/tests/test_order_offer_model.py` | 40 unit tests | 481 |

### Files Deleted
- `src/apps/orders/migrations/0009_orderoffer_canonical.py` (squashed into 0008)
- `src/cleanup_test_db.py` (temporary tooling)
- `src/apps/kernel/migrations/0012_orderoffer*.py` (phantom migrations)

### Architecture Decision
ADM-013: One canonical OrderOffer per (order, supplier). Unconditional uniqueness for stable identity, audit history, and reporting.

### Phase 1 Merge Recommendation
**Approved.** All remediations complete. All tests pass (except 1 pre-existing seed error). Single migration. No phantom files. No Phase 2 contamination.

---

## Permanent Repository Memory

**Date:** July 14, 2026
**Status:** CREATED

Created `PROJECT_CONTINUATION.md` and `NEXT_TASK.md` at repository root to ensure any future AI assistant (with zero conversation memory) can continue the project correctly.

**Why introduced:** The project has accumulated significant analysis, architecture decisions, and implementation across multiple sessions. Without persistent repository-level documentation, a new AI session would need to re-discover everything from scratch. These files provide the minimum viable context for continuation.

**Files created:**
- `PROJECT_CONTINUATION.md` — permanent project memory (status, decisions, blockers, governance)
- `NEXT_TASK.md` — next task definition (investigate seed test, then Phase 2)

**Scope:** Documentation only. No code changes.

---

## BG-002 — Order Number Collision Fix

**Date:** 2026-07-14
**Status:** COMPLETE

### Root Cause

`orders/models.py:_generate_order_number()` produced `ORD-YYYYMMDD-` plus a
4-digit random suffix — only 10,000 possible numbers per day against a
globally unique `order_number` column. The seed walkthrough creates enough
same-day orders that in-run birthday-problem collisions occur randomly.
Verified at ce3b30e: 1/10 isolated runs failed; full suite hit the collision
in two test classes (`SeedProductWalkthroughDatasetTest.setUpClass` and
`SeedProductWalkthroughReportSideEffectTest`).

### Chosen Fix (Option D — retry + stronger entropy)

1. `Order.save()` retries auto-generation up to `ORDER_NUMBER_MAX_ATTEMPTS`
   (5) times when the database rejects a generated number with the
   `order_number` unique violation. Each attempt runs inside
   `transaction.atomic()` (a savepoint inside caller transactions), so a
   rejected insert does not poison `@transaction.atomic` order-creation
   services. Any other IntegrityError, and any caller-supplied duplicate
   `order_number`, still raises immediately.
2. Suffix widened from 4 to 6 digits (10^6 numbers/day). Format family
   unchanged: `ORD-YYYYMMDD-NNNNNN`, 19 chars, well within max_length=30.
   Existing 4-digit rows remain valid; no consumer parses the suffix and no
   test asserted the old width (verified by repository-wide grep).

### Alternatives Rejected

- **A. Retry only:** fixes the flake but leaves a 10k/day global ceiling —
  retries would degrade sharply as daily volume grows.
- **B. Stronger entropy only:** reduces but does not eliminate collision
  failures; the defect class survives.
- **C. Database sequence:** deterministic, but changes the public format to
  monotonic (information leak: daily order volume), requires new DB state,
  and is more than the minimal fix.
- **Timestamp component:** rejected per task constraint — concurrent calls
  in the same instant still collide.

### Concurrency Safety

The unique constraint remains the sole arbiter — generation never
check-then-inserts. Under concurrent creation, the second inserter receives
the unique violation from PostgreSQL and retries with a fresh number.
Proven by `OrderNumberConcurrencyTest` (TransactionTestCase, 2 threads,
barrier, forced identical first draw), mirroring
`apps.booking.tests.test_concurrency`.

### Files Changed

| File | Change |
|------|--------|
| `src/apps/orders/models.py` | 6-digit suffix; `ORDER_NUMBER_SUFFIX_LENGTH`, `ORDER_NUMBER_MAX_ATTEMPTS`, `_is_order_number_collision()`; bounded retry in `Order.save()` |
| `src/apps/orders/tests/test_order_number_generation.py` | NEW — 8 regression tests (format, forced collision retry, no overwrite, bounded retry, explicit-duplicate passthrough, savepoint behavior, concurrency) |

### Migration Impact

None. No field or constraint changed; `makemigrations --check` output is
identical to the pre-fix state (pre-existing cosmetic accounts/kernel drift
only, zero orders entries).

### Rollback Method

`git revert` of the fix commit (or `git checkout` of the two files). No data
cleanup needed — 6-digit numbers are ordinary values under the existing
constraint.

---

## PR #1 Merge Record

**Date:** 2026-07-14
**Merge commit:** `eb51018ffbc9faeebae08adebcc21d6dbfe7b92e`
**PR:** #1 — "Synchronize active documentation and fix order-number collisions"
**Merged content:** documentation synchronization (CL-016), IMPLEMENTATION_ROADMAP.md,
BG-002 order-number collision fix + 8 regression tests (CL-017), traceability updates.
**Verification at merge:** full regression 1680/1680 (exit 0), seed suite 46/46,
orders suite 127/127, previously flaky test 20/20 isolated.
**Consequence:** P0 hygiene complete. **Phase 1 — Registration and Verification
Workflows is now the active implementation phase.** Implementation not started;
working branch `claude/taasisat-senior-state-verify-9dzzlm` restarted from merged main.

---

## Phase 1.1 — Registration and Manual Verification Foundation

**Date:** 2026-07-15
**Branch:** phase1-registration-manual-verification (from origin/main @ 55b1cb0)

### Part A — Focused Registration Gap Matrix

| Flow | Existing entry point | Working behavior | Missing behavior |
|------|----------------------|-------------------|-------------------|
| Customer registration | `accounts/views.py:register_customer_view` → OTP → `RegistrationService.create_customer()` | Person/UserAccount/CustomerProfile created, `customer` role assigned, phone-uniqueness checked pre-OTP. 8 passing tests (`test_registration.py`). Post-login routes to `portal:dashboard`. | No identity-document verification concept exists for customers at all — `CustomerProfile` has no `verification_status` field, `VerificationDocument` has no customer FK (see decision below). |
| Caregiver registration | `register_caregiver_view` → `RegistrationService.create_caregiver()` | Person/UserAccount/CaregiverProfile created, `independent_caregiver` role assigned, optional `CompanyAffiliationRequest` created from company_code/name. Post-login routes to `provider_portal:dashboard`. | Document upload existed (`DocumentService`) but **no reviewer path** — `VerificationDocument` could only ever sit at PENDING forever (confirmed by that model's and `DocumentService`'s own docstrings: "future platform-admin verification workflow ... does not exist yet"). |
| Company/organization registration | `register_company_view` → `RegistrationService.create_company_admin()` | Person/UserAccount/OrganizationProfile/OrganizationMembership(ADMIN) created, `organization_admin` role assigned, unique org code generated. Post-login routes to `organization_portal:dashboard`. | Same missing reviewer path as caregiver. |
| Profile bootstrap | `RegistrationService` (all three paths) | Verified via existing test suite — no defect found. | — |
| Identity/professional-license status | `CaregiverProfile.verification_status` / `OrganizationProfile.verification_status` (`VerificationStatus`: UNVERIFIED/PENDING/VERIFIED/REJECTED) | Fields exist and are read by portal/public-profile presentation. | Nothing ever transitions them off UNVERIFIED — no roll-up from document review exists yet (see Deferred). |
| VerificationDocument model | `apps/accounts/models/media.py` | 9 document types, PENDING/VERIFIED/REJECTED, exactly-one-owner CHECK constraint (caregiver XOR organization), private storage path. | No CORRECTION_REQUIRED state; no customer owner (see decision below); zero test coverage before this task. |
| Document upload | `DocumentService.upload_caregiver_document/upload_organization_document/replace_document` | Validates size/real content-type, private storage, resets to PENDING on replace. | None — production quality already. |
| Admin/operator verification capability | none | — | **This was the root missing workflow** — implemented in Part B. |
| Permissions | `apps/kernel/permissions/keys.py` | Canonical registry pattern well-established (register() + role_catalog grant). | No `accounts.document.*` review key existed. |
| Portal pages | provider_portal/organization_portal document_upload.html | Upload/replace form + status badge. | Rejection/correction reason was hard-coded blank (`action_message=""`) — never surfaced the reviewer's reason even though the model already had a `rejection_reason` field. |
| Existing tests | `apps/accounts/tests/` (16 files, 180 methods pre-task) | Strong coverage on registration/RBAC/multirole/tenant-consistency. | **Zero tests existed for `VerificationDocument`/`DocumentService`** (confirmed by directory listing) — a real, pre-existing gap this task also closes. |

**No critical defect found in customer/caregiver/organization registration or profile bootstrap** — all three create accounts/profiles/roles correctly (8/8 pre-existing tests re-run and green). Proceeded directly to Part B per the task's own instruction.

### Scope Decision: Customer Document Verification Deferred

`VerificationDocument.caregiver`/`.organization` are the only two owner FKs, enforced by a database CHECK constraint (exactly one of the two, never both, never neither) — this is `apps/accounts/models/media.py`'s own explicit, documented design. `CustomerProfile` has no `verification_status` field at all. Repository evidence therefore shows **customer identity verification does not exist as a domain concept** in this codebase — it is out of scope for both models involved. Adding a third owner type would mean changing that CHECK constraint (a real architectural change to a deliberately-designed invariant), which the task's own governance says to avoid without approval ("Do not redesign stable architecture"). This task implements manual review for the two owner types the domain model actually supports (caregiver, organization) — matching the task's own Phase 1 bullet list ("Identity verification", "Professional license workflow"), which are supply-side (caregiver/organization) concerns in a senior-care marketplace. Customer document verification, if ever needed, is a new capability requiring its own scoped decision, not a bug in this slice.

### Architecture Decision: `rejection_reason` Is Now Owner-Visible

`VerificationDocument.rejection_reason`'s original docstring (Epic 06 Sprint 2) declared it "Staff-authored, internal-only — never rendered on any provider/organization-facing... page." This task's own explicit business requirement #6 ("The document owner can see: ... rejection/correction reason") is the opposite. Resolved in favor of the current task's explicit requirement: the field is now rendered on the owning caregiver's/organization's own portal page (via `document_status.html`'s `action_message` prop) whenever status is REJECTED or CORRECTION_REQUIRED — still never on any PUBLIC page. Both the model's and the template's docstrings were updated to record this reversal in place; see `traceability/ARCHITECTURE_DECISION_LOG.md` for the formal entry.

### Profile Verification Roll-Up: Deferred

No required-document-type policy exists anywhere in the repository (confirmed by repository-wide search — zero hits for "required_document"/"REQUIRED_DOCUMENT" or any config/rule naming required types per profile). Per the task's own instruction ("If no reliable required-document policy exists, do not guess"), profile-level roll-up (`CaregiverProfile.verification_status` / `OrganizationProfile.verification_status` auto-transitioning from document outcomes) is **not implemented in this slice** and is reported as the next slice.

### Part B — What Was Implemented

- `DocumentStatus.CORRECTION_REQUIRED` added (migration `accounts.0005`, hand-trimmed to exclude unrelated pre-existing cosmetic drift the same `makemigrations` run also detected).
- `apps.accounts.services.verification_review_service.VerificationReviewService` — `approve()`/`reject()`/`request_correction()`, all `@transaction.atomic` with `select_for_update()`, tenant re-derivation + comparison, `PermissionService.require()`, self-review refusal, PENDING-only legal transition with idempotent same-outcome no-op, `AuditService.log()` audit trail.
- `accounts.document.review` permission key (`apps/kernel/permissions/keys.py`), re-exported through `apps.accounts.permission_keys` and `apps.admin_portal.permission_keys`, granted to `platform_owner`/`platform_admin`/`platform_support` in `apps.kernel.role_catalog.DEFAULT_TENANT_ROLES` (same additive pattern as `ORGANIZATION_PROFILE_UPDATE`).
- `apps.accounts.services.verification_evaluator.DocumentVerificationEvaluator` — Protocol-only AI extension point, no implementation, not called anywhere.
- Admin portal: `document_verification_queue`/`_detail`/`_file`/`_review_action` views (thin-controller, same shape as the existing dispute views), `DocumentReviewForm`, 2 templates, 1 home-page nav card.
- Owner-facing: `verification_badge.html` gained a `correction_required` branch; both `document_upload.html` templates now pass the real `rejection_reason` as `action_message` instead of a hard-coded empty string.
- Tests: `apps/accounts/tests/test_verification_review.py` (25 tests, service layer, incl. a `TransactionTestCase` concurrency test mirroring `apps.booking.tests.test_concurrency`) + `apps/admin_portal/tests/test_document_verification.py` (16 tests, view/security layer).

### Deferred (explicitly out of scope for this slice)

1. Profile-level verification roll-up (no required-document policy exists — see above).
2. Customer document verification (no domain model support — see above).
3. AI evaluator implementation (Protocol only, per task instruction).
4. Public profile rendering of verified credential types (explicitly excluded by the task).

---

## Phase 1.2 — Verification Completion and Activation Rules

**Date:** 2026-07-15
**Branch:** phase1-verification-activation-rules (from main @ 278098b)

### Part A — Required-Document Policy

Repository inspection before writing any policy:
- `apps.provider_portal.services.profile_service.PROVIDER_DOCUMENT_TYPES` (5 types) and
  `apps.organization_portal.services.profile_service.ORGANIZATION_DOCUMENT_TYPES` (4 types)
  already partition all 9 `DocumentType` members by profile relevance — reused at the
  correct dependency layer (accounts cannot import from either portal app) rather than
  redefined from scratch.
- No repository infrastructure ties `ServiceCategory`/`ServiceType` to document
  requirements — confirmed by search; per-service variation is explicitly NOT implemented,
  not silently assumed absent.
- `CustomerProfile` has no `verification_status` field; `VerificationDocument` has no
  customer-owner FK (re-confirmed, unchanged since Phase 1.1). Customer document
  verification is NOT implemented this phase either. Phone/OTP verification
  (`apps.accounts.services.otp.OTPService`, already required at registration) is recorded
  as the current-phase identity verification mechanism for customers.
- `ConfigResolver`/`ConfigurationKey`/`ConfigurationValue` (existing since kernel.0005)
  is the established tenant-configuration mechanism every other `*Configuration` wrapper
  in this codebase uses (`CommissionConfiguration`, `BookingConfiguration`, etc.) —
  `get_or_default()` requires no `ConfigurationKey` row to pre-exist, so this policy adds
  zero seeding/migration burden. Reused exactly, no new mechanism invented.

**Policy decided:** caregiver required = IDENTITY + BACKGROUND_CHECK; organization
required = REGISTRATION + OPERATING_LICENSE. Both tenant-overridable, sanitized against
the applicable-type set (an override naming an inapplicable type is dropped, not
honored). Expiry handling reuses the exact "VERIFIED but `expiry_date` < today ->
effectively expired" rule `provider_portal`/`organization_portal`'s own presentation
services already compute for display — made reusable outside the portal layer via
`RequiredDocumentPolicy.is_effectively_expired()`.

### Part B — Profile Verification Roll-Up

`ProfileVerificationRollupService.evaluate_caregiver()/evaluate_organization()` — pure,
deterministic, idempotent read. `sync_caregiver()/sync_organization()` persist the result
(row-locked, no-op write when already correct). See ARCHITECTURE_DECISION_LOG ADM-015 for
the decision to reuse the existing 4-value `VerificationStatus` enum (no 5th
CORRECTION_REQUIRED value) with `needs_correction` as a separate result flag instead.

Wired into `VerificationReviewService._apply_review()` (end of the same transaction, after
the `AuditLog` entry) and `DocumentService.resubmit()` — never left to a view, admin
action, or signal, per governance. Proven safe under concurrent review of two different
documents belonging to the same profile via `select_for_update()` on the profile row
inside `sync_*()` (`RollupConcurrencyTest`).

### Part C — Correction and Resubmission Lifecycle

`DocumentService.resubmit(document, *, actor, file)` — the new owner-authorized entry
point. `replace_document()` (Phase 1.1-era primitive, unconditional) remains but is no
longer called directly from any request-reachable view; both `provider_portal` and
`organization_portal`'s `document_manage_view` now call `resubmit()` instead. Confirmed
via existing test files (`test_profile.py` in both apps) that no pre-existing test
exercises replacing an already-VERIFIED document — the hardening introduces no regression.

Enforced: owner-only (actor's `UserAccount.id` must equal the document owner's, resolved
via the new shared `document_ownership.py`, extracted to avoid duplicating logic already
present in `VerificationReviewService`), VERIFIED documents refuse replacement, row-locked
for concurrency (`ResubmissionConcurrencyTest` proves two concurrent resubmissions
serialize without corruption — both succeed deterministically, no crash). Audit: a new
`accounts.document.resubmitted` `AuditLog` entry is created; the ORIGINAL review's reason
remains permanently in ITS OWN, earlier `AuditLog` entry (never overwritten) — proven by
`test_original_review_reason_survives_in_audit_log_after_resubmission`. The document's
live `rejection_reason` field IS cleared on resubmission (matches Phase 1.1's existing
`replace_document()` behavior, unchanged) — this is not "erasing audit history" since the
live field only ever describes the CURRENT state, and the historical record lives in
`AuditLog`, which is append-only and untouched.

### Part D — Activation Eligibility

`ActivationEligibilityService.evaluate(profile)` — dispatches by type to
`evaluate_caregiver()`/`evaluate_organization()`. Deliberately upstream of and unrelated
to `apps.public_site.services.common.is_publicly_visible()` (an existing, different,
`ServiceSupplier`/`OrganizationMembership`-level marketplace-listing concern) — not
touched, not composed with this service; that composition is explicitly out of this
task's scope ("Do not implement: Marketplace").

Criteria: profile `status == ACTIVE`, underlying `UserAccount.is_active`, base-profile
completion == 100% (`calculate_caregiver_profile_completion()`, and a new
`calculate_organization_profile_completion()` added to `profiles.py` mirroring that exact
pattern — deliberately NOT reusing `organization_portal`'s own `_completion()`, which
blends in "at least one verified document" for its own UI purposes; Part D needed profile-
completeness and document-verification as two independently testable criteria), and
rolled-up `verification_status == VERIFIED`. Returns structured `eligible: bool` +
`reasons: tuple[str, ...]` + the underlying `VerificationRollupResult` — never only a bare
boolean. Pure read, zero side effects — no auto-activation/publishing wired, since nothing
in the existing workflow clearly requires it (per task instruction).

### Test Level Decision

Level 3 (full regression) was run, not just Level 1/2, because: (a) `resubmit()`/`sync_*()`
introduce new `select_for_update()` row locking — a genuine transaction/concurrency
behavior change; (b) the change reaches through one shared service pair
(`DocumentService`, `VerificationReviewService`) into three apps (`accounts`,
`provider_portal`, `organization_portal`) via one workflow. Both are explicit Level-3
triggers in the governing test-execution policy.

### Deferred (unchanged or newly identified)

1. Customer document verification — still no domain-model support (BG-016, unchanged).
2. Wiring `ActivationEligibilityService` into an actual activation/publishing action —
   new item, BG-018.
3. `profile_completion_percent` auto-recompute on every profile mutation — still open,
   BG-018 (roadmap Phase 1 acceptance criterion 5).
4. Per-service document requirement variation — explicitly not implemented, no evidence
   to ground it (Part A).
