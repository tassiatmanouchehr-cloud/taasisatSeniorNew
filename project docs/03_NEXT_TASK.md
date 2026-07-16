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
`ARCHITECTURE_DECISION_LOG.md` ADM-021.

### PR #10 — MERGED (2026-07-15)

Final verification confirmed branch HEAD unchanged (`0682da9`), `git diff
--check origin/main...HEAD` clean, `git status --short` clean, `manage.py
check` exit 0, and all 12 required pre-merge points (dashboard selectors
read-only; no direct financial/order calculations in views/templates;
wallet balance from the canonical `WalletService`; wallet-movement
`metadata` never rendered; invoice queries beneficiary-scoped; order
summaries supplier-scoped; reviews belong to the current caregiver;
no customer-private/platform-internal accounting info exposed; query
counts bounded; no Sprint 2.6 code present; documentation synchronized;
diff contains no unrelated code) confirmed via direct code inspection.
Merged via `merge_pull_request` (merge commit
`9a260241cfd82ef3be997eec152d1aa2a510542b`). Local `main` fast-forwarded
to match `origin/main`; `manage.py check` exits 0. **Sprint 2.5 is now
CLOSED and on `main`.**

### Sprint 2.6 — Public Profile Finalization and Phase 2 Acceptance — IMPLEMENTED (2026-07-15)

Branched fresh from merged `main` (`phase2-caregiver-public-profile-finalization`,
from `9a26024`) per governance — not a reuse of the Sprint 2.5 branch.
Integration/quality/privacy/accessibility/performance closeout sprint for
the whole caregiver public-profile capability — no new models, views, or
routes; domain engines explicitly not redesigned:

- Confirmed clean (no fix needed): directory/search/home canonical
  visibility (BG-022, re-verified), provider-preview consistency (the
  "public preview" link is the exact same public URL/selector, not a
  separate render path), privacy/security boundaries (every public
  ViewModel structurally excludes phone/email/address/national-ID/
  document-path/document-number/reviewer-identity/rejection-reason),
  existing cache infra (real, but narrowly used for config/feature-flags
  only — no page/read-model cache added, no proven blocker), and the
  existing permission-gated internal discovery API (unrelated to the
  public caregiver profile — no new public API created).
- Fixed: SEO `page_url`/canonical-URL bug on the caregiver profile page
  (was pointing at the directory URL, not its own); empty-`alt` gap on
  non-decorative gallery images (3 templates); unassociated form labels
  (4 `provider_portal` templates); a redundant, always-true generic
  verification badge that duplicated the precise Sprint 2.3 badges (see
  `ARCHITECTURE_DECISION_LOG.md` ADM-022 Decision 1); one pre-existing,
  unrelated, environment-clock-dependent flaky test
  (`apps.accounts.tests.test_caregiver_professional_profile`).
- Measured and documented (Section G): query counts for all 7 required
  pages — public profile (15, bounded), directory (28/43/57 at 5/10/20
  candidates — grows with total candidates, KL-012, initially left
  unfixed), home featured (27/32/42, same cause), provider dashboard
  (30/31, pre-existing, bounded), provider profile-management (15,
  pre-existing, bounded).
- New `apps.public_site.tests.test_phase2_acceptance` (5 tests): a full
  DRAFT-to-published caregiver lifecycle proving activation, bio edit,
  skill/experience/gallery visibility, availability, credential approval,
  public composition, directory/search discovery, dashboard isolation,
  and private-data non-leakage compose correctly together.
- Deferred, recorded, not fixed (out of this sprint's caregiver-only
  scope): identical SEO bug on `organization_profile.html` (KL-021/
  BG-027); the same unassociated-label pattern in `organization_portal`/
  `admin_portal`/`portal` templates.

Zero new migration, full regression 2082/2082 green (run twice: once
surfacing the unrelated flaky test, once green after the fix). Branch
`phase2-caregiver-public-profile-finalization`, PR #11 created.

**PR #11 review remediation (KL-012, 2026-07-15):** review found the
directory/home query-count growth reported above inconsistent with the
"query behavior is bounded" and "no unresolved Phase 2 blocker" acceptance
criteria it was cited to satisfy. Root cause: three independent
per-candidate query calls — `DiscoveryRankingService`'s per-candidate
`CapacityService.is_capacity_exceeded()` inside ranking,
`SupplierSearchService`'s per-candidate `resolve_supplier_entity()` inside
its city filter, and `CaregiverDirectoryService._build_card()`'s
per-card rating/completed-jobs lookups. Fixed by batching all three at
their own selector boundary (`CapacityService.bulk_is_capacity_exceeded()`,
the pre-existing `resolve_supplier_entities_bulk()`, and two new bulk
rating/completed-jobs methods) — zero change to ranking formula, sort
order, filter semantics, or public-visibility policy. Directory/search/
home query counts are now fully flat (16/17/17) from 1 through 100+
matching candidates. 12 new tests, zero new migration, full regression
2094/2094 green. See `traceability/IMPLEMENTATION_JOURNAL.md`,
`ARCHITECTURE_DECISION_LOG.md` ADM-022's remediation note, and
`project docs/PHASE_2_COMPLETION_REPORT.md`. **Phase 2 (Caregiver
Professional Profile) acceptance criteria satisfied**, except the one
explicitly accepted external-domain dependency (no canonical
bonus/penalty representation, KL-020).

### PR #11 — MERGED (2026-07-16)

Final verification confirmed branch HEAD unchanged (`3e18970`), `git diff
--check origin/main...HEAD` clean, `git status --short` clean, `manage.py
check` exit 0, and all 12 required points (directory/search/home query
counts independent of candidate count; bulk capacity evaluation preserves
ranking semantics; bulk city/entity resolution preserves filtering
semantics; bulk reputation/completed-job data preserves card values;
canonical public visibility unchanged; no private data added to cards;
the expiry-test correction does not weaken its assertion; no Phase 3 code
in the diff; documentation and `PHASE_2_COMPLETION_REPORT.md`
synchronized; diff contains no unrelated code) confirmed via direct
inspection and the already-recorded 2094/2094 verification (branch
unchanged, not re-run). Merged via `merge_pull_request` (merge commit
`90e608dc5d14ff4f367abafc022f756819734f6d`). Local `main` fast-forwarded
to match `origin/main`; `manage.py check` exits 0. **Phase 2 (Caregiver
Professional Profile) is now CLOSED and on `main`.**

### Sprint 3.1 — Company Foundation and Caregiver Management — IMPLEMENTED (2026-07-16)

Branched fresh from merged `main` (`phase3-company-portal-foundation`,
from `90e608d`) per governance. First Phase 3 (Company Portal) slice —
closes new backlog item BG-028:

- Current-state inspection found the model layer already built —
  `OrganizationMembership` and `CompanyAffiliationRequest` — but no path
  ever produced a PENDING membership, no invitation concept existed, and
  no UI/permission enforcement covered either model. Extended (not
  replaced) `apps.accounts.services.affiliations` to close all three
  gaps.
- Canonical model: `OrganizationMembership` (extended with
  `terminated_at`/`terminated_by`/`termination_reason`) is the single
  historical relationship record; `CompanyAffiliationRequest` remains the
  caregiver-initiated join-by-code intake that feeds it. One active
  company per caregiver at a time (documented minimal policy — see
  ADM-023 Decision 2).
- Join-by-code: new tenant-scoped, exact-code-only, ACTIVE-organization-
  only resolver (`submit_join_request()`/`preview_join_code_organization()`),
  distinct from the legacy, looser `find_organization_by_code_or_name()`
  (left untouched for its existing callers).
- Company-initiated invitation: new `invite_caregiver()`/`accept_invitation()`/
  `decline_invitation()`/`cancel_invitation()`.
- Mutual termination: `terminate_membership()` (company-side,
  permission-gated) and `leave_organization()` (caregiver-side,
  ownership-authorized) — both funnel into one `_finalize_termination()`
  helper.
- 4 new permission keys (`ORGANIZATION_MEMBERSHIP_INVITE`/`_REJECT`/
  `_TERMINATE`, plus reusing the existing `_APPROVE` for affiliation-request
  approval), granted to `organization_admin` via the existing
  `OrganizationRoleSyncService` additive-merge sync.
- New UI: `organization_portal`'s staff page extended with pending
  requests/invitations/invite-by-phone/terminate sections;
  `provider_portal`'s new "company" page (join by code, respond to
  invitations, leave, history).
- Concurrency: every activation path locks the caregiver's own
  `CaregiverProfile` row first (mirroring `CaregiverGalleryService
  .add_item()`'s/`AvailabilityMutationService`'s existing "lock the
  owning parent" precedent) — proven by 3 new `TransactionTestCase`
  tests, including a genuine two-different-organizations race that the
  lock closes.
- One migration (`accounts/0008_company_affiliation_termination.py`: 3 new
  nullable `OrganizationMembership` fields — no new model, no altered
  financial/order/payment table). **Superseded by the PR #12 remediation
  below — see that entry for the final migration/constraint state and
  final test/regression counts.**

51 new tests (32 service-layer + 9 `organization_portal` HTTP-level + 10
`provider_portal` HTTP-level) landed at this point in the sprint; full
regression 2145/2145 green at this point (superseded — see the PR #12
remediation entry below for the final 2150/2150 count). Branch
`phase3-company-portal-foundation`, PR #12 created — see
`traceability/IMPLEMENTATION_JOURNAL.md` and `ARCHITECTURE_DECISION_LOG.md`
ADM-023.

### PR #12 Architecture Review Remediation — Preserve Affiliation Period History (Blocker 1) — IMPLEMENTED (2026-07-16)

An architecture review of PR #12 identified two merge blockers. Blocker 1:
`approve_affiliation_request()`/`invite_caregiver()` used
`update_or_create()`, so a caregiver rejoining the same organization after
a prior termination reactivated that same `OrganizationMembership` row
instead of getting a new one — each company-caregiver affiliation period
must be an immutable domain-history record, and `AuditLog` must not be the
only source of that history. Fixed in place on the same branch/PR (no new
branch, no new PR):

- Removed `OrganizationMembership.unique_together`; added two conditional
  `Meta.constraints` (`django.db.models.UniqueConstraint(condition=Q(...))`):
  `uniq_active_caregiver_membership_per_user` (at most one ACTIVE
  caregiver-role membership per user, globally) and
  `uniq_open_membership_per_org_user_role` (at most one open PENDING/ACTIVE
  membership per organization+user+role_type). Terminal rows are excluded
  from both, so they accumulate without limit.
- `approve_affiliation_request()`/`invite_caregiver()` now always
  `OrganizationMembership.objects.create()` a new row — never reactivate a
  prior terminal one — wrapped in `IntegrityError`-to-`AccountsError`
  translation (mirrors `CaregiverSkillService.add_skill()`'s existing
  precedent) so a duplicate-open-row race fails cleanly and idempotently.
- New `closure_reason` field (`AffiliationClosureReason` choices:
  invitation declined by caregiver, invitation cancelled by company,
  terminated by company, left by caregiver) gives a machine-readable end
  reason distinct from free-text `termination_reason` and from
  `CompanyAffiliationRequest.status=REJECTED` (already distinct for
  "join request rejected by company," unchanged).
- Added a matching conditional constraint on `CompanyAffiliationRequest`
  (`uniq_pending_affiliation_request_per_caregiver`) closing the same
  idempotency gap for duplicate pending join requests.
- Activation continues to lock the caregiver-owned `CaregiverProfile` row
  first (unchanged concurrency precedent), now proven against a
  cross-organization race that uses one join request and one invitation
  (the old two-simultaneous-pending-requests race technique no longer
  applies now that pending requests are themselves constrained to one per
  caregiver).
- `provider_portal/company.html`/`organization_portal/staff_list.html`
  updated to display `closure_reason` and each affiliation period's
  joined/terminated dates; no selector query change needed —
  `list_membership_history_for_caregiver()`/`list_staff()` already
  returned every row, so repeated periods with the same company already
  render as separate list entries.

5 new/rewritten tests in `apps.accounts.tests.test_affiliation_lifecycle`
prove: terminate → re-invite → accept creates two separate membership
records; the first remains terminal and unchanged; the second becomes
active; two concurrent organizations still cannot activate the same
caregiver; duplicate pending invitations/requests are rejected
idempotently; historical rows do not grant current company access; two
periods with the same company render as two separate history rows. One
migration (`accounts/0009_alter_organizationmembership_unique_together_and_more.py`).
Full regression 2150/2150 green (2145 + 5 net). See
`traceability/ARCHITECTURE_DECISION_LOG.md` ADM-023's remediation note.
Blocker 2 (documentation cleanup) addressed the same session — see the
9 files listed in `traceability/IMPLEMENTATION_JOURNAL.md`'s PR #12
remediation entry.

### PR #12 — MERGED (2026-07-16)

Final architecture re-review confirmed both blockers resolved and the
saved PR description accurate. Merged via `merge_pull_request` (merge
commit `ffb82a4767ba115dc158cb845b92211ccbc30d00`). Local `main`
fast-forwarded to match `origin/main`. **Sprint 3.1 (Company Foundation
and Caregiver Management) is now CLOSED and on `main`.**

### Sprint 3.2 — Company Professional Profile and Public Presence — IMPLEMENTED (2026-07-16)

Branched fresh from merged `main` (`phase3-company-professional-profile`,
from `ffb82a4`) per governance. Current-state inspection (required before
any implementation) found most target capabilities already built by
Epic 06 Sprint 2 and Sprint 3.1 — `OrganizationProfile`'s public/contact
fields, `OrganizationProfileUpdateService` (permission-gated
profile/services update), logo/cover upload, and the public
organization-profile page at `/find-an-organization/<supplier_id>/` all
already existed. No parallel model was introduced; the sprint closed the
genuinely missing or broken pieces:

- **New field:** `OrganizationProfile.headline` (professional
  headline/short introduction — the one field Epic 06 Sprint 2 had not
  built, mirroring `CaregiverProfile.specialty`'s existing role for
  caregivers). One migration
  (`accounts/0010_organizationprofile_headline.py`). Wired through
  `OrganizationProfileUpdateService.update_profile()`, both portal and
  public ViewModels, the profile-edit form, and both the portal and
  public profile templates.
- **Fixed a real canonical-visibility-policy bug:**
  `OrganizationPublicProfileService.get_profile()` previously
  re-implemented its own, weaker visibility check (`profile_status !=
  "active"` only) instead of calling `common.is_publicly_visible_attrs()`
  — the same function the caregiver public-profile page already used, and
  the one that function's own docstring already claimed every public
  entry point called. An ACTIVE-but-UNVERIFIED organization, or one whose
  admin account had been deactivated, was therefore incorrectly publicly
  visible. Fixed to call the same canonical function — one visibility
  policy, no second implementation. Every pre-existing test fixture that
  exercised "should be visible" now explicitly sets
  `verification_status=VERIFIED` (previously they happened to pass only
  because the weaker check didn't look at it).
- **Fixed the SEO metadata bug on `organization_profile.html`**
  (KL-021/BG-027, explicitly deferred by Sprint 2.6 as caregiver-only
  scope, now in Sprint 3.2's own scope): `page_url` was hardcoded to the
  organization list path instead of the profile's own canonical URL, and
  `canonical_url` was never passed at all — fixed to match the caregiver
  profile page's own established `{% url %}`-based pattern exactly.
- **Permission-gated organization media mutations:** the four
  `ProfileMediaService` organization logo/cover set/remove methods had no
  permission check at all — only `resolve_organization()`'s ownership
  boundary. Now require an `actor` kwarg and check the existing
  `ORGANIZATION_PROFILE_UPDATE` key (whose own description already
  claimed to cover "media"), mirroring
  `OrganizationProfileUpdateService`'s exact `ownership_authorized_by`
  shape and Sprint 3.1's own permission-key-hardening precedent.
  `resolve_organization()` remains the real access boundary; this is
  explicit, audited defense-in-depth, not a behavior change for admins.
- **Made media file replacement transaction-safe:**
  `ProfileMediaService._replace()` used to delete the old physical file
  *before* saving the new field value — unsafe, since storage deletion
  isn't transactional (the same class of problem Sprint 2.2's gallery
  remediation already fixed). Fixed identically: save first, delete the
  old file via `transaction.on_commit()`. Applies to both caregiver and
  organization media (one shared helper).
- **Public contact policy** stays "never expose phone/address, route to a
  generic contact CTA" — the existing, already-privacy-safe default, not
  a new opt-in toggle (no evidence of demand for one). **Service coverage
  summary** is `city` + the existing `service_names` (from
  `service_categories`) — no new service-area model, since none is
  needed. **Company caregiver aggregation** stays a count only
  (`active_provider_count`) — already privacy-safe, no caregiver identity
  exposed. `duplicate company-service records` cannot occur —
  `service_categories` is a single array field on `ServiceSupplier`, not
  separate rows.

10 new/rewritten tests (4 `apps.public_site.tests
.test_organization_profile_service` + 6 `apps.organization_portal.tests
.test_profile`) prove: unverified/pending-verification/admin-deactivated
organizations are excluded from the public profile; headline round-trips
through the edit form and appears on both profile pages; media
upload/remove is denied for unauthenticated and non-admin-staff callers
and structurally cannot reach a second organization; a terminated
(former) caregiver staff member retains no portal access. One migration.
Full regression 2160/2160 green (2150 + 10 net). Branch
`phase3-company-professional-profile`, PR #13 created — see
`traceability/IMPLEMENTATION_JOURNAL.md` and
`ARCHITECTURE_DECISION_LOG.md` ADM-024.

### PR #13 Architecture Review Remediation — Render the Public Company Logo (2026-07-16)

Architecture review found one remaining scope blocker: Sprint 3.2's own initials-only public
logo/avatar decision (Decision 6(a) in ADM-024, originally reasoned as "matches the caregiver
public profile's own established precedent") left the logo capability disconnected from the
public professional profile Sprint 3.2 exists to build — the organization's already-uploaded,
already permission-gated, already file-safety-hardened logo was never actually shown to a
public visitor. **That original reasoning is superseded**, not merely appended past: exposing
the real logo is the correct minimum-vertical-slice completion, not a redesign.

- Added `logo_url` to the public `OrganizationProfileViewModel`, populated from the existing
  `OrganizationProfile.logo` field's own `.url` (Django's standard storage-URL abstraction —
  never a filesystem path), exposed only when `entity.logo` is actually present. No new
  field, no new model, no new upload path, no second media pipeline.
  `organization_profile.html` now passes `src=profile.logo_url` to the existing
  `ui/components/data/avatar.html` include — that component's own pre-existing fallback
  (initials, when `src` is empty) now serves its originally intended purpose: the fallback
  for *no logo uploaded*, not a blanket "logo capability is public-facing only", not a
  substitute for it.
- Canonical visibility policy (`common.is_publicly_visible_attrs()`) is unchanged and still
  gates the entire profile, logo included — an unverified, suspended, rejected, or
  admin-deactivated organization returns `None`/404 exactly as before, regardless of whether
  it has a logo.
- The organization-portal admin's own profile page already showed the real logo before this
  remediation (private, authenticated, unrelated to the public-visibility boundary) — no
  change was needed there.

7 new tests prove: a publicly eligible organization with a logo exposes/renders it;
one without a logo falls back to initials; an unverified organization with a logo still
returns no public profile; an organization with a deactivated admin account and a logo
remains hidden; no filesystem path or private media metadata appears in the response
(`logo_url` differs from `logo.path`, no organization internal id appears in the URL); the
existing query-count contract is unaffected (reading `.url` off the already-resolved entity
adds no query). No model, migration, permission, file-lifecycle, or shared visibility-policy
code changed — only ViewModel/service/template projection — so no full-regression rerun was
required per this remediation's own policy.

### PR #13 — MERGED (2026-07-16)

Final pre-merge verification confirmed the branch was unchanged at `832b51a`, the saved PR
description reflected the final logo-rendering behavior, `git status`/`git diff --check`/
`manage.py check` were all clean, and the accepted full-regression baseline (2160/2160)
remained valid (no code changed after the baseline run). Merged via `merge_pull_request`
(merge commit `49b643e130018b959938907e9a5d1ae491d51f6c`). Local `main` fast-forwarded to
match `origin/main`. **Sprint 3.2 (Company Professional Profile and Public Presence,
including the PR #13 architecture-review remediation) is now CLOSED and on `main`.**

### Sprint 3.3 — Company Public Directory and Discovery — IMPLEMENTED, PR OPEN (2026-07-16)

Branched fresh from merged `main` (`phase3-company-public-directory`, from
`9929da5`) per governance. Current-state verification (Step 1, mandatory
before implementation) found no "browse companies" surface existed:
`/organizations/` renders a zero-context B2B recruitment page, and
`OrganizationPublicProfileService`'s own docstring is explicit it is
"deliberately not the full organization directory... only single-
organization lookup." ADR (Step 2, mandatory — see
`traceability/ARCHITECTURE_DECISION_LOG.md` ADM-025) chose **Option
B**: keep `/organizations/` unchanged, add a new, dedicated
`/find-an-organization/` directory route — mirrors the established
`/caregivers/` vs `/find-a-caregiver/` precedent exactly; rejected Option
A (repurposing `/organizations/`) on SEO/backward-compatibility/
navigation-consistency grounds.

- `OrganizationDirectoryService` (new file,
  `apps.public_site.services.organization_directory_service`): search +
  city + service-category filters, pagination, canonical public
  visibility. Reuses `SupplierSearchService.filter_suppliers()`/
  `DiscoveryRankingService.rank()` unmodified and
  `common.bulk_supplier_attrs()`/`is_publicly_visible_attrs()` unchanged
  — no second search/ranking/visibility implementation. Scoped to
  `SupplierType.ORGANIZATION` only, disjoint from
  `CAREGIVER_SUPPLIER_TYPES`.
- `common.py` gained `parse_page()`/`build_pagination()`, extracted
  verbatim (zero behavior change) from `CaregiverDirectoryService`'s own
  former private `_parse_page()`/`_build_pagination()` — "do not
  duplicate logic" required lifting them to the shared module; both
  directory services now call them as thin wrappers.
- `OrganizationStaffService.list_active_caregiver_counts_bulk()` (new
  method on the existing service): one grouped query regardless of
  organization count — avoids a KL-012-class N+1 when rendering up to 12
  directory cards per page (`active_provider_count`). An initial
  implementation also called `CatalogQueryService.list_active_categories()`
  once per card for `service_names` — caught by the query-budget test
  suite itself (1-vs-5-candidate count mismatch) and fixed by resolving
  categories once per `search()` call instead.
- New `OrganizationCardViewModel`/`OrganizationDirectoryFiltersViewModel`/
  `OrganizationDirectoryPageViewModel` (reuse the existing generic
  `FilterOptionViewModel`/`PaginationLinkViewModel`/`PaginationViewModel`/
  `RatingSummaryViewModel` unchanged), new `find_an_organization` view,
  new route `find-an-organization/` (ordered before the existing
  `find-an-organization/<uuid:supplier_id>/` detail route), new template
  `organization_directory.html` and component `organization_card.html`
  (mirror `caregiver_directory.html`/`caregiver_card.html`'s structure),
  new "پیدا کردن سازمان" nav links in `base_public.html` (desktop, mobile,
  footer — distinct from the existing "برای سازمان‌ها" recruitment link).
- Kept `search()`'s signature deliberately parallel to
  `CaregiverDirectoryService.search()`'s own (minus the two caregiver-only
  params) — composability for a future Supplier-level discovery layer,
  without building that layer or an abstract base class now (explicitly
  out of scope).

No new model, no migration (confirmed by `makemigrations --check
--dry-run`; `accounts`/`public_site` alone report no changes). Read-only,
unauthenticated, zero permission/tenancy impact. 25 new tests (18
`apps.public_site.tests.test_organization_directory_service` — visibility,
search, city/service filters, pagination, logo, no-private-field-leakage,
0/1/5/20+ candidate query-budget — + 7 `test_views.py`
`FindAnOrganizationViewTest` — HTTP-level 200s, filtering, malformed-page
safety, route-ordering, marketing-page regression guard). Full regression
run once (cross-cutting `common.py` refactor touching 3 existing
services): 2192/2192 green (2167 baseline + 25 net). Branch
`phase3-company-public-directory`, PR #14 created against `main`. See
`traceability/ARCHITECTURE_DECISION_LOG.md` ADM-025.

### PR #14 — MERGED (2026-07-16)

Final architecture and implementation review approved the branch with no blocking issues
across architecture, domain ownership, public visibility, privacy, tenant isolation,
routing, query performance, tests, documentation, and scope control. Two non-blocking
observations recorded, explicitly not actioned this sprint: `available_cities()` performs a
second candidate-resolution pass (matches the existing caregiver-directory precedent, not a
new inconsistency); `list_active_caregiver_counts_bulk()` may eventually belong in a
dedicated read selector rather than `OrganizationStaffService` (introducing that abstraction
now is not justified). Pre-merge verification confirmed the branch unchanged at `7c39917`,
the saved PR description accurate (ADM-025 Option B, `/organizations/` retained,
`/find-an-organization/` added, 25 new tests, 634/634 affected suites, 2192/2192 full
regression, no model/migration change), and `git status`/`git diff --check`/`manage.py
check` all clean. Merged via `merge_pull_request` (merge commit
`b78d6a293ab90831c10b2a8ad1d1d49aab06fa86`). Local `main` fast-forwarded to match
`origin/main`; `manage.py check` exits 0. **Sprint 3.3 (Company Public Directory and
Discovery) is now CLOSED and on `main`.**

---

## IMMEDIATE NEXT TASK

### Phase 3 is formally CLOSED. Phase 4 — Customer Portal is the active next phase. The Sprint 4.0 code-free assessment found it already substantially implemented (Epic 07); the immediate next task is a bounded Favorites implementation sprint, the one confirmed gap.

Defined in **`IMPLEMENTATION_ROADMAP.md`** (the single active implementation
order).

Phase 1 and Phase 2 (all sprints, including Sprint 2.6 + its PR #11
KL-012 remediation) are fully closed and merged to `main`. Sprint 3.1 is
also fully closed and merged to `main` via PR #12 (including its
architecture-review remediation that preserves affiliation-period
history and cleaned up active documentation). Sprint 3.2 is also fully
closed and merged to `main` via PR #13 (including its architecture-review
remediation that renders the public company logo). Sprint 3.3 (Company
Public Directory and Discovery) is also fully closed and merged to `main`
via PR #14 — see the entry immediately above.

**Phase 3 is formally CLOSED (2026-07-16).** A code-free architecture
assessment confirmed every Phase 3 roadmap acceptance criterion is
delivered and merged: company identity/verification, caregiver
affiliation lifecycle, company caregiver management, company professional
profile, public company profile, public company directory/discovery,
company services, permissions/tenant isolation, dashboard/operational
summaries, notifications, and public visibility/privacy boundaries.
**No Sprint 3.4 is required.** The following items were evaluated and
found to be safely deferrable — they do NOT block Phase 4 and are
explicitly not required for Phase 3 closure:

1. Company financial overview + reports (extend), company invoicing —
   not started, explicitly out of Sprint 3.2/3.3's scope, and structurally
   blocked on `quality/COMPLETION_BACKLOG.md` BG-008 (Enable Pre-Service
   Payment Gate) — a Financial/Payment-phase dependency, not a Company
   Portal defect (`organization_portal`'s `financial_view` is correct and
   read-only; it is simply empty until the payment gate is enabled).
   Company public profile/discovery parity with the caregiver side is
   **fully addressed** by Sprint 3.3 (public directory, search,
   city/service filters) on top of Sprint 3.2's profile-page work
   (headline, canonical visibility policy, SEO fix, permission-gated
   media, transaction-safe media replacement, public logo rendering) —
   gallery/certificates generalized to organizations remains open
   (deferred, no product-value trigger; Sprint 3.3 also explicitly did
   not implement `SupplierDirectoryService`, advanced filters, or new
   ranking algorithms — see ADM-025).
2. Company gallery/social feed, messaging, AI verification, payroll/
   salary, HR leave workflow, caregiver scheduling by company — not
   started, explicitly out of Phase 3's scope per its own governance;
   remain out of scope for Phase 4 as well (later-phase or no-evidence
   items, not Customer Portal prerequisites).
3. No flash-message/error-surfacing framework exists for POST-action
   portal views (invite/approve/reject/terminate/etc. in
   `organization_portal`/`provider_portal`, and any future `portal`
   customer-facing mutation) — a failed action silently redirects back
   with no visible feedback, matching this app's own pre-existing
   convention for action buttons (`staff_approve_view`/
   `staff_suspend_view` have never surfaced errors either). This is a
   **cross-portal infrastructure item, not a Company-Portal-specific
   blocker** — its own backlog entry (BG-029) names `apps.portal` (the
   Customer Portal) as equally affected, so it is evaluated as part of
   the Phase 4 Sprint 4.0 assessment rather than as a Phase 3 sprint
   (`quality/DEFECT_AND_RISK_REGISTER.md` KL-022).
4. Organization individual-review listing (aggregate rating exists;
   per-review detail does not, unlike the caregiver profile's
   `common.reviews_to_viewmodels()`) — cosmetic parity gap, zero domain
   dependency, does not block Phase 4.
4. ~~Known, recorded during BG-022's remediation~~ — **RESOLVED (PR #11
   remediation, 2026-07-15):** the pre-existing per-candidate query cost
   in directory ranking/card-building (`DiscoveryRankingService.rank()`,
   `SupplierSearchService.filter_suppliers()`'s city filter,
   `CaregiverDirectoryService._build_card()`) is fixed via bulk selector
   methods — see `quality/DEFECT_AND_RISK_REGISTER.md` KL-012 (now
   RESOLVED) and `ARCHITECTURE_DECISION_LOG.md` ADM-022's remediation
   note.
5. Known, recorded during Sprint 2.3: `CaregiverSkill.name` remains
   free-text with no catalog/normalization — see
   `quality/DEFECT_AND_RISK_REGISTER.md` KL-016, deferred (a future
   modeling decision, not a UI-completion task).
6. Known, recorded during Sprint 2.2/PR #7: gallery orphan-file cleanup/
   retry is not automated (KL-014) and decoded-image dimension/pixel
   limits are fixed, not tenant-configurable (KL-015) — both deliberate,
   not defects.
7. Known, pre-existing, unchanged: production media storage strategy
   (currently local `FileField`/`FileSystemStorage`, no S3/CDN) —
   BG-021's original dependency note.
8. Known, recorded during Sprint 2.4: per-caregiver time zone is not
   modeled — see `quality/DEFECT_AND_RISK_REGISTER.md` KL-018 /
   `quality/COMPLETION_BACKLOG.md` BG-024, deferred (no evidence of
   multi-time-zone demand).
9. Known, recorded during Sprint 2.5, unchanged since: no canonical
   bonus/penalty representation exists — see `quality/DEFECT_AND_RISK_
   REGISTER.md` KL-020 / `quality/COMPLETION_BACKLOG.md` BG-026's "not
   in scope" note, deferred (no evidence to invent one against). This
   was the one Phase 2 acceptance criterion satisfied only as an
   explicitly accepted external-domain dependency, not a
   caregiver-profile defect.
10. **RESOLVED (Sprint 3.2, 2026-07-16).** The SEO `page_url` bug on
    `organization_profile.html` (KL-021/BG-027, recorded during Sprint 2.6
    as deferred/caregiver-only scope) was fixed in Sprint 3.2 — confirmed
    by direct template inspection during the Phase 3 closure review
    (2026-07-16); `quality/COMPLETION_BACKLOG.md` BG-027's own entry was
    found not marked RESOLVED (a documentation-only drift) and corrected
    at the same time. The same unassociated-`<label>` accessibility
    pattern in `organization_portal`/`admin_portal`/`portal` (customer)
    templates remains open, out of caregiver-only scope, unrelated to
    Phase 3 closure.
11. Known, recorded during Sprint 3.1, re-evaluated at Phase 3 closure
    (2026-07-16): no flash-message/error-surfacing framework exists
    anywhere in this codebase's portals — see item 3 above (KL-022). Not
    a Phase 3 blocker; scheduled for evaluation as part of the Phase 4
    Sprint 4.0 assessment since `apps.portal` (Customer Portal) is
    equally affected.

Note: the previously listed follow-up "Phase 2: OrderOfferService" is now
scheduled as roadmap Phase 5 (Marketplace Order Workflow) and must not be
started before roadmap Phases 1–4.

### Phase 4 — Customer Portal: Sprint 4.0 Architecture Assessment (2026-07-16, code-free)

Performed immediately after Phase 3's formal closure, on a documentation-only branch
(`docs/phase3-closure-phase4-assessment`) per explicit governance for this task — no product
code, model, migration, view, template, service, selector, or test was changed.

**Major finding:** the Customer Portal (`apps.portal`) is NOT a greenfield build. Direct
inspection (not documentation) found a mature, already-tested body of work built under
"Epic 07 — Customer Experience and Portal Completion" (per every relevant service's own
docstring), predating this repository's current Phase 1–5 roadmap numbering:
`CustomerProfile`/`ElderProfile`/`TrustedContact` models; a full order-request wizard
(care-recipient → service → schedule → address → notes → review → submit); order
list/detail/history with active/completed/cancelled filters
(`OrderQueryService.list_for_customer()`); per-order financial pay/approve/dispute pages with
real `apps.commission` engine integration (`PreServicePaymentService`,
`ObjectionPeriodService`, `DisputeService`); a customer-facing invoices/payments page
(`CustomerPaymentsPresentationService`, reading `FinancialDocumentService
.list_for_payer_party()` — this domain has no separate "receipt" document type, a paid
invoice serves that role); a written-reviews list; notifications; public order-share links
(create/revoke); dashboard; profile/settings editing — all with dedicated test files
(`apps.portal.tests`, 1063 test lines across 9 files) including an explicit IDOR-focused
suite (`test_access_control.py`) proving the 404-not-403 ownership-scoping convention
(`resolve_customer_profile()` reads only `request.user.person.customer_profile`, never
accepted from the URL/body).
`IMPLEMENTATION_ROADMAP.md`'s own Phase 4 header already read "(production complete)" — only
its scope-line text (still describing invoices/payments/dashboard/orders as partially "new")
was stale relative to the code. This documentation drift is recorded, not silently corrected
beyond what this closure task authorizes.

**The one confirmed, repository-wide-verified gap: Favorites/saved-suppliers.** No
`Favorite`/bookmark/shortlist/saved-supplier model or equivalent exists anywhere in the
repository (confirmed by broad case-insensitive search across all app source).

See the full 29-point assessment in `traceability/IMPLEMENTATION_JOURNAL.md`'s "Phase 3
Closure and Phase 4 Sprint 4.0 Assessment" entry.

**Recommended first Phase 4 sprint:** Sprint 4.0 — Customer Favorites (Saved Providers), a
minimum complete vertical slice: one new `Favorite` model (customer → supplier, tenant-scoped,
unique constraint), a service layer reusing existing supplier/visibility selectors, a toggle
affordance on the existing public caregiver/organization profile pages, and a portal "My
Favorites" list page. Deliberately does NOT bundle a flash-message framework, order-history
changes, or any financial/invoice work into the same sprint — none of those need new work in
Phase 4. See the assessment for the full in-scope/out-of-scope breakdown, model-shape
options, and the exact implementation prompt.

**Do not begin Phase 4 implementation without a fresh current-state-verification instruction
that explicitly authorizes branch creation and code changes** — this assessment is planning
output only, per this task's own governance.
