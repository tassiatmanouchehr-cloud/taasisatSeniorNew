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
