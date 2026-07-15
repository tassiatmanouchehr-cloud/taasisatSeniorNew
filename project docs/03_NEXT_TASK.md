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
but **not yet merged** — see `traceability/IMPLEMENTATION_JOURNAL.md`.

---

## IMMEDIATE NEXT TASK

### Merge the Phase 1.2 PR, then continue Phase 1 — Registration and Verification Workflows

Defined in **`IMPLEMENTATION_ROADMAP.md`** (the single active implementation
order).

Remaining Phase 1 scope after Phase 1.2 merges:

1. ~~P0 hygiene: BG-002~~ — DONE
2. ~~Customer / caregiver / company registration workflows~~ — VERIFIED, no defect found (Phase 1.1 Part A)
3. ~~Platform-admin manual verification workflow~~ — IMPLEMENTED (Phase 1.1)
4. ~~Profile `verification_status` roll-up~~ — IMPLEMENTED (Phase 1.2 Part B)
5. Profile completion recomputation — `calculate_caregiver_profile_completion()`/`calculate_organization_profile_completion()` exist and are read by `ActivationEligibilityService`, but nothing yet recomputes/persists `profile_completion_percent` automatically on every profile mutation
6. ~~Verification strategy interface~~ — `DocumentVerificationEvaluator` Protocol added, no implementation (by design)
7. New, not yet scoped: customer document verification (no domain-model support currently exists — requires its own decision before implementation)
8. New, not yet scoped: wiring `ActivationEligibilityService` into an actual activation/publishing action (currently read-only, no caller mutates anything based on it)

Note: the previously listed follow-up "Phase 2: OrderOfferService" is now
scheduled as roadmap Phase 5 (Marketplace Order Workflow) and must not be
started before roadmap Phases 1–4.
