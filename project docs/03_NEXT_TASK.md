# NEXT TASK

---

## COMPLETED (previously listed here)

### Commit Phase 1 OrderOffer Implementation — DONE

OrderOffer Phase 1 (model, migration `orders/0008_orderoffer.py`, admin,
40 tests) was committed in `ce3b30e`. This item is closed
(see `quality/COMPLETION_BACKLOG.md` BG-001).

### Fix BG-002 Seed order_number Collision — DONE and MERGED (2026-07-14)

Bounded savepoint-wrapped retry in `Order.save()` + 6-digit suffix.
No migration. 8 new regression tests. Merged to main via PR #1
(merge commit `eb51018`) with full regression 1680/1680 green.
This was the P0 hygiene precursor to roadmap Phase 1
(see BG-002 in `quality/COMPLETION_BACKLOG.md`, CL-017).

### Phase 1.1 — Manual Document Verification (Caregiver + Organization) — IMPLEMENTED, PR PENDING (2026-07-15)

`VerificationReviewService` (approve/reject/request_correction), the
`accounts.document.review` permission, admin_portal review queue/detail/
file/review-action views and templates, and owner-facing reason display.
41 new tests (25 service-layer + 16 view-layer), full regression
1721/1721 green. Branch `phase1-registration-manual-verification`, PR
created but **not yet merged** — see `traceability/IMPLEMENTATION_JOURNAL.md`
and `traceability/ARCHITECTURE_DECISION_LOG.md` (ADM-014) for the full
record, including two explicit scope decisions (customer verification
deferred — no domain-model support exists; profile roll-up deferred — no
required-document policy exists). **MERGED to main** via PR #3, merge
commit `278098b` (2026-07-15), full regression 1721/1721 green at merge.

### Phase 1.2 — Verification Completion and Activation Rules — IMPLEMENTED, PR PENDING (2026-07-15)

Closes the two items Phase 1.1 explicitly deferred:

- `RequiredDocumentPolicy` (Part A): smallest explicit mandatory-document
  policy per profile type (caregiver: IDENTITY + BACKGROUND_CHECK;
  organization: REGISTRATION + OPERATING_LICENSE), tenant-overridable via
  the existing `ConfigResolver` infrastructure — no new configuration
  mechanism, no migration.
- `ProfileVerificationRollupService` (Part B): derives
  `CaregiverProfile`/`OrganizationProfile.verification_status` (the
  existing 4-value enum, no new field) from required-document state;
  wired automatically into `VerificationReviewService` and
  `DocumentService.resubmit()` — never left to a view/admin action/signal.
- `DocumentService.resubmit()` (Part C): owner-authorized resubmission
  entry point — refuses non-owners, refuses to touch a VERIFIED document,
  row-locked for concurrency, audited.
- `ActivationEligibilityService` (Part D): read-only
  `evaluate(profile)` returning structured eligibility + reasons; no
  side effects, no auto-activation/publishing.

47 new tests. Branch `phase1-verification-activation-rules`, PR created
and **MERGED to main** via PR #4, merge commit `860640e` (2026-07-15), full
regression 1768/1768 green at merge.

### Phase 1.3 — Complete Phase 1 Activation and Profile Completion — IMPLEMENTED, PR PENDING (2026-07-15)

Closes the two items Phase 1.2 explicitly left open (BG-018):

- `ProfileCompletionService` (Part A): single deterministic source of truth
  for the base-profile-field checklist per profile type (caregiver: 7
  fields; organization: 6 fields). `calculate_caregiver_profile_completion()`/
  `calculate_organization_profile_completion()` delegate their percentage to
  it — no second source of truth, bare-int signature unchanged.
- `ProfileActivationService.activate_caregiver()/activate_organization()`
  (Part B/C): the controlled, authorized, audited activation action —
  calls `ActivationEligibilityService` unchanged, refuses when ineligible
  with structured reasons, permission-gated (`ACCOUNTS_PROFILE_ACTIVATE`,
  platform staff only), refuses owner self-activation and cross-tenant
  activation, row-locked + idempotent (AuditLog-existence based, no new
  field), audited. Activation is an audited approval record over the
  existing default-ACTIVE status, not a new lifecycle state (see
  `traceability/ARCHITECTURE_DECISION_LOG.md` ADM-016).
- Minimum usable platform-operator UI (`admin_portal` activation detail +
  activate action) and owner-facing UI (activation status + blocking
  reasons on the provider/organization profile page).

40 new tests, zero new migrations, full regression 1808/1808 green.
**All Phase 1 acceptance criteria are now met.** Branch
`phase1-activation-completion-final`, PR #5 created — see
`traceability/IMPLEMENTATION_JOURNAL.md` and `ARCHITECTURE_DECISION_LOG`
ADM-016. Deferred (explicitly, recorded as BG-019, not a defect):
automatic deactivation of an already-active profile when verification
later becomes invalid — no suspension/revalidation workflow exists yet to
hook it into.

### Phase 1.3 Remediation — Fix Activation State Semantics (PR #5) — IMPLEMENTED (2026-07-15)

PR #5 review found the root defect described above under a different name:
`AuditLog` existence, not `profile.status`, was determining current
activation state, because registration left profiles `ACTIVE` by default
and `ProfileActivationService` never performed a real status transition.
Fixed in place on the same branch/PR:

- `RegistrationService.create_caregiver()`/`create_company_admin()` and
  `ensure_caregiver_profile()` now create profiles with
  `status=ProfileStatus.DRAFT` (the existing enum value, reused — no new
  status invented, no migration).
- `ActivationEligibilityService` no longer requires `status == ACTIVE`
  (the exact circularity being fixed); it now blocks only
  `SUSPENDED`/`ARCHIVED`.
- `ProfileActivationService` performs a real `DRAFT -> ACTIVE` transition,
  returns a structured `ProfileActivationResult`, and judges idempotency
  from `profile.status` — never from `AuditLog`.
- Owner/platform UI now distinguishes SUSPENDED explicitly.

16 new/renamed tests, full regression 1824/1824 green. See
`traceability/ARCHITECTURE_DECISION_LOG.md` ADM-016's remediation note and
`traceability/IMPLEMENTATION_JOURNAL.md` for the full record.

---

## IMMEDIATE NEXT TASK

### Merge the Phase 1.3 PR — Phase 1 (Registration and Verification Workflows) is then fully closed

Defined in **`IMPLEMENTATION_ROADMAP.md`** (the single active implementation
order).

Phase 1 scope — all items now complete:

1. ~~P0 hygiene: BG-002~~ — DONE
2. ~~Customer / caregiver / company registration workflows~~ — VERIFIED, no defect found (Phase 1.1 Part A)
3. ~~Platform-admin manual verification workflow~~ — IMPLEMENTED (Phase 1.1)
4. ~~Profile `verification_status` roll-up~~ — IMPLEMENTED (Phase 1.2 Part B)
5. ~~Profile completion recomputation~~ — IMPLEMENTED (Phase 1.3 Part A, `ProfileCompletionService`)
6. ~~Verification strategy interface~~ — `DocumentVerificationEvaluator` Protocol added, no implementation (by design)
7. ~~Wiring `ActivationEligibilityService` into an actual activation/publishing action~~ — IMPLEMENTED (Phase 1.3 Part B/C, `ProfileActivationService`)
8. Deferred, not part of Phase 1's own acceptance criteria: customer document verification (BG-016, no domain-model support), automatic deactivation on verification becoming invalid (BG-019, no suspension/revalidation workflow exists)

Once the Phase 1.3 PR merges, the next roadmap phase is **PHASE 2 —
Caregiver Professional Profile** (`IMPLEMENTATION_ROADMAP.md`) — explicitly
NOT started by this task (public Instagram-style profile, gallery,
credential presentation, structured skills — all out of scope until
Phase 1's PR is reviewed and merged).

Note: the previously listed follow-up "Phase 2: OrderOfferService" is now
scheduled as roadmap Phase 5 (Marketplace Order Workflow) and must not be
started before roadmap Phases 1–4.
