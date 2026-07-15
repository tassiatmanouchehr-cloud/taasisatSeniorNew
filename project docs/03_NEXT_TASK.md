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

16 new/renamed tests, full regression 1824/1824 green. **MERGED to main**
via PR #5, merge commit `0c9d70c` (2026-07-15). **Phase 1 — Registration
and Verification Workflows is CLOSED.** See
`traceability/ARCHITECTURE_DECISION_LOG.md` ADM-016's remediation note and
`traceability/IMPLEMENTATION_JOURNAL.md` for the full record.

### Phase 2.1 — Caregiver Professional Profile Foundation — IMPLEMENTED, PR PENDING (2026-07-15)

The first coherent, production-usable slice of roadmap Phase 2. Current-
state inspection found most of "public biography and professional
introduction," "services offered," "public caregiver profile page," and
"caregiver-side profile editing UI" already implemented (Epic 06 Sprint 2)
— reused as-is, not rebuilt (see `traceability/IMPLEMENTATION_JOURNAL.md`'s
implementation matrix). New work:

- `CaregiverSkill`/`CaregiverExperience` (Parts D/E): new, minimal FK
  child models of `CaregiverProfile` (mirrors `VerificationDocument`'s
  existing shape). `CaregiverSkillService`/`CaregiverExperienceService`:
  owner-authorized CRUD, case-insensitive duplicate-skill prevention
  (DB `UniqueConstraint` backstop), experience date validation
  (`CheckConstraint` backstop).
- `PublicCredentialSelector.for_caregiver()` (Part G): derives a safe,
  3-field public credential summary (type, label, expiry) from APPROVED,
  unexpired, caregiver-owned `VerificationDocument` rows only — never
  file/document-number/reviewer/rejection-reason.
- Corrected public-profile eligibility (Part H): `CaregiverPublicProfileService
  .get_profile()` now also requires `verification_status == VERIFIED` and
  the owning account's `is_active`, on top of (never replacing) the
  existing `common.is_publicly_visible()` check — added locally, not in
  the function shared with the caregiver directory/home-page listings
  (see `ARCHITECTURE_DECISION_LOG.md` ADM-017 Decision 2).
- Provider-portal skill/experience management pages; public profile page
  extended with skills/experience/credentials sections.

50 new tests, one new migration (2 new, empty tables only), full
regression 1874/1874 green. Branch
`phase2-caregiver-professional-profile-foundation`, PR pending, not yet
merged. Deferred (explicitly, recorded in
`quality/COMPLETION_BACKLOG.md`): gallery/posts/social features,
caregiver financial/order dashboards, directory/home-page listing
eligibility left unchanged (a known, documented inconsistency with the
now-stricter profile-page eligibility — **closed by the remediation
below**).

### Phase 2.1 Remediation — Close Public Caregiver Visibility Gap (BG-022) — IMPLEMENTED (2026-07-15)

PR #6 review found the gap Phase 2.1 itself recorded: its eligibility fix
(`verification_status == VERIFIED` + account `is_active`) was added only
to the single caregiver detail page, not to the directory or home-page
listings, which kept using the older, looser rule. A caregiver could be
discoverable in a listing while their own detail page 404'd. Fixed in
place on the same branch/PR:

- `apps.public_site.services.common.is_publicly_visible_attrs()` is now
  the single canonical public-visibility rule — every public entry point
  (directory search, home-page featured cards, home-page city filter,
  detail page) calls it, directly or via `bulk_supplier_attrs()`/
  `supplier_entity_attrs()`.
- `CaregiverPublicProfileService.get_profile()`'s now-redundant local
  duplicate check was removed.
- `apps.accounts.services.supplier_bridge.resolve_supplier_entities_bulk()`
  gained `select_related("user")`/`select_related("admin_user")` — a JOIN
  on the existing batched query, confirmed to add zero new queries
  regardless of candidate count.

13 new tests, full regression 1887/1887 green. See
`traceability/ARCHITECTURE_DECISION_LOG.md` ADM-017's second remediation
note. **BG-022 is now RESOLVED.**

### PR #6 — MERGED (2026-07-15)

Final verification confirmed the branch was exactly two commits ahead of
`main`, contained only Phase 2.1 + BG-022 remediation work (no gallery/
Sprint 2.2 code), the canonical visibility policy was applied consistently
everywhere it needed to be, private verification files/review information
stayed non-public, and documentation was synchronized. Merged via
`merge_pull_request` (merge commit `c5259b3787569b48df4c40133a5733d8567fa505`).
Local `main` fast-forwarded to match `origin/main`; `manage.py check` exits 0.
**Phase 2.1 (including BG-022) is now CLOSED and on `main`.**

### Sprint 2.2 — Caregiver Gallery and Media Portfolio — IMPLEMENTED (2026-07-15)

Branched fresh from merged `main` (`phase2-caregiver-gallery-media`, from
`c5259b3`) per governance ("do not stack new sprint work on an unmerged
feature branch"). Delivers a caregiver-managed professional photo
portfolio — closes the gallery portion of BG-021:

- `CaregiverGalleryItem` (new model, `apps/accounts/models/gallery.py`):
  plain FK child of `CaregiverProfile`, same shape as `CaregiverSkill`/
  `CaregiverExperience` (Phase 2.1) — UUID PK, no `TenantAwareModel`,
  `image`/`caption`/`alt_text`/`display_order`/`is_visible`.
- `CaregiverGalleryService`: owner-authorized upload (row-locked, 12-item
  cap), caption/alt-text/visibility edit, reorder (row-locked, all-or-
  nothing), remove (hard delete + physical file cleanup) — mirrors
  `CaregiverSkillService`/`CaregiverExperienceService`'s ownership shape,
  `DocumentService.resubmit()`'s row-locking precedent where a lock is
  genuinely needed.
- `apps.accounts.services.image_validation.validate_image()` (new,
  extracted from `ProfileMediaService`'s former private validator) — one
  shared implementation of image validation, not a second one.
- Provider-portal gallery management page (upload/caption/visibility/
  reorder/remove); public-profile gallery section reusing the existing
  BG-022 canonical visibility policy — no second visibility rule
  introduced.

45 new tests, one new migration (one new, empty table), full regression
1932/1932 green. Branch `phase2-caregiver-gallery-media`, PR #7 created —
see `traceability/IMPLEMENTATION_JOURNAL.md` and
`ARCHITECTURE_DECISION_LOG.md` ADM-018. **Not merged — awaiting review.**

### Sprint 2.2 Remediation — Harden Gallery File Lifecycle and Image Safety (PR #7 review) — IMPLEMENTED (2026-07-15)

PR #7 review found two bounded issues, both fixed in place on the same
branch/PR (no new branch, no new PR):

- `CaregiverGalleryService.remove_item()` deleted the physical file
  *before* the database row, inside the same transaction — unsafe, since
  filesystem operations aren't transactional. Fixed: the row is deleted
  first; physical deletion is scheduled via `transaction.on_commit()`,
  which Django discards entirely if the transaction rolls back. A
  storage-deletion failure after commit is caught and logged, never
  raised or allowed to restore the row.
- `apps.accounts.services.image_validation.validate_image()` bounded
  upload byte size but not decoded pixel dimensions — no defense against
  a small file claiming an enormous decoded image
  ("decompression bomb"). Fixed: `MAX_IMAGE_WIDTH`/`MAX_IMAGE_HEIGHT`/
  `MAX_IMAGE_PIXELS` are read from the image header and enforced before
  any full decode; Pillow's own `DecompressionBombError`/`Warning` are
  caught and mapped to the existing controlled error.

16 new tests, zero new migration, full regression 1948/1948 green. See
`traceability/ARCHITECTURE_DECISION_LOG.md` ADM-018's remediation note.
PR #7 updated in place. **Not merged — awaiting review.**

---

## IMMEDIATE NEXT TASK

### Await review of the Sprint 2.2 PR (#7); do not start Sprint 2.3 automatically

Defined in **`IMPLEMENTATION_ROADMAP.md`** (the single active implementation
order).

Phase 1 and Phase 2.1 (+ BG-022) are fully closed and merged to `main`.
Sprint 2.2 (this session's work) delivers the gallery/media-portfolio slice
of roadmap Phase 2 — remaining roadmap Phase 2 scope, explicitly NOT
started by this task:

1. Sprint 2.3 — Professional Certificates, Credential Presentation,
   Professional Skills UI, Experience Timeline, Professional Highlights,
   Verification Badges — not started.
2. Sprint 2.4 — Availability, Working Hours, Calendar, Vacation,
   Availability Rules, Availability Presentation — not started.
3. Sprint 2.5 — Professional Dashboard, Orders Summary, Financial Summary,
   Review Summary, Statistics, Performance Overview — not started (closes
   the rest of BG-021: extended financial overview, orders + history).
4. Sprint 2.6 — Public Profile Finalization (SEO, caching, search, public
   APIs, accessibility, performance, privacy review, architecture cleanup,
   final acceptance) — not started.
5. Known, recorded during BG-022's remediation: a pre-existing, unrelated
   per-candidate query cost in directory ranking/card-building
   (`DiscoveryRankingService.rank()`, `CaregiverDirectoryService
   ._build_card()`) — see `quality/DEFECT_AND_RISK_REGISTER.md` KL-012,
   not fixed (separate performance task, out of scope).
6. Known, pre-existing, unchanged by Sprint 2.2: production media storage
   strategy (currently local `FileField`/`FileSystemStorage`, no S3/CDN) —
   BG-021's original dependency note; gallery images inherit this exactly
   as avatar/cover already do.

Note: the previously listed follow-up "Phase 2: OrderOfferService" is now
scheduled as roadmap Phase 5 (Marketplace Order Workflow) and must not be
started before roadmap Phases 1–4.
