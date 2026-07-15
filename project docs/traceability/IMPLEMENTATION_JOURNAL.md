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

---

## Phase 1.3 — Complete Phase 1 Activation and Profile Completion

**Date:** July 15, 2026
**Branch:** `phase1-activation-completion-final` (from main @ `860640e`)
**Status:** IMPLEMENTED, PR pending merge

### What This Phase Closes

The two remaining Phase 1 items left open by Phase 1.2 (BG-018): (1)
`ActivationEligibilityService.evaluate()` had no caller that actually activated anything;
(2) profile completion percentage was computed by two independent, duplicated field lists
(`calculate_caregiver_profile_completion()`/`calculate_organization_profile_completion()`
in `profiles.py`) rather than one canonical source.

### Part A — Deterministic Profile Completion

`ProfileCompletionService` (new) owns the labeled base-field checklist per profile type —
`CAREGIVER_COMPLETION_FIELDS` (7 fields: display_name, phone, city, specialty, bio,
years_experience, service_radius_km) and `ORGANIZATION_COMPLETION_FIELDS` (6 fields: name,
city, phone, address, description, company_type), each a `(field_name, Persian label)`
pair. `evaluate_caregiver()`/`evaluate_organization()` return a frozen
`ProfileCompletionResult(percent, completed, missing)`. Field-filled semantics preserved
exactly from the pre-refactor per-field checks: `value not in (None, "")` — `0` counts as
filled (a caregiver with 0 years' experience has answered the question, not skipped it),
blank string counts as missing. `calculate_caregiver_profile_completion()`/
`calculate_organization_profile_completion()` in `profiles.py` now delegate their
percentage to this service instead of duplicating the field list; their existing bare-int
signature is unchanged, so `ActivationEligibilityService` and
`apps.portal.services.profile_service` needed no changes. Deliberately did NOT touch or
unify with `provider_portal`/`organization_portal`'s own pre-existing `_completion()`
methods, which blend in "at least one verified document approved" for portal-specific UI
purposes predating this task — see ARCHITECTURE_DECISION_LOG ADM-016 for the full
reasoning. 11 new tests.

### Part B/C — Controlled Activation

`ProfileActivationService.activate_caregiver()/activate_organization()` — see
ARCHITECTURE_DECISION_LOG ADM-016 for the full design decision (activation as an audited
approval record over the existing default-ACTIVE status and existing AuditLog, not a new
lifecycle state). In summary: `transaction.atomic` + `select_for_update()` row lock,
resolves and tenant-checks the profile before enforcing `ACCOUNTS_PROFILE_ACTIVATE`
(cross-tenant returns not-found), refuses owner self-activation as defense-in-depth,
calls `ActivationEligibilityService.evaluate()` unchanged and raises a structured
`ProfileActivationError` with the service's own reasons if ineligible, is an idempotent
no-op if an `accounts.profile.activated` AuditLog entry already exists for that resource,
otherwise sets `status = ACTIVE` (no-op if already ACTIVE) and writes the AuditLog entry.
16 new tests, including a `TransactionTestCase` + `threading.Barrier` concurrency test
proving exactly one AuditLog record is created under a 2-thread race, and a source-
inspection regression test proving `ProfileStatus.SUSPENDED`/`ARCHIVED` are never
referenced (no auto-deactivation was introduced).

### Part C — Activation Authority

New platform-scoped permission `ACCOUNTS_PROFILE_ACTIVATE`, registered in
`apps/kernel/permissions/keys.py`, re-exported through the existing
`apps/accounts/permission_keys.py` and `apps/admin_portal/permission_keys.py` facades.
Granted to `platform_owner`/`platform_admin`/`platform_support` in
`apps/kernel/role_catalog.py:DEFAULT_TENANT_ROLES`, alongside the Phase 1.1
`ACCOUNTS_DOCUMENT_REVIEW` grant — the tuple carrying both was renamed
`DOCUMENT_REVIEW_PERMISSIONS` -> `PLATFORM_VERIFICATION_PERMISSIONS` (grep-verified no
other references existed before renaming). Caregivers/organization admins cannot self-
activate (defense-in-depth check inside the service, independent of RBAC) and cannot
activate across tenants (profile resolution is tenant-scoped before permission
enforcement). No automatic/self-service activation path exists anywhere in the codebase.

### Part D — Minimum Usable UI

Platform/operator side: 4 new `admin_portal` views/routes mirroring the existing
`document_verification_*` view shape exactly (thin controllers, `PermissionService.require`
+ `AccountsError`→404 pattern) — caregiver/organization activation detail pages (status,
key facts, blocking reasons if ineligible) and a POST activate action. The existing
document-verification queue and detail pages now link the owner's name to the new
activation detail page. Owner side: `is_activated`/`activation_eligible`/
`activation_blocking_reasons` added to `ProviderProfileViewModel`/
`OrganizationProfileViewModel` (new fields, existing `completion_percent`/
`completion_missing_labels` untouched), rendered by a new reusable
`ui/components/portal/activation_status.html` component included on both portals' profile
pages, following the existing badge-component convention — no shell/theme redesign. 9 new
admin_portal view tests + 4 new owner-facing presentation tests (2 per portal).

### Query-Count Baseline Update (expected, not a regression)

The new owner-facing activation-status lookup adds a small, fixed number of queries to
every profile-page load (an AuditLog existence check + the `ActivationEligibilityService`
call's own document-list/config-lookup queries) — flat per page load, not per item, so no
N+1 was introduced. The two pre-existing "locked baseline" query-count regression tests
(`ProviderProfileQueryCountTest`, `OrganizationProfileQueryCountTest`) had their hardcoded
expected counts updated (7→10, 7→11 respectively) with their docstrings explaining the
new fixed cost, exactly as their own stated purpose requires ("a regression that turns any
of these into a per-item loop would raise this count").

### Test Level Decision

Level 3 (full regression) was run, once, before PR creation, justified by: activation
behavior is shared across 4 apps through one new service; a new platform-scoped RBAC
permission was added to the canonical registry and role catalog; `ProfileActivationService`
introduces new `select_for_update()` concurrency locking; and this change closes Phase 1
(medium/high-risk merge-prep trigger). 40 new tests, full regression 1808/1808 green
(1768 baseline + 40 new).

### Deferred (explicitly, per task instruction)

1. Automatic deactivation of an already-active profile when verification later becomes
   invalid/expired — no suspension/revalidation workflow exists in this repository to
   hook it into; recorded as BG-019, not implemented as a guess.
2. Customer document verification — still no domain-model support (BG-016, unchanged).
3. Public Instagram-style caregiver profile, galleries, credential presentation, company
   staff-management expansion, customer portal expansion, marketplace/invoice/financial
   workflow — all explicitly out of scope for this task, untouched.

### Phase 1 Acceptance Criteria — Now Complete

All roadmap Phase 1 acceptance criteria (see `IMPLEMENTATION_ROADMAP.md`) are met:
customer/caregiver/organization registration works (verified, no defect); document upload
works; manual review works (approve/reject/correction, Phase 1.1); resubmission works
(Phase 1.2); required-document policy exists (Phase 1.2); verification roll-up works
(Phase 1.2); profile completion is deterministic (Phase 1.3 Part A); activation
eligibility is enforced (Phase 1.2, corrected below); authorized activation works (Phase
1.3 Part B/C, corrected below); private documents remain protected (unchanged); tests are
green; active documentation is synchronized (this update). Phase 1 — Registration and
Verification Workflows is COMPLETE.

---

## Phase 1.3 Remediation — Fix Activation State Semantics (PR #5)

**Date:** July 15, 2026
**Branch:** `phase1-activation-completion-final` (same branch, PR #5 updated in place)
**Status:** IMPLEMENTED, PR #5 updated, not yet merged

### The Root Defect

PR #5 review correctly identified that the Phase 1.3 implementation above had no
canonical profile-state transition. Because `CaregiverProfile.status`/
`OrganizationProfile.status` already defaulted to `ProfileStatus.ACTIVE` at registration
(a fact Phase 1.3 treated as a fixed, unchangeable constraint — see ADM-016's original
"apparent circularity" reasoning), `ProfileActivationService` never actually needed to
flip a profile's status in the ordinary case. "Activation" degenerated into "write an
`AuditLog` entry," and `ProfileActivationService.is_activated()` read that `AuditLog`'s
existence — not `profile.status` — to answer "is this profile currently active." A
historical log became a live source of truth, which is exactly backwards, and which a new
regression test (`AuditLogIsNotSourceOfTruthTest`) now proves was possible: writing an
`accounts.profile.activated` `AuditLog` entry by hand, with no real transition behind it,
previously would have made `is_activated()` return `True`.

### The Fix

`profile.status` is now the sole source of truth for current activation state.
`AuditLog` is written on every real transition as permanent historical evidence of when
and by whom it happened, and is never read back to answer "is this active right now."
Concretely, this required breaking the original circularity at its actual root — the
registration default, not the eligibility check:

1. **Registration bootstrap now creates DRAFT profiles.**
   `RegistrationService.create_caregiver()`/`create_company_admin()` and
   `ensure_caregiver_profile()` (the multi-role attach helper) now explicitly pass
   `status=ProfileStatus.DRAFT` at creation. `DRAFT` already existed in the
   `ProfileStatus` enum — no new status value was invented, satisfying the remediation
   task's explicit instruction to reuse an existing pre-activation state rather than add
   one. Repository-wide grep confirmed these are the *only* three production code paths
   that create a `CaregiverProfile`/`OrganizationProfile` at all — every other creation
   site (test fixtures across `accounts`/`provider_portal`/`organization_portal`/
   `admin_portal`/`orders`/`booking`/`commission`; the `seed_demo_people`/
   `seed_demo_accounts` dev-only commands) uses `.objects.create()` directly, outside the
   canonical registration layer.
2. **No model-field default change, no migration.** `CaregiverProfile.status`/
   `OrganizationProfile.status`'s own Django field default remains `ProfileStatus.ACTIVE`.
   Changing it would have silently flipped status for every one of the call sites named
   above, including test fixtures in apps this task is explicitly forbidden from touching
   (`orders`, `booking`, `commission` — where `OrderEligibilityService.is_eligible()`/
   `is_organization_supplier_active()` read `organization.status == ACTIVE` for unrelated
   marketplace/financial-core purposes). Passing an explicit `status=` override at the
   three canonical entry points is the smaller, correct-scope fix.
3. **`ActivationEligibilityService` no longer requires `status == ACTIVE`.** This was the
   literal circularity: under the old rule, a DRAFT profile could never be "eligible"
   (since eligibility required already being ACTIVE), so it could never be activated. The
   corrected rule blocks only `SUSPENDED`/`ARCHIVED` (`BLOCKING_PROFILE_STATUSES`); DRAFT
   and ACTIVE are both non-blocking, evaluable statuses. The reason code changed from
   `profile_status_not_active:{status}` to `profile_status_blocked:{status}`.
4. **`ProfileActivationService._activate()` performs the real transition.** DRAFT +
   eligible now genuinely sets `status = ACTIVE` and returns a structured
   `ProfileActivationResult(profile, previous_status, status, transitioned)`. Idempotency
   is now judged by `profile.status == ACTIVE` directly — a repeated call on an
   already-ACTIVE profile short-circuits (`transitioned=False`) without re-running
   eligibility, so an activated profile stays activatable even if some later fact (e.g. an
   expired document) would fail a *fresh* eligibility check — that is the same, already
   explicitly deferred deactivation/revalidation gap (BG-019), not a new one.
   `AuditLog.before_snapshot`/`after_snapshot` now capture the real
   `{"status": "draft"}` -> `{"status": "active"}` transition.
5. **`is_activated()` reads `profile.status` directly** — `profile.status ==
   ProfileStatus.ACTIVE`, no query at all. This also *removed* one query from every
   provider/organization profile page load (the old `AuditLog.objects.filter(...).exists()`
   check), which is why the two locked query-count regression tests
   (`ProviderProfileQueryCountTest`, `OrganizationProfileQueryCountTest`) had their
   baselines reduced by exactly one (10→9, 11→10) rather than increased.
6. **UI now distinguishes SUSPENDED explicitly.** A new `activation_profile_status` field
   was added to both portal ViewModels (the raw `ProfileStatus` value), and
   `ui/components/portal/activation_status.html` plus the two `admin_portal`
   activation-detail templates gained an explicit "معلق" / "پروفایل معلق شده است"
   (Suspended) badge branch, rather than folding SUSPENDED into the generic "not eligible"
   case.

### Tests

16 new/renamed focused tests across `test_profile_activation.py` (accounts, rewritten:
DRAFT fixtures, `ProfileActivationResult` field assertions, `AuditLogIsNotSourceOfTruthTest`
proving a hand-written `AuditLog` entry does *not* imply activation,
`EligibilitySemanticsTest` proving DRAFT is eligible and ACTIVE remains evaluable,
organization-SUSPENDED coverage), `test_activation_eligibility.py` (reason-code rename,
archived/draft-eligible/organization-suspended coverage), `test_registration.py` (DRAFT-
on-registration assertions for both caregiver and organization), and
`test_profile_activation.py` (admin_portal, suspended-activation-refused and
suspended-detail-shows-suspended). Full regression 1824/1824 green (1808 baseline + 16).

### Test Level Decision

Level 3 (full regression), run once before updating PR #5, justified by: this remediation
changes what status a real user's caregiver/organization profile starts in — a
foundational, widely-depended-on fact (registration bootstrap); it changes the
activation-eligibility precondition logic; and it rewrites the same
`select_for_update()`-guarded service already covered by Level 3 in the original Phase 1.3
run. The status-default change is upstream of `apps.orders`/`apps.accounts.services
.supplier_bridge` marketplace/financial-core eligibility reads even though those apps'
own code was not modified, which the full suite exercises.

### Deferred (unchanged)

Automatic deactivation of an already-active profile when verification later becomes
invalid/expired remains deferred (BG-019) — this remediation did not add or remove that
gap, only made the *current* activation state (DRAFT/ACTIVE/SUSPENDED) accurately
reflected by `profile.status` at all times.

---

## Phase 2.1 — Caregiver Professional Profile Foundation

**Date:** July 15, 2026
**Branch:** `phase2-caregiver-professional-profile-foundation` (from main @ `0c9d70c`)
**Status:** IMPLEMENTED, PR pending

### Current-State Implementation Matrix (Part A)

| Capability | Existing implementation | Reusable | Missing |
|---|---|---|---|
| Public biography / bio text | `CaregiverProfile.bio`, edited via `CaregiverProfileUpdateService.update_professional_info()`, read by `CaregiverPublicProfileService` | Yes — reused as-is | — |
| Professional headline/title | `CaregiverProfile.specialty` (free-text, already rendered as the public profile subtitle) | Yes — reused as-is, no new field | — |
| Years of experience | `CaregiverProfile.years_experience` | Yes | — |
| Service area/location summary | `CaregiverProfile.city` (already public) | Yes | — |
| Languages | No field/model anywhere | — | Not added — no evidence to model it (per governance) |
| Avatar/cover image | `CaregiverProfile.avatar/cover_image`; public_site deliberately shows only `avatar_initial`, never the image URL (pre-existing, consistent across directory/organization/profile) | Yes — left unchanged (existing, deliberate convention; "media storage strategy for production" is an acknowledged, separate roadmap blocker) | — |
| Activation/verification badge | `ActivationEligibilityService`, `ProfileActivationService`, `verification_status` — already surfaced on the public profile as `verification_label`/`is_verified` | Yes | — |
| Skills | No model anywhere | — | `CaregiverSkill` (new) |
| Structured experience | No model anywhere | — | `CaregiverExperience` (new) |
| Services offered (caregiver-editable) | `ServiceSupplier.service_categories` + `SupplierRegistry.set_service_categories()` + `CaregiverProfileUpdateService.update_professional_info(service_category_ids=…)` — full CRUD already implemented (Epic 06 Sprint 2) | Yes — fully reused, zero new code | — |
| Services offered (public display) | `CaregiverProfileViewModel.service_names`, already resolved from active `ServiceCategory` rows | Yes | — |
| Verified credential summary (public) | Only a single coarse `verification_status`/`is_verified` flag; no per-credential-type public summary | Partially | `PublicCredentialSelector` (new) |
| Public profile page/route | `public_site:caregiver-profile`, `CaregiverPublicProfileService.get_profile()`, safe-404 on ineligible/unknown | Yes | Skills/experience/credentials sections; stricter eligibility (see below) |
| Public-profile eligibility | `common.is_publicly_visible()` — checked `profile.status == ACTIVE` + org-membership-active only | Partially | `verification_status == VERIFIED` + account `is_active` (added locally, see ADM-017) |
| Caregiver-side profile editing UI | `provider_portal` basic/professional-info edit pages, avatar/cover upload, document upload/status, activation status, public-preview link | Yes | Skills/experience management pages |
| Reviews/reputation summary | `ReputationService`, already surfaced on both authenticated and public profile pages | Yes | — |
| Private document protection | `VerificationDocument.file` stored under `private/` — never publicly URL-servable, by storage location | Yes | — |

### Canonical Ownership (Part B)

See `traceability/ARCHITECTURE_DECISION_LOG.md` ADM-017, Decision 1. In short:
`CaregiverProfile` remains the sole caregiver aggregate. `CaregiverSkill`/
`CaregiverExperience` are new, minimal FK child tables (mirroring `VerificationDocument`'s
existing shape). No new "professional profile" table, no second identity, no duplicated
biography/headline/services-offered field.

### Public/Private Data Boundary (Part F/G/H)

Never publicly exposed: `national_id` (not modeled at all), phone, private email, private
address, `VerificationDocument.file` (private storage path), document number (not
modeled), reviewer identity, rejection/correction reason, internal audit data. Verified by
`test_no_private_document_fields_leak_into_the_viewmodel` (pre-existing, still green) and
new tests (`test_public_context_excludes_private_fields`,
`test_credential_summary_never_includes_file_url_or_reviewer`,
`test_selector_never_exposes_file_field`).

Public-profile eligibility (Part H) — see ADM-017 Decision 2 for the full reasoning. Final
rule, enforced by `CaregiverPublicProfileService.get_profile()`:
`common.is_publicly_visible(supplier)` (profile status ACTIVE + org-membership-active,
unchanged) AND `verification_status == "verified"` (new) AND the owning account's
`user.is_active` (new). Deliberately NOT changed in the shared `common.py` function the
caregiver directory/home-page listings also use — see Deferred below.

### Credential-Summary Derivation (Part G)

`PublicCredentialSelector.for_caregiver(caregiver)` — see ADM-017 Decision 3. APPROVED +
not-expired + applicable-type-for-caregiver + owned-by-this-caregiver only. Returns
document_type, a public label, and expiry_date — nothing else.

### Skills (Part D)

`CaregiverSkillService.add_skill()/remove_skill()/list_skills()`. `unique_together`
(DB `UniqueConstraint`) on (caregiver, name) is the backstop; the service pre-checks
case-insensitively (`name__iexact`) and translates a race-condition `IntegrityError` into
the same controlled `AccountsError`. No skill catalog/taxonomy — no evidence to justify
one. `is_visible` flag (default `True`) lets a caregiver hide a skill without deleting it;
the public selector only reads `is_visible=True` rows.

### Experience (Part E)

`CaregiverExperienceService.create()/update()/delete()/list_experiences()`. `end_date`
optional even when not current (no evidence to require it); `is_current=True` forces
`end_date=None` server-side regardless of what was submitted. A `CheckConstraint`
(`end_date IS NULL OR end_date >= start_date`) is the DB-level backstop for the same rule
the service already validates. No employment-verification workflow.

### Services Offered (Part F)

No new code — see the ownership matrix above. `CaregiverProfileUpdateService
.update_professional_info(service_category_ids=…)` already lets a caregiver replace their
offered-services set (bulk-set semantics; a `MultipleChoiceField` structurally prevents
duplicate submissions). The only genuinely new work was the public-facing display, which
already existed too (`service_names` on `CaregiverProfileViewModel`) — confirmed, not
re-implemented.

### UI/Routes (Part J)

Provider portal (new): `/provider/profile/skills/` (list + add + remove),
`/provider/profile/experience/` (list), `/provider/profile/experience/add/`,
`/provider/profile/experience/<id>/edit/`, `/provider/profile/experience/<id>/delete/`.
Provider portal (extended): profile page now shows skill/experience counts with links to
the management pages, and a "which verified credential types will appear publicly" panel
(`public_credential_labels`). "Preview public profile" was already implemented
(`profile_header.html`'s `public_preview_url` prop) — confirmed, not re-implemented.
Public site (extended): `caregiver_profile.html` gained skills/experience/credentials
sections, following the existing bio/services/reviews section pattern exactly (no new
visual language, no theme changes).

### Security and Privacy (Part K)

Owner-only editing is enforced structurally by `_guard_with_caregiver()` (resolves
`request.user.caregiver_profile`, an account-scoped attribute — a customer or
organization-only user has none, `PermissionDenied` -> 403) plus a second,
service-level check on every mutation (`CaregiverSkillService`/`CaregiverExperienceService`
filter every query by `caregiver=caregiver`, the caller's own resolved profile — never a
caller-supplied id trusted as ownership proof). Cross-tenant is a strict subset of
cross-caregiver here (a cross-tenant user cannot resolve another tenant's
`caregiver_profile` at all). Verified directly by
`test_another_caregiver_cannot_remove_skill`, `test_cannot_update_another_caregivers_experience`,
`test_cross_tenant_cannot_edit_experience` (404, not a silent no-op).

### Test Level Decision

Level 3 (full regression), run once before PR creation, justified by: two new models with
a real migration; a public/private security-boundary change on the caregiver public
profile page; and the workflow spans `accounts`, `provider_portal`, and `public_site`.

### Deferred (explicitly, recorded as new backlog items — see `quality/COMPLETION_BACKLOG.md`)

1. Gallery, posts, feed, follows, likes, comments, stories, messaging — explicitly out of
   this task's scope, untouched.
2. Caregiver financial dashboard, caregiver order dashboard, Company Portal expansion,
   Customer Portal expansion, Marketplace offer workflow, invoice workflow, financial
   engine changes, payment/settlement changes — explicitly out of scope, untouched.
3. AI verification implementation, service-specific credential enforcement, public
   document-file access — explicitly out of scope, untouched (and the last one remains
   structurally impossible — private storage path, never surfaced).
4. Directory/home-page listing eligibility does not yet require `verification_status ==
   VERIFIED` or account `is_active` the way the single profile page now does (ADM-017
   Decision 2) — an inconsistency ("found in the directory, but its own page 404s") this
   phase deliberately did not fix, since correcting discovery/listing eligibility is a
   separate, out-of-scope decision with its own blast radius (~80 pre-existing tests
   depend on the current, looser rule).
5. Languages field — not modeled, no evidence to justify adding it.
6. Skill catalog/taxonomy, skill endorsements/rankings, employment verification — not
   built, per explicit governance ("do not build endorsements, likes, rankings, or
   skill-verification workflows in this slice").

### Phase 2.1 Acceptance Criteria — Status

Caregiver can edit public professional information (existing, reused) — met. Caregiver can
manage skills — met (new). Caregiver can manage experience — met (new). Caregiver can
manage services offered — met (existing, reused). Public caregiver page exists — met
(existing route, extended). Only activated and verified caregivers are public — met (new
local eligibility rule). Safe verified credential summaries are shown — met (new
selector). Original credential files remain private — met (storage location, never
surfaced). Private identity/contact/review data is absent — met (verified by tests).
Authorization and tenant isolation are enforced — met (verified by tests). Tests pass — met
(50 new, full regression 1874/1874). Active documentation is synchronized — met (this
update). **Phase 2.1 is complete; the remainder of roadmap Phase 2 (gallery, certificates-
as-gallery, orders/history, extended financial overview) remains a separate, future
slice — not claimed complete here.**

---

## Phase 2.1 Remediation — Close Public Caregiver Visibility Gap (BG-022)

**Date:** July 15, 2026
**Branch:** `phase2-caregiver-professional-profile-foundation` (same branch, PR #6 updated in place)
**Status:** IMPLEMENTED, PR #6 updated, not yet merged

PR #6 review found that Phase 2.1's own eligibility fix (`verification_status ==
VERIFIED` + account `is_active`) was added only to the single caregiver profile detail
page, not to the caregiver directory or home-page listings — a caregiver could appear in
a public listing while their own detail page 404'd. Recorded and deliberately deferred as
BG-022 in the original Phase 2.1 slice (ARCHITECTURE_DECISION_LOG ADM-017 Decision 2);
this remediation closes it, inside the same PR, per governance instruction.

### Public Entry-Point Matrix (Part 1)

| Entry point | Selector/service | Current eligibility enforcement (before this fix) | Fix required |
|---|---|---|---|
| `/find-a-caregiver/<supplier_id>/` (detail) | `CaregiverPublicProfileService.get_profile()` | `common.is_publicly_visible()` (profile ACTIVE + membership) **plus** a local, duplicated check (`verification_status == VERIFIED` + account `is_active`) | Remove the local duplicate; rely solely on the now-unified canonical function |
| `/find-a-caregiver/` (directory search) | `CaregiverDirectoryService.search()` → `_filter_candidates()` | `common.is_publicly_visible_attrs()` (profile ACTIVE + membership only) | Extend the canonical function (fixes this automatically) |
| `/` home page — featured caregivers | `CaregiverDirectoryService.featured()` (via `HomePageService`) | Same as directory (shares `_filter_candidates()`) | Same fix, automatic |
| `/` home page — city filter options | `CaregiverDirectoryService.available_cities()` | Same as directory | Same fix, automatic |
| `/caregivers/` (static marketing page) | None — `render(request, "public_site/caregivers.html")`, no real caregiver data queried | N/A — no data exposed | None |
| `GET /api/v1/discovery/suppliers/` | `DiscoveryService.search()` → `SupplierSearchService.filter_suppliers()` | Permission-gated (`DISCOVERY_SUPPLIERS_READ`) — **not** a default-granted role in `DEFAULT_TENANT_ROLES`; no anonymous/public access path exists to it. An internal/operator tool (Module 17B), not a public marketing surface. Applies `ServiceSupplier.status == ACTIVE` only, no `CaregiverProfile`-level eligibility at all — a deliberate difference from the public surfaces, since internal operators/matching may legitimately need to see not-yet-public suppliers. | None — out of BG-022 scope ("Do not alter owner or platform-admin visibility"); this is neither owner nor public, it is internal/operator tooling, confirmed via its permission requirement |
| `apps.discovery.services.search_service.SupplierSearchService` (internal matching/booking building block) | N/A | `ServiceSupplier.status == ACTIVE` only — used by the matching engine and the above internal API, not a public listing | None — out of scope (Marketplace/matching internals, explicitly not to be touched) |
| Sitemap / RSS / indexing feed | N/A | Does not exist in this repository | None |
| Related-recommendation widgets | N/A | Does not exist in this repository (no "similar caregivers" feature) | None |

### Root Visibility Defect

`common.is_publicly_visible_attrs()` (the function `directory_service.py`'s `_filter_candidates()` — used by `search()`, `featured()`, and `available_cities()` — already called) was a *different, looser* rule than the one Phase 2.1 added locally to `CaregiverPublicProfileService.get_profile()`. Two independent implementations of "is this caregiver publicly visible" existed for a matter of days — exactly the "second, parallel eligibility system" this project's governance repeatedly warns against.

### Canonical Public-Visibility Policy (Part 2)

Rather than introduce a new, differently-named class (`PublicCaregiverVisibilityPolicy`, etc.), the existing `apps.public_site.services.common.is_publicly_visible_attrs()`/`is_publicly_visible()` — already the single, batched, shared implementation `directory_service.py`'s own docstring described as "exactly one implementation of both the resolution and the eligibility rule" — was extended in place and is now genuinely canonical: every public entry point calls it, directly or via `bulk_supplier_attrs()`/`supplier_entity_attrs()`. Introducing a differently-named wrapper alongside it would have created exactly the duplication this remediation exists to remove.

The canonical rule now requires ALL of:
- `profile_status == "active"` (excludes DRAFT, SUSPENDED, ARCHIVED — a single check, since those are mutually exclusive string values)
- `verification_status == "verified"`
- the owning account's own `is_active` (resolved via `entity.user` for caregivers / `entity.admin_user` for organizations)
- organization-membership active, for organization-affiliated caregivers only (unchanged, pre-existing)

Not applicable / not added: no `ServiceSupplier`-level "public visibility" boolean flag exists anywhere in the repository to reuse (confirmed by inspection) — none was invented. Tenant/scope validity is enforced structurally by every entry point's own tenant-scoped query (`ServiceSupplier.objects.get(..., tenant_id=tenant_id)` / `SupplierSearchService.filter_suppliers()`'s `tenant_id=query.tenant_id` filter) — not a new check inside the eligibility function itself.

### Public Surfaces Corrected (Part 3)

Directory search, home-page featured cards, home-page city filter, and the single-profile detail page all now apply the identical rule (confirmed by `CanonicalVisibilityAcrossSurfacesTest`, which checks all four in the same test per scenario). Owner-facing (`provider_portal`) and platform-admin-facing (`admin_portal`) visibility were not touched — neither reads `common.is_publicly_visible_attrs()`, both use their own, already-correct, unrelated ownership/permission checks.

### Query and Performance Impact (Part 4)

`bulk_supplier_attrs()` already resolved the caregiver/organization entity and organization-membership status in exactly 2 batched queries regardless of candidate count (pre-existing, Architecture Review M1/M2). This fix adds the account (`user`/`admin_user`) relation via `select_related()` on the same already-batched query in `resolve_supplier_entities_bulk()` (`apps.accounts.services.supplier_bridge`) — a JOIN, not a new query. Verified directly: `ListingQueryCountTest.test_eligibility_resolution_query_count_is_constant_regardless_of_candidate_count` proves `bulk_supplier_attrs()` costs exactly 2 queries whether given 3 or 13 candidates.

A genuine, pre-existing per-candidate query cost was discovered during this verification — `DiscoveryRankingService.rank()` (one `availability_capacity_rule` query per candidate) and `CaregiverDirectoryService._build_card()` (one `reviews_reputation_snapshot` + one `orders_order` completed-jobs query per card). This is unrelated to eligibility/visibility (it is ranking-score and card-enrichment cost) and pre-dates this remediation — not fixed here, since touching `apps.discovery`'s ranking algorithm or the reputation/completed-jobs enrichment path is a separate, unrelated performance task, out of BG-022's narrow scope. Recorded as `quality/DEFECT_AND_RISK_REGISTER.md` KL-012.

Simplifying `CaregiverPublicProfileService.get_profile()` (removing its now-redundant local eligibility check) actually *reduced* the detail page's own query count by one (14 → 13, confirmed by the existing `PublicProfileQueryCountTest`).

### Tests (Part 5)

New file `apps/public_site/tests/test_public_visibility_policy.py` (13 tests):
`CanonicalVisibilityAcrossSurfacesTest` (8 tests — active+verified visible everywhere;
DRAFT/SUSPENDED/ARCHIVED/unverified/pending-verification/inactive-account/inactive-membership
hidden everywhere, each checked against directory search, home featured, detail-service,
and the detail HTTP route in one test), `ListingCountAndPrivacyTest` (3 tests — hidden
profiles don't inflate directory `total_count`, hidden profiles absent from
`available_cities()`, private contact fields absent from directory HTML), and
`ListingQueryCountTest` (2 tests — eligibility resolution is O(1), directory search
remains correct at scale).

Existing pre-existing test fixture default corrected: `PublicSiteTestCase
._create_caregiver_supplier()`'s `verification_status` default changed from `"unverified"`
to `"verified"` (`apps/public_site/tests/helpers.py`) — the ~80 pre-existing
`test_directory_service.py`/`test_home_service.py` tests never asserted anything about
verification status (confirmed by grep before changing the default) and continued
passing unmodified once the default matched what a "normal, visible caregiver" fixture
should represent.

### Test Level Decision

Level 3 (full regression), run once before updating PR #6, justified by: this remediation
changes a public/private security boundary shared across multiple selectors
(`apps.public_site`) and reaches into `apps.accounts` (`supplier_bridge.py`); the fix is
exactly the kind of "shared public selector" change the task's own Level 3 trigger list
names explicitly.

### Deferred (unchanged, or newly recorded)

1. `quality/DEFECT_AND_RISK_REGISTER.md` KL-012 (new) — pre-existing per-candidate ranking/
   card-building query cost, unrelated to eligibility, not fixed (out of scope).
2. Gallery, financial overview, orders + history (BG-021, unchanged) remain deferred.
3. `GET /api/v1/discovery/suppliers/` and `apps.discovery.services.search_service
   .SupplierSearchService` were confirmed, not modified — internal/operator tooling
   (permission-gated, no default role grant), a different trust boundary than the public
   surfaces this remediation covers.

### BG-022 Status

**RESOLVED.** All four real public entry points (directory search, home-page featured
cards, home-page city filter, detail page) now apply the identical canonical
public-visibility rule. 13 new tests, zero regressions, full regression 1887/1887 green.

---

## Sprint 2.2 — Caregiver Professional Profile: Gallery and Media Portfolio (2026-07-15)

First sprint on a fresh branch (`phase2-caregiver-gallery-media`, from `main` @ `c5259b3`)
after PR #6 (Phase 2.1 foundation + BG-022 remediation) was merged. Delivers a
caregiver-managed, Instagram-like professional photo portfolio — explicitly "a
professional portfolio, not a social network" (no posts/feed/likes/comments/follows/
stories/messaging).

### Current Media Architecture Inspection

| Capability | Existing | Reusable | Missing |
|---|---|---|---|
| Single-image profile fields (avatar/cover) | `CaregiverProfile.avatar`/`.cover_image` (`ImageField`, `apps/accounts/models/profiles.py`) | Yes — pattern copied, field type never touched by gallery | A *list*-type image model (avatar/cover are singular) |
| Private-file-owned-by-caregiver pattern | `VerificationDocument` (`apps/accounts/models/media.py`) — UUID PK, FK to caregiver, no `TenantAwareModel`, `CheckConstraint` for exactly-one-owner | Model *shape* (UUID PK, FK+`related_name`, no `TenantAwareModel`) reused via `CaregiverSkill`/`CaregiverExperience`'s already-established variant of it | `VerificationDocument` itself is private/PDF-oriented — not reused directly (gallery images are public, image-only) |
| List-type caregiver-owned child model | `CaregiverSkill`/`CaregiverExperience` (Phase 2.1, `apps/accounts/models/professional_profile.py`) | Yes — `CaregiverGalleryItem` copies this exact skeleton (plain `models.Model`, UUID PK, FK+`related_name`, `display_order`, `is_visible`, no `TenantAwareModel`) | Neither existing model holds a file |
| Image upload validator | `ProfileMediaService._validate_image()` (Pillow content-sniff, 5MB cap, JPEG/PNG/WEBP) | Yes — extracted verbatim to `apps.accounts.services.image_validation.validate_image()`, called by both `ProfileMediaService` and the new `CaregiverGalleryService` | — |
| Upload-path generator | `media_paths.py` (`caregiver_avatar_path`, `caregiver_cover_path`, `verification_document_path`) | Yes — `caregiver_gallery_path()` added alongside, same `uuid4()`-filename, type-scoped-directory pattern | — |
| Storage backend | Plain Django `FileSystemStorage` (`MEDIA_ROOT`/`MEDIA_URL`, `config/settings/base.py`); no S3/django-storages | Yes — no change needed; gallery images live under `public/`, exactly like avatar/cover | Production storage strategy (local disk) remains an acknowledged, pre-existing open item (BG-021's original dependency note) — unchanged, not worsened |
| Public/private file-serving split | `public/` vs `private/` path-prefix convention (`config/urls.py`'s dev `static()` helper only serves `MEDIA_ROOT/public`); `admin_portal.views.document_verification_file` streams `private/` documents to authorized reviewers only | Yes — gallery images use `public/`, need no authenticated streaming view | — |
| Thumbnail/derivative-image generation | None anywhere in the repo — `ProfileMediaService`'s own docstring states this as a deliberate simplicity choice ("no derivative image sizes") | N/A | Genuinely absent; Sprint 2.2 follows the same choice (deferred, not a defect — see Deferred section below) |
| Audit logging on media mutation | `AuditLog` written only for document *resubmission* (`document_service.py`); avatar/cover/skill/experience CRUD write no audit entries | N/A (convention is "no audit for this class of mutation") | Gallery upload/edit/reorder/remove follow the same no-audit convention, matching avatar/cover/skills/experience, not documents |
| Soft-delete / archive mixin | `apps.common.models.SoftDeleteMixin`/`ActiveManager` exist but are used by zero `apps.accounts` models | No — `apps.accounts`'s own convention is hard delete (`VerificationDocument`, `CaregiverSkill`, `CaregiverExperience` all hard-delete) | A soft-delete/archive field would be a new, non-conforming pattern for this app — not introduced (see ADM-018 Decision 4) |
| Tenant ownership pattern | `TenantAwareModel` (own `tenant_id` column) vs. transitive-via-FK (no own column) — `CaregiverSkill`/`CaregiverExperience`/`VerificationDocument` all use the transitive pattern | Yes — `CaregiverGalleryItem` follows the transitive pattern, no own `tenant_id` | — |
| Generic Media/Attachment model | None found repo-wide (confirmed by search before implementing) | N/A | A dedicated `CaregiverGalleryItem` was built instead — a gallery item has exactly one owner type, so `VerificationDocument`'s own reasoning for rejecting a polymorphic model applies even more strongly here |
| Test-image construction helper | `_png_bytes()` duplicated in `provider_portal`/`organization_portal` test files (real, Pillow-verifiable 1x1 PNG via `SimpleUploadedFile`) | Yes — copied verbatim into the three new gallery test files, matching this repo's existing style of duplicating this small helper rather than centralizing it | — |

No genuine architectural blocker was found — proceeded directly to implementation per the
task's own instruction.

### Canonical Gallery Model

`CaregiverGalleryItem` (`apps/accounts/models/gallery.py`) — plain `models.Model`, UUID PK,
single FK to `CaregiverProfile` (`related_name="gallery_items"`, `on_delete=CASCADE`),
`image` (`ImageField`, `caregiver_gallery_path()`), `caption`/`alt_text` (both
`CharField(max_length=255, blank=True)` — `alt_text` for accessibility, distinct from
`caption`), `display_order` (`IntegerField(default=0)`), `is_visible`
(`BooleanField(default=True)`), `created_at`/`updated_at`. `Meta.ordering =
["display_order", "created_at"]`, one composite index `(caregiver, display_order)`. No
`TenantAwareModel` base — tenant derived transitively via `caregiver.user.tenant`, the
same pattern `CaregiverSkill`/`CaregiverExperience` already established. Never touches
`CaregiverProfile.avatar`/`.cover_image` — avatar is the primary identity image, cover is
the profile header image, a gallery item is one entry in a list of portfolio photos; three
distinct responsibilities, never conflated. See `ARCHITECTURE_DECISION_LOG.md` ADM-018 for
the full ownership/storage/deletion/limit reasoning.

### Image Validation

Extracted `ProfileMediaService`'s former private `_validate_image()` into a new, shared,
public function: `apps.accounts.services.image_validation.validate_image()` — behavior is
byte-for-byte unchanged (5MB cap checked first, then Pillow `Image.open().verify()` on the
file's own bytes, never the client-supplied `Content-Type` header; only JPEG/PNG/WEBP
accepted). `ProfileMediaService` now imports and re-exports the same constants
(`MAX_IMAGE_BYTES`, `ALLOWED_IMAGE_FORMATS`) so no existing importer of that module breaks
(grep-verified: nothing outside `profile_media_service.py` referenced these before this
change). `CaregiverGalleryService` calls the identical function — one implementation of
"is this a valid image," not two.

### Gallery Business Rules and Mutation Service

`CaregiverGalleryService` (`apps/accounts/services/caregiver_gallery_service.py`) —
owner-authorized only, no RBAC permission key (ownership via
`request.user.caregiver_profile` is the boundary, mirroring
`CaregiverSkillService`/`CaregiverExperienceService`):

- `add_item(caregiver, *, image, caption="", alt_text="")` — validates caption/alt-text
  length (255 chars, matching the field width), validates the image, then row-locks the
  owning `CaregiverProfile` (`select_for_update()`) for the count-check-then-create so two
  concurrent uploads from the same caregiver cannot both observe `count < MAX` and both
  succeed — `MAX_GALLERY_ITEMS_PER_CAREGIVER = 12` has no unique-constraint backstop the
  way `uq_caregiver_skill_name` gives `add_skill()`.
- `update_item(caregiver, *, item_id, caption, alt_text, is_visible)` — re-verifies
  `caregiver=caregiver` in the same `.get()` call that resolves the row (the filter itself
  is the authorization boundary), same shape as `CaregiverExperienceService.update()`.
- `reorder(caregiver, *, ordered_item_ids)` — row-locks the owning profile and every one of
  the caregiver's own gallery items, then requires `ordered_item_ids` to be exactly the
  caregiver's own item ids, each exactly once — any foreign id, missing id, or duplicate
  refuses the *entire* operation (no partial reorder), verified directly by
  `test_reorder_with_foreign_item_id_refused`/`test_reorder_with_missing_item_refused`.
- `remove_item(caregiver, *, item_id)` — row-locks the target item (ownership-filtered),
  deletes the physical file (`image.delete(save=False)`) before deleting the row — never
  leaves an orphaned file, mirroring `ProfileMediaService._replace()`'s own convention.
  Verified not to touch avatar/cover
  (`test_removing_gallery_item_does_not_touch_avatar_or_cover`).

Provider-portal views (`profile_gallery_view`, `profile_gallery_item_edit_view`,
`profile_gallery_item_remove_view`, `profile_gallery_item_move_view`) are thin controllers
— `_guard_with_caregiver()` then a service call then a redirect/render, matching
`ProviderPortalOrmDisciplineTest`'s zero-ORM-in-views rule (verified: no `.objects.`/
`.filter(`/`.save(`/`.delete()` pattern appears in the added view code; `caregiver
.gallery_items.get(...)`/`.count()` mirror the pre-existing, already-guardrail-compliant
`caregiver.experiences.get(...)` idiom). Reordering is exposed as simple "move up"/"move
down" actions per item (not a drag-and-drop widget) — theme-independent, keyboard/
screen-reader operable by construction (plain `<form method="post">` + `<button>`, no new
JS dependency), and each move computes the full desired order client-side-free by swapping
two adjacent ids before calling `reorder()`.

### Public Selector and Visibility Composition

`CaregiverPublicProfileService._gallery()` (`apps/public_site/services/profile_service.py`)
adds no eligibility check of its own. It runs only after `get_profile()`'s existing,
canonical `common.is_publicly_visible(supplier)` gate (BG-022) has already passed, then
filters to `caregiver.gallery_items.filter(is_visible=True)` — the identical per-item
pattern `_skills()`/`_experience()` already established. A caregiver failing the canonical
policy (DRAFT/SUSPENDED/ARCHIVED/unverified/pending-verification/inactive-account/
inactive-membership) never has their gallery resolved at all — proven directly by
`test_draft_caregiver_profile_exposes_no_gallery`/
`test_suspended_caregiver_profile_exposes_no_gallery`/
`test_unverified_caregiver_profile_exposes_no_gallery`, each asserting `get_profile()`
returns `None` entirely (not merely an empty gallery on an otherwise-populated profile).
No second visibility rule was written.

### Public Surfaces Corrected/Extended

Only the single-caregiver detail page (`caregiver_profile.html`) gained a gallery section
— directory cards, home-page featured cards, and city-filtered listings show only
existing summary fields (name, city, specialty, rating), unchanged; a gallery grid was
never in scope for those listing surfaces (strict scope: "Extend the existing public
caregiver profile with a gallery section").

### Query/Performance Impact

`_gallery()` adds exactly one fixed query
(`caregiver.gallery_items.filter(is_visible=True)`) to `get_profile()`'s existing pipeline
— confirmed by `PublicGalleryQueryCountTest.test_gallery_resolution_is_a_single_bounded_
query` (`assertNumQueries(14)` with 5 gallery items present, same as with 0). The
pre-existing `PublicProfileQueryCountTest` (Phase 2.1) locked baseline moved 13 -> 14
accordingly — documented inline in that test as an intentional, fixed-cost addition, not a
regression. The provider profile page's own locked baseline
(`ProviderProfileQueryCountTest.test_profile_page_query_count_bounded`) moved 12 -> 13 for
the equivalent `gallery_count` count query. Both are proven O(1) by dedicated tests, not
guessed.

### Files Changed

See `traceability/CHANGE_LEDGER.md` CL-025 and `traceability/FILE_CHANGE_REGISTER.md`'s
"2026-07-15 — Sprint 2.2" section for the complete, categorized list.

### Security/Privacy Behavior Proven by Tests

Owner may upload/edit/reorder/remove own items; another caregiver cannot mutate another
caregiver's items (structurally — the `caregiver=caregiver` filter is the boundary — and
directly, via `test_another_caregiver_cannot_edit`/`test_another_caregiver_cannot_remove`/
`test_another_caregiver_cannot_reorder_items_they_do_not_own`); a customer/unauthenticated
user cannot upload at all (403, `_guard_with_caregiver()`); cross-tenant access denied
(404, `test_cross_tenant_cannot_edit`); non-image and corrupted files rejected
(`test_non_image_file_rejected`/`test_corrupted_image_rejected`); oversized images
rejected (`test_oversized_image_rejected`); hidden/removed items never public
(`test_hidden_item_does_not_appear`/`test_removed_item_does_not_appear`); a
DRAFT/SUSPENDED/unverified caregiver's gallery is entirely unreachable, not just filtered
(three dedicated tests, above); the gallery limit is enforced atomically under the
owning-profile row lock (`test_gallery_limit_enforced`, and per-caregiver independence via
`test_gallery_limit_is_per_caregiver`); no storage path or filesystem metadata is ever
rendered on the public page (`test_public_page_never_leaks_storage_path`); captions are
HTML-escaped by Django's autoescaping, verified directly
(`test_caption_rendered_safely`); another caregiver's gallery items never leak onto a
different caregiver's public profile (`test_another_caregivers_gallery_never_appears`).

### Test Level Decision

Level 3 (full regression), run exactly once before creating the Sprint 2.2 PR, justified
by: a new model + migration, a file-upload/privacy boundary, a public-profile change, and
several apps (accounts, provider_portal, public_site) touched — the task's own explicit
Level-3 trigger set. 45 new tests (21 accounts + 13 provider_portal + 11 public_site).
Level 2 (accounts + provider_portal + public_site combined): 536/536. Architecture
guardrails (`ServiceSupplierProfileCouplingTest` + ORM-discipline tests): 13/13. Full
regression: 1932/1932 green (1887 baseline + 45 new).

### Deferred (explicitly, recorded)

1. Video support — not implemented; no canonical video-upload/processing infrastructure
   exists anywhere in this repository to reuse, and the task's own scope explicitly
   excludes it "unless the repository already has safe canonical video support" (it does
   not).
2. Thumbnail/derivative-image generation — not implemented, matching
   `ProfileMediaService`'s own pre-existing "no derivative image sizes" simplicity choice;
   the full-size, Pillow-validated image is served directly (bounded at 5MB), same as
   avatar/cover.
3. AI/automatic content moderation — not implemented, per explicit task scope exclusion.
4. Company gallery, customer gallery, order attachments, financial dashboard, order
   dashboard, marketplace/invoice/payment/settlement changes — none touched, per explicit
   task scope exclusion.
5. Certificates-as-visual-gallery presentation (surfacing verified documents as a photo-
   style gallery, distinct from this sprint's plain photo grid) — Sprint 2.3's stated
   territory, not started here.
6. Production media storage strategy (currently local `FileField`/`FileSystemStorage`, no
   S3/CDN) — a pre-existing, acknowledged roadmap blocking item (BG-021's original
   dependency note); gallery images inherit this exactly as avatar/cover already do, they
   do not worsen it.

### BG-021 Status (gallery portion)

**RESOLVED.** Gallery/media-portfolio scope is delivered. Extended financial overview and
orders + history (the remainder of BG-021) remain open, scheduled for Sprint 2.5.

---

## Sprint 2.2 Remediation — Harden Gallery File Lifecycle and Image Safety (PR #7 review, 2026-07-15)

PR #7 review found two bounded issues before approving merge. Both are corrected in place
on the same branch (`phase2-caregiver-gallery-media`) and PR (#7) — no new branch, no new
PR, no scope expansion into Sprint 2.3 or social features.

### Root file-lifecycle defect

`CaregiverGalleryService.remove_item()` originally called `item.image.delete(save=False)`
(the physical file) *before* `item.delete()` (the database row), both inside the same
`transaction.atomic()` block. Filesystem operations do not participate in a database
transaction — if the transaction (or an outer transaction this call was nested inside) had
later rolled back for any reason, the row deletion would be undone while the file it
pointed to was already, irreversibly gone: a live database row referencing a dead file,
with no way to detect or recover from it short of manual inspection.

### Corrected deletion sequence

1. Resolve and row-lock the item (unchanged — ownership/tenancy authorization still
   happens first, exactly as before).
2. Capture the storage handle and stored file name (`item.image.storage`,
   `item.image.name`) — `item.image` becomes unusable once the row is deleted, so this
   must happen before that.
3. Delete the database row (`item.delete()`).
4. Schedule physical deletion via `transaction.on_commit(lambda: cls._delete_stored_file(storage, file_name))`
   — Django guarantees this only runs after the outermost enclosing transaction actually
   commits, and discards it entirely (never runs it) if that transaction instead rolls
   back. No model signal was used — the scheduling is explicit, in the same service method
   that performs the deletion, matching this codebase's "every mutation goes through an
   explicit service call" convention.

The database can therefore never be left inconsistent by this operation: either both the
row and (eventually) the file are gone, or neither ever was.

### Storage-deletion failure behavior (now defined)

If the post-commit physical deletion itself fails (a storage/filesystem error), the new
`_delete_stored_file()` catches the exception and logs it (`logger.exception(...)`) —
never re-raises. By the time it runs, the row is already durably committed gone and cannot
be un-deleted by this failure, and the item is already unreachable (nothing resolves the
deleted row anymore, so its public URL is already dead). The only possible consequence of
a storage failure here is an orphaned file left on disk — now detectable via the error log
(`apps.accounts.services.caregiver_gallery_service`). Automatic retry/cleanup of orphaned
files is explicitly **deferred** — no cleanup-job/retry infrastructure exists anywhere in
this repository to hook it into, and building one was out of this remediation's scope
("do not implement a broad background-cleanup subsystem"). Recorded as
`quality/DEFECT_AND_RISK_REGISTER.md` KL-014.

### Image safety limits

`apps.accounts.services.image_validation.validate_image()` previously bounded only the
*uploaded, compressed* byte size (`MAX_IMAGE_BYTES`). A small, adversarially-crafted file
can still declare an enormous *decoded* pixel grid ("decompression bomb") — the byte-size
cap does nothing to stop this, since compression ratio is exactly what a bomb file
exploits. Added `MAX_IMAGE_WIDTH = 8000`, `MAX_IMAGE_HEIGHT = 8000`,
`MAX_IMAGE_PIXELS = 25_000_000` — explicit constants, matching this module's own existing
style (`MAX_IMAGE_BYTES`), not tenant-configurable (no product requirement or existing repo
convention calls for that). Both `width`/`height` are read from `image.size` immediately
after `Image.open()` — a cheap, header-only read that happens before any full pixel
decode — so an oversized image is rejected before the expensive/dangerous decode is ever
attempted, not after.

### Pillow/decompression-bomb handling

Pillow's own `Image.DecompressionBombError` (raised outright when decoded size exceeds
twice its own global `Image.MAX_IMAGE_PIXELS` threshold, ~89M px by default) and
`DecompressionBombWarning` (only warned, not raised, for sizes between 1x and 2x that
threshold) are both caught. The warning case required promoting it to a catchable
exception first — Python warnings don't propagate as exceptions by default — via a
`warnings.catch_warnings()` block scoped to just this validation call with
`warnings.simplefilter("error", Image.DecompressionBombWarning)`. Both are mapped to the
same controlled `AccountsError` the rest of this validator already uses — never a raw
`DecompressionBombError`/`Warning` reaching the caller, never an unhandled 500. Truncated/
corrupted content (`image.verify()`), unsupported formats, and image-open failures
(`UnidentifiedImageError`/`OSError`) all continued to map to the same controlled error, as
before this remediation — this was existing, correct behavior, just re-verified.

### Validation order (single decode pass)

Byte-size check -> `Image.open()` (format + size read from header, no decode) ->
`image.verify()` (integrity check) -> exceptions mapped to `AccountsError` -> format
allow-list check -> width/height/pixel-count checks -> `file.seek(0)` (stream reset for
the subsequent `ImageField` save). The image is opened and decoded exactly once — never
re-opened to re-check dimensions, matching the "avoid decoding the same image repeatedly"
requirement. No thumbnail generation was added (out of scope, matching
`ProfileMediaService`'s own pre-existing "no derivative image sizes" choice).

### Files changed

`apps/accounts/services/caregiver_gallery_service.py` (`remove_item()` restructured, new
`_delete_stored_file()`), `apps/accounts/services/image_validation.py` (dimension/pixel
limits, decompression-bomb handling), `apps/accounts/tests/test_caregiver_gallery.py`
(existing remove-item tests updated for the new deferred-deletion behavior; 16 new tests).
No model, no migration, no template, no URL change — this remediation is entirely
service-layer.

### Test infrastructure note

Proving "a rollback discards the scheduled physical deletion" and "a storage-deletion
failure does not raise or restore the row" both require observing `transaction.on_commit()`
behavior. `TransactionTestCase` (this repo's usual tool for genuine commit semantics) was
tried first; it triggered a pre-existing, unrelated Postgres/Django flush-teardown
incompatibility in this specific environment (`cannot truncate a table referenced in a
foreign key constraint` on `UserAccount`'s auto-generated `groups`/`user_permissions`
M2M-through tables) — reproduced independently with a minimal `TransactionTestCase` that
does nothing but create a single `UserAccount` row, confirming it is unrelated to this
remediation's own code and out of this narrowly-scoped remediation's mandate to fix.
Switched to `django.test.TestCase.captureOnCommitCallbacks()` instead, after directly
verifying (with a small standalone check) that it correctly reflects Django's real
nested-atomic-block rollback discard behavior — a genuine property of `transaction.atomic()`'s
own bookkeeping, not a simulation — without requiring the outermost per-test transaction to
ever truly commit.

### Test Level Decision

Level 3 (full regression), run exactly once before updating PR #7, justified by: the
shared `image_validation.validate_image()` function and the gallery's file-lifecycle logic
are both security/data-integrity boundaries reached from multiple surfaces (avatar/cover
upload, gallery upload, the public profile page). 16 new tests. Level 2 (accounts +
provider_portal + public_site combined): 552/552. Full regression: 1948/1948 green (1932
baseline + 16 new).

### Deferred (explicitly, recorded)

1. Automatic orphan-file cleanup/retry — `quality/DEFECT_AND_RISK_REGISTER.md` KL-014, no
   cleanup-job infrastructure exists to hook into, out of this remediation's scope.
2. Tenant-configurable image dimension/pixel limits — `quality/DEFECT_AND_RISK_REGISTER.md`
   KL-015, not a defect, a deliberate simplicity choice matching this module's existing
   constant-based style.
3. Thumbnail/derivative-image generation — unchanged, still out of scope (Sprint 2.2's own
   deferral, restated).

---

## Sprint 2.3 — Caregiver Professional Profile: Credentials, Skills, Experience, Highlights (2026-07-15)

First sprint on a fresh branch (`phase2-caregiver-credentials-skills-experience-ui`, from
`main` @ `f7b7b2b`) after PR #7 (Sprint 2.2 gallery + file-lifecycle/image-safety
remediation) was merged. Completes the professional-credibility presentation layer of the
caregiver profile — precise verification badges, owner-completable skill/experience
visibility, derived highlights, an owner-facing "expiring soon" credential state, and an
explicit self-declared-vs-verified distinction. Presentation and management of existing
credibility signals, not a new verification workflow and not a social system.

### Current-State Inspection

| Capability | Existing | Reusable | Missing |
|---|---|---|---|
| Skill model | `CaregiverSkill` — free-text `CharField`, `is_visible` field (unused), add/remove CRUD | Yes, kept exactly as-is per governance ("do not silently redesign") | Owner-facing way to change `is_visible` |
| Experience model | `CaregiverExperience` — `is_visible` field (unused), create/edit/delete CRUD | Yes | Owner-facing way to change `is_visible` |
| Credential summary | `PublicCredentialSelector` — `document_type`/`label`/`expiry_date` only, APPROVED + unexpired + applicable-type filter | Yes, extended (added `document_type` to the public ViewModel — the selector itself needed no change) | Per-type badge derivation at the presentation layer |
| Expiry derived fact | `RequiredDocumentPolicy.is_effectively_expired()` (Phase 1.2) | Yes, sibling added | "Expiring soon" (no expiry-window concept existed) |
| Owner credential-status preview | `ProviderProfilePresentationService._document_rows()` + `document_status.html` — already renders PENDING/VERIFIED/REJECTED/CORRECTION_REQUIRED/expired with reviewer-authored reason (owner-only) | Yes, reused as-is, only extended with one more derived status | "Expiring soon" status/badge |
| Verification badge component | `ui/components/portal/verification_badge.html` — icon+text, WCAG 1.4.1 compliant, `verified\|pending\|rejected\|correction_required\|expired\|unverified` | Yes, extended (also used by `apps.organization_portal`) | `expiring_soon` status branch |
| Public badge presentation | Single generic `"تأییدشده"` (Verified) pill tied to `is_verified` | Replaced, not extended — a compound, imprecise claim | Precise, per-claim badges |
| Highlights/professional summary | None anywhere | N/A | New, fully derived selector |
| Self-declared vs verified distinction | None (implicit only) | N/A | Explicit UI disclaimer |
| Service catalog | `ServiceCategory` (already shown as `service_names` on both portal and public pages) | Unrelated to this sprint — no per-service credential enforcement exists or was requested | N/A, out of scope by design |
| Skill catalog/normalization | None — free-text only | N/A | Explicitly out of scope this sprint (see Deferred) |

No genuine architectural blocker was found — proceeded directly to implementation.

### Credential Presentation Behavior

`PublicCredentialSelector` itself was not modified — it already returns only APPROVED,
unexpired, caregiver-owned, applicable-type documents, and already excludes file, document
number (never modeled — nothing to leak), reviewer identity, and rejection/correction
reason. `PublicCredentialViewModel` gained one new field, `document_type` (a type code, not
evidence), purely so the presentation layer (`_verification_badges()`) can derive precise
per-type badges without a new query or touching the selector's own privacy boundary. Owner
side is unchanged in scope — approved/pending/rejected/correction-required/expiring-soon/
expired states, reviewer reason shown only to the owner, private file access only through
the existing protected admin-portal route (never touched this sprint).

### Skills Behavior

`CaregiverSkillService.toggle_visibility(caregiver, *, skill_id)` — ownership-filtered
(`caregiver=caregiver` in the same lookup, defense-in-depth against a guessed id),
flips `is_visible`. Provider portal: a "نمایش/پنهان کردن" button per skill row
(`profile_skill_visibility_toggle_view`, new POST-only route), plus a status badge.
Public profile: `_skills()` (unchanged) already filtered `is_visible=True` since Phase
2.1 — this sprint only added the means to actually change that value. No catalog/
normalization was introduced (`CaregiverSkill.name` stays free-text) — the resulting
duplicate-spelling ambiguity is recorded, not fixed (`quality/DEFECT_AND_RISK_REGISTER.md`
KL-016).

### Experience Behavior

`CaregiverExperienceService.create()`/`update()` gained an `is_visible: bool = True`
keyword parameter (backward compatible — every existing caller that omits it keeps
today's behavior). `ExperienceForm` gained a matching checkbox field, rendered inline
with its label (matching the existing `is_current` checkbox's presentation, made
consistent in the same template edit). Public profile: `_experience()` (unchanged)
already filtered `is_visible=True`. The public experience section gained an explicit
disclaimer — "این سوابق توسط خود مراقب اعلام شده و توسط پلتفرم تأیید نشده است." (this
experience is self-declared by the caregiver and not verified by the platform) — since no
experience-verification record exists anywhere in this repository to derive such a claim
from, and this sprint's own governance explicitly forbids implying one.

### Highlights Behavior

Two parallel, independently-computed ViewModels — `ProfessionalHighlightsViewModel`
(public) and `HighlightsViewModel` (provider-portal owner preview) — both entirely
derived, never a new stored/duplicated statistic. Public: `years_experience` (existing
attribute), `verified_credential_count`/`visible_skill_count` (`len()` of tuples
`get_profile()` already resolved), `completed_jobs_count`/`review_count` (values already
computed for the rating sidebar) — zero new queries, confirmed unchanged at 14 by the
pre-existing `PublicProfileQueryCountTest`. Owner-side: mirrors the same shape but needs
two new, fixed-cost `.count()` queries (`visible_skill_count`/`visible_experience_count`
require a `WHERE is_visible` filter distinct from the existing unfiltered
`skills_count`/`experience_count`) — the provider profile page's own locked query-count
baseline moved 13 -> 15 accordingly, proven fixed-cost by the test's own unchanged
structure (no per-item loop introduced).

### Badge Semantics

Replaced the single generic `"تأییدشده"` pill with `VerificationBadgeViewModel` entries,
each naming exactly one evidence-backed claim: "نمایه تأییدشده" (Profile verified — the
canonical BG-022 visibility gate passed), "هویت تأییدشده" (Identity verified — an
approved, unexpired IDENTITY document exists), "مدرک حرفه‌ای تأییدشده" (Professional
credential verified — at least one approved credential of any applicable type exists).
Under the *default* required-document policy these badges co-occur (IDENTITY is
mandatory for "verified" status at all), but they are independently derived, evidence-
backed facts, not aliases — proven by a test that narrows a tenant's required-document
policy (the same override mechanism `RequiredDocumentPolicy` has supported since Phase
1.2) to exclude IDENTITY and confirms the "Identity verified" badge correctly does not
appear even though the profile itself is publicly verified. Owner side: `verification_
badge.html` gained one new, purely additive `expiring_soon` status branch (warning-
colored, icon+text, matching the existing pending/correction-required treatment) —
verified not to change any of the six pre-existing status branches' rendering, and
`apps.organization_portal`'s own suite (which also renders this shared component) was
re-run to confirm (51/51).

### Public/Private Boundary

No new boundary was introduced. Every new public field (`document_type` on credentials,
`highlights`, `verification_badges`) is either already-public data reshaped, or a pure
derivation of data already resolved behind the existing BG-022 canonical visibility gate.
A caregiver failing that gate (DRAFT/SUSPENDED/ARCHIVED/unverified/pending-verification/
inactive-account/inactive-membership) has `get_profile()` return `None` entirely —
highlights and badges are never computed at all for such a caregiver, proven directly by
`test_hidden_caregiver_profile_has_no_highlights_or_badges`.

### Files Added / Modified

See `traceability/CHANGE_LEDGER.md` CL-027 and `traceability/FILE_CHANGE_REGISTER.md`'s
"2026-07-15 — Sprint 2.3" section for the complete, categorized list. No files added — all
changes extend existing files. No migration.

### Security/Privacy Behavior Proven by Tests

Caregiver manages only their own skills/experience (structurally, via the
`caregiver=caregiver` filter, and directly via dedicated tests); cross-tenant mutation
denied (404, `test_cross_tenant_cannot_toggle_skill_visibility`); customer cannot mutate
(403); an account with no `caregiver_profile` at all (representing an unrelated
organization user) cannot mutate
(`test_unrelated_organization_user_cannot_mutate_skills`); private credential files,
document numbers (never modeled), reviewer identity, and rejection/correction reason
never appear publicly (existing tests plus a new direct rejection-reason check); pending/
rejected/correction-required/expired credentials never appear publicly (existing tests,
re-verified unchanged); hidden skills/experience never appear publicly (existing +1 new
test for experience specifically); a hidden caregiver profile exposes no professional-
credibility section at all, not just filtered ones; skill names and experience
descriptions are HTML-escaped (2 new direct tests); query count stays bounded (public: 14,
unchanged; provider: 15, +2 fixed-cost, proven not per-item).

### Test Level Decision

Level 3 (full regression), run exactly once before creating the Sprint 2.3 PR, justified
by: shared selector/ViewModel changes, a public/private presentation boundary change, and
a shared UI component (`verification_badge.html`) reaching into `apps.organization_portal`
as well as `apps.provider_portal` — the sprint's own explicit Level-3 trigger set. 36 new
tests (14 accounts + 11 provider_portal + 11 public_site). Level 2 (accounts +
provider_portal + public_site combined): 588/588. `apps.organization_portal` (shared-
component blast-radius check): 51/51. Architecture guardrails: 13/13. Full regression:
1984/1984 green (1948 baseline + 36 new).

### Deferred (explicitly, recorded)

1. Skill catalog/normalization (`CaregiverSkill.name` stays free-text) —
   `quality/DEFECT_AND_RISK_REGISTER.md` KL-016, a genuine future modeling decision, not a
   UI-completion task, explicitly out of this sprint's mandate ("do not silently
   redesign").
2. Certificates-as-visual-gallery presentation (distinct from this sprint's precise-badge/
   label treatment) — remains open under BG-021, Sprint 2.3's own governance did not
   include it.
3. Availability/calendar (Sprint 2.4), extended financial overview and orders + history
   (Sprint 2.5) — unchanged, not started.
4. Per-service credential enforcement — no repository infrastructure ties `ServiceCategory`
   to document/credential requirements (confirmed, unchanged since Phase 1.2); inventing
   one would be guessing a business rule with no evidence to ground it.

### BG-023 Status

**RESOLVED.** Professional credibility layer (badges, visibility management, highlights,
expiring-soon state, self-declared/verified distinction) delivered. See
`quality/COMPLETION_BACKLOG.md` BG-023.

## PR #8 Merge (2026-07-15)

`main` fast-forwarded from `f7b7b2b` to merge commit `20c532e` (PR #8, "Complete caregiver
credentials, skills, and experience presentation"). Final pre-merge verification confirmed
branch HEAD unchanged at `0b9b9c7`, diff scope unchanged (36 files), `git diff --check`
clean, `manage.py check` exit 0, PR description accurately reflecting the repository (the
prior turn's stray "public listing surfaces' looser eligibility rule" deferred-item claim
was a REPORTING_ERROR — that gap was already closed in PR #6, corrected in the PR #8
description, no code change needed). Local `main` verified identical to `origin/main`
(`20c532e878780397291bcaaddf287807a7efed92`) after the merge.

## Sprint 2.4 — Caregiver Availability and Working Schedule (2026-07-15)

First sprint on a fresh branch (`phase2-caregiver-availability-schedule`, from `main` @
`20c532e`) after PR #8 merged. Completes the caregiver availability layer — weekly working
intervals, time-off, one canonical availability evaluator, and a privacy-safe public
availability summary — so a caregiver can define when they are generally available and
what a future marketplace workflow may read. Not a booking/matching/calendar-sync feature.

### Current-State Inspection

| Capability | Existing | Reusable | Missing |
|---|---|---|---|
| Weekly working-hours model | `ProviderWorkingWindow` (Module 10 foundation) — day_of_week/start_time/end_time/is_active, keyed on `kernel.ServiceSupplier` | Yes, unchanged schema | Overlap/duplicate validation; owner-facing edit + enable/disable UI |
| Time-off model | `AvailabilityBlockedPeriod` (Module 10 foundation) — start_at/end_at/reason/notes | Yes, unchanged schema | Nothing structural — add/remove UI already existed |
| Availability evaluator | `AvailabilityQueryService.is_supplier_available()` — bool-only, fail-closed, timezone-aware, single-local-day scope | Yes, extended (kept as a thin wrapper) | Structured output (reasons, matched window, conflicting period, timezone) |
| Provider portal UI | `availability_view` — add window, list, remove window; add/remove blocked period; capacity display | Yes, extended | Edit window, enable/disable toggle, public-summary preview |
| Public schedule presentation | None | N/A | New, privacy-safe, day-labels-only summary |
| Caregiver-specific time zone | None anywhere in the repository (confirmed by grep) | N/A | Out of scope — platform default (`Asia/Tehran`) used, per Section J's explicit fallback instruction |
| Booking conflict awareness in the evaluator | `apps.booking.services.assignment_service` already *consumes* `is_supplier_available()` as one input | Reused as-is (unchanged call site) | Out of scope — folding booking state into the evaluator would invert the dependency direction |
| Caregiver-keyed availability service | None | N/A | Deliberately not created — would violate `apps.accounts` -> `apps.availability` dependency direction; see ADM-020 Decision 1 |

No genuine architectural blocker was found — proceeded directly to implementation.

### Canonical Availability Ownership

`apps.availability` (predates this sprint) already owns weekly schedule, time off, and (as
of this sprint) the public summary and canonical evaluator — all keyed on
`kernel.ServiceSupplier`, never `CaregiverProfile`/`OrganizationProfile` directly, matching
this app's own pre-existing docstring commitment. `apps.provider_portal` and
`apps.public_site` both resolve their own `ServiceSupplier` and read through this one
source; neither maintains schedule data of its own. See
`traceability/ARCHITECTURE_DECISION_LOG.md` ADM-020 for the full reasoning, including why
the governance's suggested `CaregiverAvailabilityService.evaluate(caregiver, ...)` shape was
not adopted literally.

### Weekly Schedule Behavior

`AvailabilityMutationService.add_working_window()`/`update_working_window()` now call a new
`_validate_no_overlap()` before create/save — refuses an exact duplicate or any partially
overlapping *active* window on the same day for the same supplier (covers both cases in one
range-intersection check). A disabled window is excluded from the check on both sides:
disabling one frees its slot for a new window, and re-enabling one re-validates against
whatever is active at that moment. `toggle_working_window()` is a thin convenience wrapper
(mirrors Sprint 2.3's `toggle_visibility()` pattern) for the new enable/disable button.
Provider portal gained inline start/end edit (`working_window_update_view`,
`WorkingWindowEditForm`) alongside the existing add/remove — ownership enforced by this
app's own pre-existing resolve-then-mutate-by-id pattern, not a new mechanism.

### Time-Off Behavior

Unchanged from the Module 10 foundation: add/remove only, no cancelled/active state (hard
delete remains the convention — nothing in the repository suggested otherwise). Overlapping
blocked periods are deliberately still allowed to coexist — `test_overlapping_blocked_periods
_both_apply` already proved this is harmless, pre-existing, tested behavior; adding refusal
here would silently change a passing, intentional test rather than fix a defect (ADM-020
Decision 3). Time-off continues to override weekly availability exactly as before (`evaluate()`
checks blocked periods first, unconditionally).

### Availability Evaluation Behavior

`AvailabilityQueryService.evaluate(*, supplier, start, end) -> AvailabilityEvaluation` — a
frozen dataclass (`available`, `reasons`, `matched_window`, `conflicting_blocked_period`,
`timezone`). Read-only: never creates/mutates/deletes a row (proven by a dedicated test
comparing row counts before/after). `is_supplier_available()` is now a one-line wrapper
around `evaluate(...).available` — the existing 20 tests for it pass completely unmodified,
and `apps.booking`'s existing consumer is unaffected (67/67 green). Booking/execution
conflict state is explicitly not consulted (Section E item 6, declined — see ADM-020
Decision 2); the evaluator only ever answers "is this a configured, unblocked working
window," the same question it always answered, now with a structured, explainable answer
instead of a bare bool.

### Time-Zone Policy

No per-tenant or per-caregiver time-zone field exists anywhere in this repository
(confirmed by grep before implementation). Every evaluation already resolved through
Django's default `timezone.localtime()`/`settings.TIME_ZONE` (`Asia/Tehran`, `USE_TZ=True`)
before this sprint; `evaluate()`'s new `timezone` field surfaces
`timezone.get_current_timezone_name()` — the same single, deterministic source, not a
second one. DST/ambiguous-local-time handling is whatever Django/`pytz`-equivalent already
provides for `Asia/Tehran` — unchanged, not specially handled. Documented as a known
platform-wide-only limitation (`quality/COMPLETION_BACKLOG.md` BG-024), not fixed —
inventing a per-caregiver time zone without evidence of demand would be guessing a business
requirement.

### Public Summary/Privacy Behavior

`CaregiverPublicProfileService._schedule_summary()` returns
`AvailabilityScheduleSummaryViewModel(has_schedule, available_day_labels)` — Persian
weekday names only (`apps.availability.models.PERSIAN_DAY_LABELS`, the one canonical
translation both `provider_portal` and `public_site` share), never exact start/end times,
never any `AvailabilityBlockedPeriod` field (reason, notes, or even its existence). Gated
by the same canonical `common.is_publicly_visible()` policy as every other section — a
hidden/DRAFT/suspended/unverified caregiver's schedule is never even queried, proven by
`test_hidden_caregiver_has_no_schedule_summary`. Two dedicated tests
(`test_summary_never_exposes_exact_times`, `test_summary_never_exposes_blocked_period_details`)
render the actual public page and assert the exact time strings and blocked-period
reason/notes text never appear in the response body. The provider-portal availability page
shows the identical computation as an owner-facing preview of exactly what the public sees.

### Files Added

None — `apps.availability` already contained every model this sprint needed.

### Files Modified

16 source files (2 model/service/init files in `apps.availability`, 2 test files there;
3 files in `apps.provider_portal` — forms/views/urls — plus 1 test file; 2 service files
in `apps.public_site` plus 2 test files; 2 templates) + 16 documentation files. Full list in
`traceability/FILE_CHANGE_REGISTER.md` (2026-07-15, CL-028) and
`traceability/CHANGE_LEDGER.md` Entry 028.

### Migration Impact

None. `ProviderWorkingWindow` and `AvailabilityBlockedPeriod` already carried every field
this sprint needed. `makemigrations --check --dry-run` shows only pre-existing,
unrelated drift (`kernel.ServiceSupplier`/`UserAccount` field alterations) — confirmed via
`git stash` comparison against the merged-main baseline to be byte-identical to the
pre-Sprint-2.4 drift, not new.

### UI/Routes

Provider portal: `availability/windows/<uuid:window_id>/update/`
(`working-window-update`), `availability/windows/<uuid:window_id>/toggle/`
(`working-window-toggle`) — both new, POST-only. Existing add/remove routes unchanged.
`availability.html` gained inline edit fields and an enable/disable button per window, plus
a "پیش‌نمایش نمایه عمومی" (public profile preview) section. Public site: no new route — the
existing caregiver-profile page gained one new sidebar card.

### Security/Privacy

All 15 of Section I's required proofs verified directly by tests: ownership (owner-only
mutation, cross-caregiver/cross-tenant/customer/unrelated-organization-user denial — 2
existing + 8 new tests across `test_availability_views.py`), invalid/duplicate/overlapping
interval rejection (11 new tests in `test_mutation_service.py`), time-off override of
weekly availability (pre-existing, re-confirmed unchanged), hidden-caregiver no public
schedule (new), no private reason/booking detail in public output (2 new tests asserting
exact absence), evaluator read-only (new), timezone deterministic (new, plus pre-existing
UTC-conversion test), concurrency (the pre-existing `select_for_update()` inside
`update_working_window()`'s `@transaction.atomic` block, exercised by the overlap-
validation tests — no dedicated multi-threaded race test was written, consistent with this
repository's existing testing conventions elsewhere in `apps.availability`/`apps.booking`).

### Query/Performance Impact

`evaluate()` issues the same query shape `is_supplier_available()` always did (at most one
blocked-period query, one working-window query) — no change. `get_distinct_active_days()`
is one new query, added to both the public profile (`_schedule_summary()`) and the
provider-portal availability page (`_public_summary_labels()`). Public profile page's
locked baseline moved 14 -> 15 (both `PublicProfileQueryCountTest` and
`PublicGalleryQueryCountTest`, proven O(1) against gallery-item count). Provider-portal
availability page gained a newly-locked baseline of 9 queries (no prior test existed).

### Test Level Decision

Level 3 (full regression), run exactly once before creating the Sprint 2.4 PR, justified
by: a new documented cross-app dependency edge (`apps.public_site` -> `apps.availability`),
a public/private presentation boundary change (the new schedule summary), and three apps
affected directly plus one proactive consumer check — matching this sprint's own Level-3
trigger set. 40 new tests (11 availability-mutation + 8 availability-query + 15
provider_portal + 6 public_site). Level 2 (`apps.availability` + `apps.provider_portal` +
`apps.public_site` combined): 297/297. `apps.booking` (proactive extra check — existing
`is_supplier_available()` consumer): 67/67. Full regression: 2024/2024 green (1984 baseline
+ 40 new).

### Deferred (explicitly, recorded)

1. Per-caregiver time zone — no field exists; platform-wide `Asia/Tehran` default used
   throughout, documented as a known limitation (`quality/COMPLETION_BACKLOG.md` BG-024),
   not invented without evidence of demand.
2. Overnight/midnight-spanning working windows — `AvailabilityQueryService._validate_range()`
   already rejected these before this sprint (unchanged); still deferred to a future
   sprint with a concrete overnight-shift use case to design against.
3. Booking/execution-session conflict awareness inside the evaluator — declined this
   sprint (ADM-020 Decision 2); `apps.booking` remains the sole consumer of availability
   state for that purpose, not the other way around.
4. Multi-threaded concurrency race testing for the overlap-validation
   `select_for_update()` path — not written, consistent with this repository's existing
   testing conventions for concurrent-mutation scenarios elsewhere in this app.
5. Extended financial overview, orders + history (Sprint 2.5) — unchanged, not started.

### BG-024 Status (new)

**RECORDED.** Per-caregiver time zone is not modeled; every caregiver is scheduled in the
platform's single default time zone regardless of their own physical location. See
`quality/COMPLETION_BACKLOG.md` BG-024.
