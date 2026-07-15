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

### PR #7 — MERGED (2026-07-15)

Final verification confirmed the branch was in-scope only (gallery + PR
#7 remediation, no Sprint 2.3 code), physical deletion was proven to run
only through `transaction.on_commit()` with rollback correctly discarding
it, storage-deletion failure could not recreate or publicly expose the
deleted row, width/height/pixel-count limits and Pillow decompression-
bomb handling were confirmed enforced, avatar/cover validation remained
compatible, and documentation was synchronized. Merged via
`merge_pull_request` (merge commit
`f7b7b2be5abd42d85935f522cf1b7b9b27bb6da1`). Local `main` fast-forwarded
to match `origin/main`; `manage.py check` exits 0. **Sprint 2.2 (including
the PR #7 remediation) is now CLOSED and on `main`.**

### Sprint 2.3 — Credentials, Skills, Experience, Highlights — IMPLEMENTED (2026-07-15)

Branched fresh from merged `main`
(`phase2-caregiver-credentials-skills-experience-ui`, from `f7b7b2b`) per
governance. Completes the professional-credibility presentation layer —
closes new backlog item BG-023:

- `CaregiverSkillService.toggle_visibility()` and
  `CaregiverExperienceService.create()`/`update()`'s new `is_visible`
  parameter — the column existed on both models since Phase 2.1, unused
  until now; zero migration.
- Precise `VerificationBadgeViewModel` entries ("Profile verified",
  "Identity verified", "Professional credential verified") replace the
  single generic "Verified" pill — each independently evidence-derived,
  proven via a required-document-policy-override test that the badges
  are not mere aliases of each other.
- Fully derived `ProfessionalHighlightsViewModel`/`HighlightsViewModel`
  (years of experience, verified-credential count, visible-skill count,
  completed-jobs/review count) — zero new queries on the public page,
  two fixed-cost `.count()` queries on the provider-portal preview.
- `RequiredDocumentPolicy.is_expiring_soon()` (30-day window, owner-
  facing only) and a new `expiring_soon` branch on the shared
  `verification_badge.html` component (also used by
  `apps.organization_portal`, re-verified 51/51).
- Explicit "self-declared, not platform-verified" disclaimer on the
  public experience section, contrasted with a "platform-reviewed" note
  on credentials.

36 new tests, zero new migration, full regression 1984/1984 green. Branch
`phase2-caregiver-credentials-skills-experience-ui`, PR created — see
`traceability/IMPLEMENTATION_JOURNAL.md` and
`ARCHITECTURE_DECISION_LOG.md` ADM-019.

### PR #8 — MERGED (2026-07-15)

Final verification confirmed branch HEAD unchanged (`0b9b9c7`), diff scope
unchanged (36 files, Sprint 2.3 only, no Sprint 2.4 code), `git diff
--check` clean, `manage.py check` exit 0, and the PR description corrected
to no longer claim a public-listing visibility gap (that claim was a
REPORTING_ERROR — the gap had already been closed in PR #6; no code
change was needed). Merged via `merge_pull_request` (merge commit
`20c532e878780397291bcaaddf287807a7efed92`). Local `main` fast-forwarded
to match `origin/main`; `manage.py check` exits 0. **Sprint 2.3 is now
CLOSED and on `main`.**

### Sprint 2.4 — Caregiver Availability and Working Schedule — IMPLEMENTED (2026-07-15)

Branched fresh from merged `main` (`phase2-caregiver-availability-schedule`,
from `20c532e`) per governance. Completes the caregiver availability layer
— closes new backlog item BG-025:

- `AvailabilityMutationService.add_working_window()`/`update_working_window()`
  gained duplicate/overlap refusal for active windows on the same day
  (closes KL-017); a new `toggle_working_window()` enables/disables an
  existing window.
- `AvailabilityQueryService.evaluate()` is now the one canonical,
  structured availability evaluator (`available`, `reasons`,
  `matched_window`, `conflicting_blocked_period`, `timezone`) —
  `is_supplier_available()` is a thin wrapper around it, zero behavior
  change for the existing `apps.booking` consumer (67/67 green).
  Deliberately stays supplier-keyed, not caregiver-keyed, to respect
  `apps.availability`'s position in the dependency graph — see
  `ARCHITECTURE_DECISION_LOG.md` ADM-020 Decision 1.
- Provider portal: inline working-window edit and enable/disable UI (new),
  alongside the existing add/remove; a public-summary preview section.
- Public caregiver profile: a new privacy-safe schedule-summary sidebar
  card — weekday labels only (`apps.availability.models.PERSIAN_DAY_LABELS`),
  never exact times or time-off details, gated by the existing canonical
  `is_publicly_visible()` policy.
- No per-caregiver time zone modeled — platform default (`Asia/Tehran`)
  used throughout, documented as a known limitation (new backlog item
  BG-024), not invented without evidence of demand.

40 new tests, zero new migration, full regression 2024/2024 green. Branch
`phase2-caregiver-availability-schedule`, PR created — see
`traceability/IMPLEMENTATION_JOURNAL.md` and
`ARCHITECTURE_DECISION_LOG.md` ADM-020.

### PR #9 Review Remediation — Availability Mutation Concurrency — IMPLEMENTED (2026-07-15)

Review found the initial Sprint 2.4 implementation's overlap validation
was not concurrency-safe: `_validate_no_overlap()` was an unlocked
`SELECT`, and `add_working_window()` took no lock at all before its
check-then-insert — two concurrent transactions could both read "no
conflict" before either committed, then both insert overlapping active
windows. `update_working_window()`'s existing `select_for_update()` on
the window-being-updated didn't close the gap either (it locks no row a
concurrent create touches). Fixed by locking the owning
`kernel.ServiceSupplier` row first, before any overlap check, in both
`add_working_window()`/`update_working_window()` — mirroring
`CaregiverGalleryService.add_item()`'s existing precedent for the same
class of problem. `toggle_working_window()` inherited the fix
automatically. 9 new `TransactionTestCase` tests
(`apps.availability.tests.test_concurrency`) prove the invariant against
real, separately-committed transactions, each asserting final database
state. Zero new migration. Remediation kept inside PR #9 (same branch,
same PR, description updated) — see
`traceability/IMPLEMENTATION_JOURNAL.md` and
`ARCHITECTURE_DECISION_LOG.md` ADM-020's remediation note.

### PR #9 — MERGED (2026-07-15)

Final verification confirmed branch HEAD unchanged (`74752d9`), diff
scope unchanged (33 files, both commits), the supplier row is locked
before overlap validation on every path that can introduce or activate
an interval, enabling a conflicting disabled window is refused,
concurrent overlapping creates cannot both commit, different suppliers
are not globally serialized, no Sprint 2.5 code existed in the diff, and
documentation was synchronized. Merged via `merge_pull_request` (merge
commit `125dd3b2916877230684b187e847fb1c07292d05`). Local `main`
fast-forwarded to match `origin/main`; `manage.py check` exits 0.
**Sprint 2.4 (including the PR #9 concurrency remediation) is now
CLOSED and on `main`.**

### Sprint 2.5 — Caregiver Professional Dashboard — IMPLEMENTED (2026-07-15)

Branched fresh from merged `main` (`phase2-caregiver-professional-dashboard`,
from `125dd3b`) per governance. Completes the caregiver's own
professional dashboard — closes new backlog item BG-026:

- Work summary: `Order.status`-derived current/upcoming/completed/
  cancelled counts and bounded recent lists, via two new methods on the
  existing `apps.orders.services.queries.OrderQueryService` (mirrors
  `list_for_customer()`'s exact shape — no new statuses invented).
- Financial overview and wallet movements: reuse the existing
  `WalletService`/`WalletTransactionService` unchanged — no new
  financial calculation.
- Bonus/penalty: confirmed, by repository-wide inspection, that no
  canonical representation exists anywhere — documented as a gap
  (`FinancialOverviewViewModel.bonus_penalty_note`), not invented.
- Invoice summary: two new methods on `apps.finance.services
  .document_service.FinancialDocumentService`
  (`list_for_beneficiary_party()`/`count_by_status_for_beneficiary_party()`),
  mirroring the existing customer-side `list_for_payer_party()`.
- Reviews/reputation: reuses `ReputationService.get_reputation_summary()`
  and a new `list_recent_reviews_with_reviewer_names()`.
- Professional statistics: reuses `ProviderReportService` and Sprint
  2.3's existing skill/credential/gallery-count definitions, each
  documented per-field with its exact source.

44 new tests, zero new migration, full regression 2077/2077 green.
Branch `phase2-caregiver-professional-dashboard`, PR created — see
`traceability/IMPLEMENTATION_JOURNAL.md` and
`ARCHITECTURE_DECISION_LOG.md` ADM-021. **Not merged — awaiting review.**

---

## IMMEDIATE NEXT TASK

### Await review of the Sprint 2.5 PR; do not start Sprint 2.6 automatically

Defined in **`IMPLEMENTATION_ROADMAP.md`** (the single active implementation
order).

Phase 1, Phase 2.1 (+ BG-022), Sprint 2.2 (+ PR #7 remediation), Sprint
2.3, and Sprint 2.4 (+ PR #9 concurrency remediation) are fully closed
and merged to `main`. Sprint 2.5 (this session's work) delivers the
professional-dashboard slice of roadmap Phase 2 — remaining roadmap
Phase 2 scope, explicitly NOT started by this task:

1. Sprint 2.6 — Public Profile Finalization (SEO, caching, search, public
   APIs, accessibility, performance, privacy review, architecture cleanup,
   final acceptance) — not started.
2. Known, recorded during BG-022's remediation: a pre-existing, unrelated
   per-candidate query cost in directory ranking/card-building
   (`DiscoveryRankingService.rank()`, `CaregiverDirectoryService
   ._build_card()`) — see `quality/DEFECT_AND_RISK_REGISTER.md` KL-012,
   not fixed (separate performance task, out of scope).
3. Known, recorded during Sprint 2.3: `CaregiverSkill.name` remains
   free-text with no catalog/normalization — see
   `quality/DEFECT_AND_RISK_REGISTER.md` KL-016, deferred (a future
   modeling decision, not a UI-completion task).
4. Known, recorded during Sprint 2.2/PR #7: gallery orphan-file cleanup/
   retry is not automated (KL-014) and decoded-image dimension/pixel
   limits are fixed, not tenant-configurable (KL-015) — both deliberate,
   not defects.
5. Known, pre-existing, unchanged by Sprint 2.2: production media storage
   strategy (currently local `FileField`/`FileSystemStorage`, no S3/CDN) —
   BG-021's original dependency note; gallery images inherit this exactly
   as avatar/cover already do.
6. Known, recorded during Sprint 2.4: per-caregiver time zone is not
   modeled — see `quality/DEFECT_AND_RISK_REGISTER.md` KL-018 /
   `quality/COMPLETION_BACKLOG.md` BG-024, deferred (no evidence of
   multi-time-zone demand).
7. Known, recorded during Sprint 2.5: no canonical bonus/penalty
   representation exists — see `quality/DEFECT_AND_RISK_REGISTER.md`
   KL-020 / `quality/COMPLETION_BACKLOG.md` BG-026's "not in scope" note,
   deferred (no evidence to invent one against).

Note: the previously listed follow-up "Phase 2: OrderOfferService" is now
scheduled as roadmap Phase 5 (Marketplace Order Workflow) and must not be
started before roadmap Phases 1–4.
