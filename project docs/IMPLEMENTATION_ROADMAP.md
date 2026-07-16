# IMPLEMENTATION ROADMAP

**Created:** 2026-07-14
**Verified against HEAD:** ce3b30e0f3c06d7b058587f3e75c357bfe588415 ("Repository documentation reorganization")
**Post-merge update:** 2026-07-14 — PR #1 merged to main (`eb51018`): documentation sync + BG-002 fix are on main; P0 hygiene complete; **Phase 1 is the active phase**
**Phase 1.1 update:** 2026-07-15 — manual document verification workflow merged to main via PR #3 (merge commit `278098b`); full regression 1721/1721 green at merge
**Phase 1.2 update:** 2026-07-15 — verification completion and activation rules implemented on branch `phase1-verification-activation-rules` (from main @ `278098b`); no migration; PR not yet merged
**Phase 1.3 update:** 2026-07-15 — deterministic profile completion + controlled activation implemented on branch `phase1-activation-completion-final` (from main @ `860640e`, the merged Phase 1.2 PR #4); no migration; PR #5 created; **Phase 1 acceptance criteria now fully met**
**Phase 1.3 remediation update:** 2026-07-15 — PR #5 review found AuditLog existence, not `profile.status`, was the activation signal; fixed in place (registration now creates DRAFT profiles, ProfileActivationService performs a real DRAFT->ACTIVE transition, `is_activated()` reads `profile.status` directly); no migration; **MERGED to main via PR #5 (merge commit `0c9d70c`); Phase 1 is CLOSED**
**Phase 2.1 update:** 2026-07-15 — caregiver professional profile foundation (skills, experience, verified-credential public summary, corrected public-profile eligibility) implemented on branch `phase2-caregiver-professional-profile-foundation` (from main @ `0c9d70c`); 1 new migration (2 new tables only); PR #6 created
**Phase 2.1 remediation update (BG-022):** 2026-07-15 — PR #6 review found the eligibility fix was added only to the detail page, not directory/home-page listings; fixed by extending `common.is_publicly_visible_attrs()` into the single canonical rule every public entry point shares; no migration; PR #6 updated in place
**PR #6 merge update:** 2026-07-15 — final verification confirmed the branch was exactly two commits ahead of main, in-scope only, and green (1887/1887); **MERGED to main via PR #6 (merge commit `c5259b3`); Phase 2.1 + BG-022 remediation are CLOSED**
**Sprint 2.2 update:** 2026-07-15 — caregiver gallery and media portfolio (`CaregiverGalleryItem`, `CaregiverGalleryService`, provider-portal gallery management, public-profile gallery section reusing the existing BG-022 canonical visibility policy) implemented on branch `phase2-caregiver-gallery-media` (from main @ `c5259b3`); 1 new migration (1 new table); PR #7 created
**Sprint 2.2 remediation update (PR #7 review):** 2026-07-15 — PR #7 review found an unsafe file-deletion transaction order (physical file deleted before the DB row, inside the same transaction) and missing decoded-image safety limits (byte-size cap alone doesn't bound decompression-bomb conditions); fixed by deferring physical deletion to `transaction.on_commit()` and adding width/height/pixel-count limits + Pillow decompression-bomb handling to `image_validation.validate_image()`; no migration; PR #7 updated in place
**PR #7 merge update:** 2026-07-15 — final verification confirmed the branch was in-scope only, deletion-order/rollback/storage-failure/image-safety behavior all directly verified against the code, and green (1948/1948); **MERGED to main via PR #7 (merge commit `f7b7b2b`); Sprint 2.2 + PR #7 remediation are CLOSED**
**Sprint 2.3 update:** 2026-07-15 — professional credibility layer (precise verification badges, skill/experience visibility toggles, derived highlights, owner-facing "expiring soon" state, self-declared/verified distinction) implemented on branch `phase2-caregiver-credentials-skills-experience-ui` (from main @ `f7b7b2b`); zero new migration; PR #8 created
**PR #8 merge update:** 2026-07-15 — final verification confirmed the branch was unchanged from its recorded 1984/1984 verification, in-scope only, and the PR description accurately reflected the repository (a prior reporting error about a public-listing visibility gap was corrected, no code change needed); **MERGED to main via PR #8 (merge commit `20c532e`); Sprint 2.3 is CLOSED**
**Sprint 2.4 update:** 2026-07-15 — caregiver availability and working schedule (weekly working-hour intervals with overlap/duplicate refusal, provider-portal edit/enable-disable UI, canonical structured `AvailabilityQueryService.evaluate()`, privacy-safe public availability summary) implemented on branch `phase2-caregiver-availability-schedule` (from main @ `20c532e`); zero new migration — `apps.availability`'s Module 10 foundation already modeled every entity needed; PR #9 created
**PR #9 review remediation update:** 2026-07-15 — review found the overlap validation above was not concurrency-safe (unlocked check-then-insert); fixed by locking the owning `ServiceSupplier` row (`select_for_update()`) before overlap validation in `add_working_window()`/`update_working_window()`, mirroring `CaregiverGalleryService.add_item()`'s existing precedent; 9 new `TransactionTestCase` tests prove the invariant against real concurrent transactions; zero new migration; full regression 2033/2033 green; remediation kept inside PR #9
**PR #9 merge update:** 2026-07-15 — final verification confirmed the branch was unchanged from its recorded 2033/2033 verification, in-scope only, and the supplier-row locking behavior directly verified against the code; **MERGED to main via PR #9 (merge commit `125dd3b`); Sprint 2.4 (+ concurrency remediation) is CLOSED**
**Sprint 2.5 update:** 2026-07-15 — caregiver professional dashboard (work summary, financial overview, wallet movements, invoice summary, reviews/reputation, professional statistics) implemented on branch `phase2-caregiver-professional-dashboard` (from main @ `125dd3b`); zero new migration — every new selector reads existing tables via new, minimally-extended methods on `OrderQueryService`/`FinancialDocumentService`/`ReputationService`; **MERGED to main via PR #10 (merge commit `9a26024`)**
**Sprint 2.6 + PR #11 update:** 2026-07-16 — public profile finalization and Phase 2 acceptance, plus the PR #11 KL-012 query-performance remediation, both **MERGED to main via PR #11 (merge commit `90e608d`); Phase 2 is CLOSED**
**Sprint 3.1 update:** 2026-07-16 — company foundation and caregiver management (see PHASE 3 section below) implemented on branch `phase3-company-portal-foundation` (from main @ `90e608d`); PR #12 created
**PR #12 architecture-review remediation update:** 2026-07-16 — preserve affiliation-period history (see PHASE 3 section's remediation entry); applied in place on the same branch/PR; full regression 2150/2150 green
**PR #12 merge update:** 2026-07-16 — final architecture re-review confirmed both blockers resolved and the saved PR description accurate; **MERGED to main via PR #12 (merge commit `ffb82a4767ba115dc158cb845b92211ccbc30d00`); Sprint 3.1 is CLOSED**
**Sprint 3.2 update:** 2026-07-16 — company professional profile and public presence (see PHASE 3 section's Sprint 3.2 entry) implemented on branch `phase3-company-professional-profile` (from main @ `ffb82a4`); 1 new migration; full regression 2160/2160 green; PR #13 created
**PR #13 architecture-review remediation update:** 2026-07-16 — render the public company logo (see PHASE 3 section's remediation entry); applied in place on the same branch/PR; no model/migration/permission change; **PR #13 still not merged — awaiting review**
**Branch verified:** phase3-company-professional-profile (via claude/taasisat-senior-state-verify-9dzzlm)
**Authority:** This roadmap replaces every previous implementation order (including
`project docs/03_NEXT_TASK.md` sequencing and the archived Offer Marketplace phase plans).
The repository code remains the ultimate source of truth.

---

## 1. CURRENT REPOSITORY STATUS (verified by direct inspection)

| Fact | Evidence |
|------|----------|
| Working tree | CLEAN — `git status` reports nothing to commit |
| OrderOffer Phase 1 | **COMMITTED** in HEAD `ce3b30e` (`src/apps/orders/migrations/0008_orderoffer.py`, `models.py:363-478`, `tests/test_order_offer_model.py`). Docs claiming "in working tree, not committed" are stale. |
| Apps | 25 Django apps + config (`src/apps/`) |
| Tests | 196 test files, 1,672 `def test` methods (grep-verified) |
| Templates | 112 HTML templates across 7 template roots |
| OrderOfferService | **DOES NOT EXIST** — `src/apps/orders/services/` contains only eligibility_service, order_creation, queries, share_links, status_machine, timeline |
| Payment PSP | Fake only — `src/apps/payments/providers/fake.py` is the sole provider |
| Notifications | Fake providers only |
| Document verification | Upload-only. `VerificationDocument` model docstring (`src/apps/accounts/models/media.py`) states the admin verification workflow "does not exist yet and is explicitly not built here" |
| Admin portal | 13 views, financial/dispute focused (`src/apps/admin_portal/urls.py`) — no verification review, no user/profile management |
| Test execution | EXECUTED 2026-07-14 at ce3b30e (PostgreSQL 16.13, Django 5.2.16, Python 3.11.15): `check` exit 0; `migrate` exit 0 (0008_orderoffer applies cleanly); `makemigrations --check` exit 1 (pre-existing cosmetic drift, same as CL-013); full suite 1662 run / 2 errors, both the pre-existing seed order_number collision (`TEST_EXECUTION_LOG.md`) |

### What exists and works (per code inspection + committed test suite)

- OTP phone auth (fake SMS), customer/caregiver/company registration (`accounts/views.py`, `accounts/services/registration.py`)
- Customer portal: dashboard, profile, settings, care recipients CRUD, 7-step order wizard, requests, per-order financial view + pay, reviews, share links, notifications (`portal/urls.py` — 30+ routes)
- Provider portal: dashboard, assignments (confirm/decline/start/complete), availability, earnings, profile + avatar/cover, documents (`provider_portal/urls.py` — 21 routes)
- Organization portal: dashboard, staff approve/suspend, assignment center, capacity, financial, reports, profile, documents (`organization_portal/urls.py` — 18 routes)
- Public site: caregiver/organization directories and public profiles with ratings and reviews (`public_site/`)
- Order lifecycle state machine, matching, operator assignment, execution sessions
- Financial core: FinancialDocument chain, escrow with conservation constraints, commission engine (contracts, snapshots, deadlines, objection periods, disputes + resolution), canonical wallet, ledger, settlement orchestration
- Job system, event outbox, RBAC with permission registry

---

## 2. REMAINING IMPLEMENTATION (gap inventory, all repository-evidenced)

| # | Gap | Evidence |
|---|-----|----------|
| G1 | Manual verification workflow (platform owner reviews identity/license documents) | No admin-portal route touches `VerificationDocument`; model docstring says workflow not built |
| G2 | Caregiver public "Instagram-like" profile media: gallery, certificates showcase, skills | `grep -ri gallery\|portfolio\|skill` over `src/apps` → zero models/services; only avatar + cover exist |
| G3 | OrderOfferService + marketplace flow (publish, submit, select, hold, payment timeout/retry, accept) | Model exists; zero services/views/APIs reference OrderOffer outside model/admin/tests |
| G4 | Company invitation system (company-initiated invite, join code UX, removal) | Only caregiver-initiated `CompanyAffiliationRequest` at registration + approve/reject (`accounts/services/affiliations.py`); no invite, no remove-member service |
| G5 | Customer favorites | `grep -ri favorite` → nothing |
| G6 | Customer invoices/receipts pages | Per-order financial view exists; no invoice list/receipt/export UI |
| G7 | Invoice verification/approval/adjustment/export workflow | `finance/services/document_service.py` has create/issue/lock/cancel; no approval UI, no exports |
| G8 | Real PSP adapter | `payments/providers/` contains only `fake.py` |
| G9 | Real SMS/email/push providers | fake providers only |
| G10 | Deadline expiry + pre-service payment gates enabled end-to-end | `deadline_activation_enabled`, `preservice_payment_enabled` default DISABLED |
| G11 | Tenant-isolation hardening, RBAC toggle audit | FR-001/FR-002 in `project docs/quality/DEFECT_AND_RISK_REGISTER.md`, verified in `kernel/services/permission_service.py` |
| G12 | ~~Seed test order_number collision~~ **FIXED, merged in PR #1** | Bounded savepoint retry + 6-digit suffix in `orders/models.py`; 8 regression tests in `orders/tests/test_order_number_generation.py`; full regression 1680/1680 (CL-017, Run 009) |
| G13 | AI verification placeholder | Nothing exists; must be a deliberate no-op extension point |
| G14 | Production deployment config / CI activation | `.github/workflows/ci.yml` present, never run |

---

## 3. RECOMMENDED ORDER, DEPENDENCIES, COMPLEXITY

Pre-phase (P0 hygiene, small): ~~fix seed test race (G12)~~ — **DONE, merged in PR #1** (`eb51018`); full regression 1680/1680 green.

### PHASE 1 — Registration & Verification Workflows — **COMPLETE (2026-07-15, pending PR merge)**

**Scope:** Complete customer/caregiver/company registration; profile completion; identity + professional-license verification; **manual verification by platform owner** (admin portal review queue: approve/reject `VerificationDocument`, roll up to profile `verification_status`); future-AI-verification placeholder (strategy interface with manual implementation only).

- **Depends on:** nothing (foundation exists: `RegistrationService`, `DocumentService`, `VerificationDocument`, `VerificationStatus`)
- **Complexity:** MEDIUM. Registration flows ~80% done; the new work is the admin review workflow (G1) + status roll-up rules + notifications on decision + tests.
- **Blocking items:** none.
- **Acceptance criteria (ALL MET as of Phase 1.3, 2026-07-15):**
  1. ✅ All three registration flows produce correct profiles, roles, and (for caregivers with company code) affiliation requests — regression green.
  2. ✅ Platform admin can list pending documents, view file, approve or reject with internal reason; `reviewed_by`/`reviewed_at` recorded.
  3. ✅ Profile `verification_status` transitions UNVERIFIED→PENDING→VERIFIED/REJECTED are derived by one service only, with tests for every transition.
  4. ✅ Verification strategy interface exists with `ManualVerification` as the only registered implementation; AI slot documented, not implemented.
  5. ✅ Profile completion percent is deterministic, computed by one service (`ProfileCompletionService`, Phase 1.3), recomputed live on every read (no persisted staleness to auto-recompute).
  6. ✅ (Added by Phase 1.3) Activation eligibility is enforced by a real, controlled, authorized, audited activation action (`ProfileActivationService`) — not merely read-only.

**Phase 1.1 (2026-07-15, MERGED via PR #3) — PARTIALLY COMPLETE:**
- ✅ Criterion 1 (all three registration flows verified, 8/8 pre-existing tests re-run green — no defect found).
- ✅ Criterion 2 (`VerificationReviewService` + admin_portal queue/detail/file/review views — caregiver and organization documents only; see scope decision below).
- ✅ Criterion 4 (`DocumentVerificationEvaluator` Protocol added, no implementation).
- ✅ Criterion 3 (profile `verification_status` roll-up) — **now complete, see Phase 1.2 below**.
- ⏳ Criterion 5 (profile completion recompute) — untouched, out of scope.
- **Scope note:** `VerificationDocument` has no customer-owner FK and `CustomerProfile` has no `verification_status` field anywhere in the repository — customer document verification does not exist as a domain concept yet. This slice covers caregiver + organization documents only (the supply-side "identity verification"/"professional license" concerns the roadmap phase actually names). Adding a customer owner is new domain-model work, not a defect in this slice.

**Phase 1.2 (2026-07-15, branch `phase1-verification-activation-rules`) — verification completion and activation rules:**
- `RequiredDocumentPolicy` — the required-document policy Phase 1.1 explicitly deferred (Criterion 3's prerequisite). Smallest defensible mandatory set: caregiver = IDENTITY + BACKGROUND_CHECK; organization = REGISTRATION + OPERATING_LICENSE. Tenant-overridable via the existing `ConfigResolver` (no new configuration mechanism, no migration). Customer document verification remains out of scope (no domain-model support — see BG-016); phone/OTP verification is the current-phase mechanism for customers.
- `ProfileVerificationRollupService` — completes Criterion 3. Reuses the existing 4-value `VerificationStatus` enum as-is; `needs_correction` is a separate flag on the result, not a 5th enum value. Wired into `VerificationReviewService` and `DocumentService.resubmit()`, not left to a view/signal.
- `DocumentService.resubmit()` — owner-authorized correction/resubmission lifecycle; hardens the pre-existing `replace_document()` primitive so an already-VERIFIED document can no longer be silently reset by its owner.
- `ActivationEligibilityService.evaluate(profile)` — read-only, structured eligibility for caregiver/organization (base profile complete + documents verified + no blocking state + active account). No auto-activation/publishing wired — nothing in the existing workflow clearly requires it yet.
- 47 new tests, zero new migrations. Criterion 5 (profile completion percent auto-recompute on every mutation) and wiring `ActivationEligibilityService` into an actual activation action remain open — see `03_NEXT_TASK.md`.

**Phase 1.3 (2026-07-15, branch `phase1-activation-completion-final`) — activation and profile completion, closes Phase 1:**
- `ProfileCompletionService` — single deterministic source of truth for the base-profile-field checklist (Criterion 5). `calculate_caregiver_profile_completion()`/`calculate_organization_profile_completion()` delegate to it; bare-int signature unchanged for existing callers.
- `ProfileActivationService.activate_caregiver()/activate_organization()` — wires `ActivationEligibilityService` (unchanged) into a real, controlled action: `transaction.atomic` + row lock, permission-gated (`ACCOUNTS_PROFILE_ACTIVATE`, platform staff only), refuses owner self-activation and cross-tenant activation, refuses when ineligible with structured reasons, idempotent (AuditLog-existence based, no new field), audited. Activation is an audited approval record over the existing default-ACTIVE status, not a new lifecycle state — see `traceability/ARCHITECTURE_DECISION_LOG.md` ADM-016.
- Minimum usable platform-operator UI (activation detail + activate action, `admin_portal`) and owner-facing UI (activation status + blocking reasons on the provider/organization profile page).
- 40 new tests, zero new migrations, full regression 1808/1808 green. **All Phase 1 acceptance criteria are now met — Phase 1 (Registration and Verification Workflows) is COMPLETE.** Deferred (explicitly, recorded as BG-019, not a defect): automatic deactivation of an already-active profile when verification later becomes invalid — no suspension/revalidation workflow exists yet to hook it into.

**Phase 1.3 remediation (2026-07-15, PR #5 review, same branch) — fix activation state semantics:**
- Root defect: `AuditLog` existence, not `profile.status`, was the activation signal, because registration left profiles `ACTIVE` by default and `ProfileActivationService` never performed a real status transition in the common case.
- Fix: registration (`RegistrationService.create_caregiver()`/`create_company_admin()`, `ensure_caregiver_profile()`) now creates profiles as `ProfileStatus.DRAFT` (the existing enum value, no new status, no migration); `ActivationEligibilityService` no longer requires `status == ACTIVE` (removes the circularity); `ProfileActivationService` performs a real `DRAFT -> ACTIVE` transition and judges idempotency from `profile.status`, never `AuditLog`.
- 16 new/renamed tests, zero new migrations, full regression 1824/1824 green. See `traceability/ARCHITECTURE_DECISION_LOG.md` ADM-016's remediation note.

### PHASE 2 — Caregiver Profile (Phase 2.1 + Sprint 2.2 gallery + Sprint 2.3 credibility layer + Sprint 2.4 availability + Sprint 2.5 dashboard + Sprint 2.6 public-profile finalization — Phase 2 ACCEPTANCE CRITERIA SATISFIED, except the accepted bonus/penalty external-domain dependency, KL-020; see `project docs/PHASE_2_COMPLETION_REPORT.md`)

**Scope:** Instagram-like public profile: gallery (new model + upload service + moderation flag), certificates (surface VERIFIED `VerificationDocument`s of certificate/license types), structured skills, experience, reviews (exists), availability display (COMPLETE — Sprint 2.4), financial overview (dashboard-level summary COMPLETE — Sprint 2.5; extended reporting/exports remain), orders + history (dashboard-level summary COMPLETE — Sprint 2.5; full history pages remain).

- **Depends on:** Phase 1 (verified documents feed the certificates section).
- **Complexity:** MEDIUM-HIGH. New models (GalleryItem, Skill/CaregiverSkill), new provider-portal management pages, public-profile rendering, image validation reuse from `profile_media_service.py`.
- **Blocking items:** media storage strategy for production (currently local `FileField`) — still blocks gallery specifically; did not block Phase 2.1 (no image upload work in this slice).
- **Acceptance criteria:** caregiver can manage gallery/skills/experience from the provider portal; public profile renders gallery, certificates, skills, reviews, availability; unverified/rejected documents never leak publicly (existing rule in `media.py` docstring enforced by tests); earnings/orders/history pages complete.

**Phase 2.1 (2026-07-15, branch `phase2-caregiver-professional-profile-foundation`) — Caregiver Professional Profile Foundation:**
- Current-state inspection found most of the "biography/headline/services-offered/public-page/editing-UI" scope already implemented (Epic 06 Sprint 2) — `CaregiverProfile.bio`/`.specialty`/`.city`, `CaregiverProfileUpdateService`, `ServiceSupplier.service_categories` + `SupplierRegistry.set_service_categories()`, `CaregiverPublicProfileService`, the `/find-a-caregiver/<supplier_id>/` route, and the provider-portal profile edit pages were all reused as-is, not rebuilt.
- `CaregiverSkill`/`CaregiverExperience` (new models, one migration, 2 new empty tables) — the genuinely missing pieces. `CaregiverSkillService`/`CaregiverExperienceService`: owner-authorized CRUD, case-insensitive duplicate-skill prevention, experience date validation, both backed by DB constraints.
- `PublicCredentialSelector.for_caregiver()` (new) — derives a safe, 3-field public credential summary (type, label, expiry) from APPROVED, unexpired, caregiver-owned documents only.
- Corrected public-profile eligibility: `CaregiverPublicProfileService.get_profile()` now also requires `verification_status == VERIFIED` and the owning account's `is_active`, added locally (not in the function shared with the caregiver directory/home-page listings — see `traceability/ARCHITECTURE_DECISION_LOG.md` ADM-017 Decision 2, including the deliberate decision NOT to tighten directory/home-page eligibility in this slice).
- Provider-portal skill/experience management pages; public profile extended with skills/experience/credentials sections; owner-facing "which credentials will show publicly" panel.
- 50 new tests, full regression 1874/1874 green. **Gallery, certificates-as-gallery presentation, extended financial overview, and orders + history remain open — Phase 2 as a whole is NOT complete.**

**Phase 2.1 remediation (2026-07-15, PR #6 review, same branch) — close BG-022, unify public visibility:**
- Root defect: the eligibility fix above was added only to `CaregiverPublicProfileService.get_profile()`, not to `common.is_publicly_visible_attrs()` (the function the caregiver directory and home-page listings already shared) — a caregiver could appear in a listing while their own detail page 404'd.
- Fix: `common.is_publicly_visible_attrs()` is now the single canonical public-visibility rule (profile ACTIVE + verification VERIFIED + account active + membership active for org-affiliated caregivers), applied identically by directory search, home-page featured cards, home-page city filter, and the detail page (whose own local duplicate check was removed). `supplier_bridge.resolve_supplier_entities_bulk()` gained a `select_related()` for the account relation — a JOIN, not a new query.
- 13 new tests, zero new migration, full regression 1887/1887 green. **BG-022 is RESOLVED.** A pre-existing, unrelated per-candidate query cost in directory ranking/card-building was discovered and recorded (KL-012), not fixed (separate, out-of-scope performance task). See `traceability/ARCHITECTURE_DECISION_LOG.md` ADM-017's second remediation note.
- **MERGED to main via PR #6 (merge commit `c5259b3`, 2026-07-15).**

**Sprint 2.2 (2026-07-15, branch `phase2-caregiver-gallery-media`, from merged main @ `c5259b3`) — Caregiver Gallery and Media Portfolio:**
- `CaregiverGalleryItem` (new model, one migration, one new empty table) — plain FK child of `CaregiverProfile`, same shape as `CaregiverSkill`/`CaregiverExperience`. `CaregiverGalleryService`: owner-authorized upload (row-locked, 12-item cap)/caption-alt-visibility edit/reorder (row-locked, all-or-nothing)/remove (hard delete + physical file cleanup).
- `apps.accounts.services.image_validation.validate_image()` (new) — the Pillow-based image validator extracted from `ProfileMediaService`, now shared by both avatar/cover uploads and gallery uploads, not duplicated.
- Provider-portal gallery management page (upload/caption/visibility/reorder/remove, "N/12" count); public profile extended with a gallery photo grid, gated by the existing canonical BG-022 `common.is_publicly_visible()` policy — no second visibility rule.
- 45 new tests, full regression 1932/1932 green. **Gallery portion of BG-021 is RESOLVED.** Certificates-as-gallery presentation, availability, professional dashboard, extended financial overview, and orders + history remain open — Phase 2 as a whole is still NOT complete. See `traceability/ARCHITECTURE_DECISION_LOG.md` ADM-018.

**Sprint 2.2 remediation (2026-07-15, PR #7 review, same branch) — harden gallery file lifecycle and image safety:**
- Root defect: `CaregiverGalleryService.remove_item()` deleted the physical file before the database row, inside the same transaction — filesystem operations aren't transactional, so a later rollback could have left a live row pointing at an already-deleted file.
- Fix: the row is deleted first; physical deletion is scheduled via `transaction.on_commit()` (discarded entirely if the transaction rolls back); a storage-deletion failure after commit is logged, never raised or allowed to restore the row (orphan cleanup explicitly deferred — no cleanup-job infrastructure exists to hook into). `image_validation.validate_image()` gained `MAX_IMAGE_WIDTH`/`MAX_IMAGE_HEIGHT`/`MAX_IMAGE_PIXELS`, enforced from the image header before any full decode, plus Pillow `DecompressionBombError`/`Warning` handling — both mapped to the existing controlled error.
- 16 new tests, zero new migration, full regression 1948/1948 green. See `traceability/ARCHITECTURE_DECISION_LOG.md` ADM-018's remediation note.
- **MERGED to main via PR #7 (merge commit `f7b7b2b`, 2026-07-15).**

**Sprint 2.3 (2026-07-15, branch `phase2-caregiver-credentials-skills-experience-ui`, from merged main @ `f7b7b2b`) — Credentials, Skills, Experience, Highlights:**
- `CaregiverSkillService.toggle_visibility()` and `CaregiverExperienceService.create()`/`update()`'s new `is_visible` parameter — both models' `is_visible` column existed since Phase 2.1, unused until now; zero migration.
- Single generic "Verified" pill replaced with precise `VerificationBadgeViewModel` entries ("Profile verified", "Identity verified", "Professional credential verified"), each independently evidence-derived — proven not to be mere aliases via a required-document-policy-override test.
- Fully derived `ProfessionalHighlightsViewModel`/`HighlightsViewModel` (years of experience, verified-credential count, visible-skill count, completed-jobs/review count) — zero new queries publicly, two fixed-cost queries on the provider-portal preview.
- `RequiredDocumentPolicy.is_expiring_soon()` (30-day window, owner-facing only) + a new `expiring_soon` branch on the shared `verification_badge.html` component (also used by `apps.organization_portal`, re-verified 51/51).
- Explicit "self-declared, not platform-verified" disclaimer on the public experience section, contrasted with a "platform-reviewed" note on credentials.
- 36 new tests, zero new migration, full regression 1984/1984 green. **BG-023 is RESOLVED.** Skill catalog/normalization (KL-016), certificates-as-visual-gallery presentation, availability, professional dashboard, extended financial overview, and orders + history remain open — Phase 2 as a whole is still NOT complete. See `traceability/ARCHITECTURE_DECISION_LOG.md` ADM-019.
- **MERGED to main via PR #8 (merge commit `20c532e`, 2026-07-15).**

**Sprint 2.4 (2026-07-15, branch `phase2-caregiver-availability-schedule`, from merged main @ `20c532e`) — Caregiver Availability and Working Schedule:**
- `apps.availability` (Module 10 foundation) already modeled `ProviderWorkingWindow`/`AvailabilityBlockedPeriod` and a basic add/remove UI before this sprint — zero new models, zero new migration.
- `AvailabilityMutationService.add_working_window()`/`update_working_window()` gained duplicate/overlap refusal for active windows on the same day (`_validate_no_overlap()`); new `toggle_working_window()` for enable/disable.
- `AvailabilityQueryService.evaluate()` is now the one canonical, structured availability evaluator (`available`, `reasons`, `matched_window`, `conflicting_blocked_period`, `timezone`) — `is_supplier_available()` is a thin wrapper around it, zero behavior change for the existing `apps.booking` consumer. Deliberately kept supplier-keyed, not caregiver-keyed, to respect `apps.availability`'s position in the dependency graph.
- Provider portal gained inline working-window edit + enable/disable UI and a public-summary preview; public caregiver profile gained a privacy-safe schedule-summary section (weekday labels only, never exact times or time-off details), gated by the existing canonical `common.is_publicly_visible()` policy.
- No per-caregiver time zone modeled — platform default (`Asia/Tehran`) used throughout, documented as a known limitation, not invented.
- 40 new tests, zero new migration, full regression 2024/2024 green. **BG-025 is RESOLVED.** Per-caregiver time zone (BG-024), skill catalog/normalization (KL-016), certificates-as-visual-gallery presentation, professional dashboard, extended financial overview, and orders + history remain open — Phase 2 as a whole is still NOT complete. See `traceability/ARCHITECTURE_DECISION_LOG.md` ADM-020.

**Sprint 2.4 remediation (2026-07-15, PR #9 review, same branch) — prove and enforce availability mutation concurrency:**
- Root defect: `_validate_no_overlap()` was an unlocked `SELECT`, and `add_working_window()` took no lock at all before its check-then-insert — two concurrent transactions could both read "no conflict" before either committed and both insert overlapping active windows. `update_working_window()`'s existing window-row lock did not close the gap (a concurrent create touches no existing row; two updates to different windows each lock a different row).
- Fix: both mutation methods now lock the owning `ServiceSupplier` row first, before any overlap check — mirroring `CaregiverGalleryService.add_item()`'s existing precedent. 9 new `TransactionTestCase` tests prove the invariant against real concurrent transactions, each asserting final database state.
- Zero new migration, zero new models, full regression 2033/2033 green. See `traceability/ARCHITECTURE_DECISION_LOG.md` ADM-020's remediation note.
- **MERGED to main via PR #9 (merge commit `125dd3b`, 2026-07-15).**

**Sprint 2.5 (2026-07-15, branch `phase2-caregiver-professional-dashboard`, from merged main @ `125dd3b`) — Caregiver Professional Dashboard:**
- `apps.provider_portal.views.dashboard_view` already showed pending assignments, active visits, `ProviderReportService` performance stats, reputation, and notifications before this sprint — this sprint completed it, adding zero new views/routes.
- Work summary: two new methods on `apps.orders.services.queries.OrderQueryService` (`list_for_supplier()`/`count_by_status_for_supplier()`, mirroring `list_for_customer()`) group orders into current/upcoming/completed/cancelled — `Order.status` values only, no new statuses invented.
- Financial overview and wallet movements reuse `WalletService`/`WalletTransactionService` unchanged; invoice summary adds two new methods on `FinancialDocumentService` (`list_for_beneficiary_party()`/`count_by_status_for_beneficiary_party()`, mirroring the existing customer-side `list_for_payer_party()`).
- Reviews/reputation reuse `ReputationService.get_reputation_summary()` plus a new `list_recent_reviews_with_reviewer_names()`; professional statistics reuse `ProviderReportService` and Sprint 2.3's existing skill/credential/gallery-count definitions.
- Bonus/penalty: confirmed, by repository-wide inspection, that no canonical representation exists anywhere — documented as a gap (`FinancialOverviewViewModel.bonus_penalty_note`), not invented.
- New `CaregiverDashboardPresentationService` (`apps/provider_portal/services/dashboard_service.py`) assembles all five new sections, keeping `apps/provider_portal/views.py` free of any direct model/ORM access.
- 44 new tests, zero new migration, full regression 2077/2077 green. **BG-026 is RESOLVED.** Bonus/penalty (KL-020), skill catalog/normalization (KL-016), certificates-as-visual-gallery presentation, extended financial overview beyond wallet/invoices, and orders + history remain open — Phase 2 as a whole is still NOT complete. See `traceability/ARCHITECTURE_DECISION_LOG.md` ADM-021.
- **MERGED to main via PR #10 (merge commit `9a26024`, 2026-07-15).**

**Sprint 2.6 (2026-07-15, branch `phase2-caregiver-public-profile-finalization`, from merged main @ `9a26024`) — Public Profile Finalization and Phase 2 Acceptance:**
- Integration/quality/privacy/accessibility/performance closeout sprint — no new models, views, or routes; domain engines not redesigned.
- Confirmed clean: canonical directory/search/home visibility (BG-022, re-verified); provider-preview consistency (the owner's "public preview" link is the exact same public URL/selector, no separate render path); privacy/security boundaries (every public ViewModel structurally excludes private-contact/identity/document/wallet/order-customer fields); existing cache infra reviewed and left unused for page/read-model caching (no proven blocker); existing permission-gated internal discovery API confirmed unrelated to the public profile (no new public API).
- Fixed: SEO `page_url`/canonical-URL bug (caregiver profile page pointed at the directory URL instead of its own); empty-`alt` gap on gallery images (3 templates); unassociated form labels (4 `provider_portal` templates); a redundant, always-true generic verification badge duplicating the precise Sprint 2.3 badges; one unrelated, pre-existing, environment-clock-dependent flaky test.
- Measured and documented query counts for all 7 required pages (Section G) — public profile 15 (bounded), directory 28/43/57 at 5/10/20 candidates (grows with candidate count, KL-012, initially left unfixed), home featured 27/32/42 (same cause), provider dashboard 30/31 (bounded), provider profile-management 15 (bounded).
- New `apps.public_site.tests.test_phase2_acceptance` (5 tests): a full DRAFT-to-published caregiver lifecycle proving Phase 2's 15 governance-listed acceptance points compose correctly across apps.
- Deferred, recorded (out of caregiver-only scope): identical SEO bug on `organization_profile.html` (KL-021/BG-027); the same unassociated-label pattern in other portals' templates.
- 5 new tests, zero new migration, full regression 2082/2082 green.

**PR #11 review remediation (2026-07-15, same branch) — resolve the KL-012 query-performance blocker:**
- Root defect: three independent per-candidate query sources, not one — `DiscoveryRankingService._score()` called `CapacityService.is_capacity_exceeded()` once per candidate inside `rank()`; `SupplierSearchService.filter_suppliers()`'s city filter called `resolve_supplier_entity()` (singular) once per candidate; `CaregiverDirectoryService._build_card()` called `rating_summary()`/`completed_jobs_count()` once per built card.
- Fix: `CapacityService.bulk_is_capacity_exceeded()` (new), the pre-existing `resolve_supplier_entities_bulk()` (already built for exactly this class of problem during Epic 06's M1 remediation), and two new bulk methods (`ReputationService.get_reputation_summaries_bulk()`, `common.completed_jobs_counts_bulk()`) — each a small, fixed number of queries regardless of candidate count. Ranking formula, sort order, filter semantics, and public-visibility policy unchanged.
- Directory/search/home query counts now fully flat (16/17/17) from 1 through 100+ matching candidates. 12 new tests, zero new migration, full regression 2094/2094 green. **KL-012 is RESOLVED.** See `traceability/ARCHITECTURE_DECISION_LOG.md` ADM-022's remediation note and `project docs/PHASE_2_COMPLETION_REPORT.md`. **Phase 2 acceptance criteria satisfied**, except the accepted bonus/penalty dependency (KL-020, unchanged).

### PHASE 3 — Company Portal (inherits caregiver capability; Sprint 3.1 + 3.2 complete, financial-overview/invoicing/gallery-parity slices remain)

**Scope:** Company staff management (exists), caregiver management (exists), **invitation system** (company-initiated invite + join-by-code — COMPLETE, Sprint 3.1), approval (exists, extended), removal (COMPLETE, Sprint 3.1 — `terminate_membership()`/`leave_organization()`), assignment management (exists), company professional profile and public presence (COMPLETE, Sprint 3.2), company financial overview + reports (extend — remains open), company public profile gallery/certificates parity with the caregiver profile (remains open).

- **Depends on:** Phases 1–2 (verification + profile media foundations).
- **Complexity:** HIGH. New invitation model/flows, membership removal with supplier-bridge consistency (`accounts/services/supplier_bridge.py`), profile parity work.
- **Blocking items:** decision on invitation delivery channel while SMS is fake (in-app code acceptable — Sprint 3.1 confirmed this is sufficient: the caregiver sees the pending invitation directly on their own portal page, no SMS delivery needed for acceptance).
- **Acceptance criteria:** company can invite by phone/code (COMPLETE); caregiver can join by code post-registration (COMPLETE); approve/reject/accept/decline/terminate/leave lifecycle fully tested incl. concurrency (COMPLETE, Sprint 3.1); company professional profile with canonical public-visibility policy, permission-gated management, and headline/logo/services (COMPLETE, Sprint 3.2); company financial overview and reports production-complete (still open).

**Sprint 3.1 (2026-07-16, branch `phase3-company-portal-foundation`, from merged main @ `90e608d`) — Company Foundation and Caregiver Management, including the PR #12 architecture-review remediation that preserves affiliation-period history:**
- Current-state inspection found `OrganizationMembership`/`CompanyAffiliationRequest` already modeled but no path ever produced a PENDING membership, no invitation concept existed, and zero UI/permission enforcement covered either model.
- Extended `apps.accounts.services.affiliations` with the full lifecycle: join-by-code (new tenant-scoped, exact-code, ACTIVE-organization-only resolver), company-initiated invitation (`invite_caregiver()`/`accept_invitation()`/`decline_invitation()`/`cancel_invitation()`), mutual termination (`terminate_membership()` company-side permission-gated, `leave_organization()` caregiver-side ownership-authorized), and read helpers for both portals.
- Canonical model: `OrganizationMembership` is the single historical relationship record — every affiliation cycle creates a new, independent row (never reactivates a prior terminal one); two conditional `UniqueConstraint`s (`uniq_active_caregiver_membership_per_user`, `uniq_open_membership_per_org_user_role`) enforce the live-state invariants while terminal rows accumulate as immutable history; `closure_reason` distinguishes terminal outcomes. `CompanyAffiliationRequest` remains the caregiver-initiated intake, with a matching conditional pending-request constraint. See `ARCHITECTURE_DECISION_LOG.md` ADM-023 and its remediation note.
- 4 new permission keys (`ORGANIZATION_MEMBERSHIP_INVITE`/`_REJECT`/`_TERMINATE`, reusing existing `_APPROVE`), granted to `organization_admin` via the existing `OrganizationRoleSyncService` sync.
- New UI: `organization_portal` staff page extended (pending requests/invitations, invite-by-phone, terminate); `provider_portal` new "company" page (join by code, respond to invitations, leave, history).
- Concurrency: every activation path locks the caregiver's own `CaregiverProfile` row first, closing a genuine cross-organization race — proven by 3 new `TransactionTestCase` tests.
- Two migrations (`accounts/0008_...`, `accounts/0009_...`). 56 new/rewritten tests. Full regression 2150/2150 green at merge. **BG-028 is RESOLVED. MERGED to main via PR #12** (merge commit `ffb82a4767ba115dc158cb845b92211ccbc30d00`, 2026-07-16). **Sprint 3.1 is CLOSED.**

**Sprint 3.2 (2026-07-16, branch `phase3-company-professional-profile`, from merged main @ `ffb82a4`) — Company Professional Profile and Public Presence:**
- Current-state inspection found most target capabilities already built by Epic 06 Sprint 2 and Sprint 3.1 (`OrganizationProfile`'s public/contact fields, `OrganizationProfileUpdateService`, logo/cover upload, the public organization-profile page) — no parallel model introduced; closed the genuinely missing/broken pieces instead.
- New field: `OrganizationProfile.headline` (professional headline/short intro, mirroring `CaregiverProfile.specialty`), wired through the update service, both portal and public ViewModels, the edit form, and both templates.
- Fixed a real canonical-visibility-policy bug: the public organization-profile service checked only `profile_status`, not `common.is_publicly_visible_attrs()` (the same function the caregiver page already used) — an unverified organization or one with a deactivated admin account was incorrectly publicly visible. Fixed to call the same canonical function.
- Fixed the organization public-profile page's SEO canonical-URL bug (KL-021/BG-027, previously deferred as caregiver-only scope).
- Permission-gated the four organization logo/cover set/remove methods on `ProfileMediaService` (previously no permission check at all, only ownership) — reuses the existing `ORGANIZATION_PROFILE_UPDATE` key, mirroring Sprint 3.1's own permission-hardening precedent.
- Made `ProfileMediaService._replace()` transaction-safe (old file deleted via `transaction.on_commit()`, mirroring Sprint 2.2's gallery remediation) — shared by caregiver and organization media.
- One migration (`accounts/0010_organizationprofile_headline.py`). 10 new/rewritten tests. Full regression 2160/2160 green. See `ARCHITECTURE_DECISION_LOG.md` ADM-024. PR #13 created.

**PR #13 architecture-review remediation (2026-07-16, same branch) — render the public company logo:**
- Root defect: the sprint's own initials-only public logo/avatar decision left the organization's already-uploaded, already permission-gated, already file-safety-hardened logo disconnected from the public professional profile the sprint exists to build.
- Fix: exposed `logo_url` on the public `OrganizationProfileViewModel` (from the existing `OrganizationProfile.logo` field's own `.url`, never a filesystem path), passed as `src=` to the existing `avatar.html` include — its pre-existing initials fallback now serves its real purpose (no logo uploaded) instead of a blanket "never show the real logo." Canonical visibility policy (unchanged) still gates the logo along with the rest of the profile.
- No model, migration, permission, upload-flow, company-directory, contact-settings, gallery, certificates, financial, or Marketplace change. 5 new tests proving exposure/fallback/visibility-gating/no-metadata-leakage/query-count parity. No full regression rerun (ViewModel/service/template projection only). See `ARCHITECTURE_DECISION_LOG.md` ADM-024's remediation note. **PR #13 not merged — awaiting review.**

### PHASE 4 — Customer Portal (production complete)

**Scope:** Dashboard (exists), orders (exists), payments (exists per-order), invoices + receipts pages (new, read from `FinancialDocumentService.list_for_payer_party`), notifications (exists), **favorites** (new model + toggle on public profiles + portal list), profile (exists), history.

- **Depends on:** Phase 2 (favorites target public caregiver profiles); invoice pages need only existing finance services.
- **Complexity:** MEDIUM. Mostly additive views over existing services + one small Favorite model.
- **Blocking items:** none.
- **Acceptance criteria:** invoice/receipt list and detail render issued documents with correct totals; favorites add/remove/list with tenant scoping; order history complete; regression green.

### PHASE 5 — Marketplace Order Workflow

**Scope:** Job publication (PUBLIC order visibility exists in `Order.PUBLIC`), offer submission marketplace, OrderOfferService (submit/edit/withdraw/select per ADM-001..013), reservation hold via SELECTED status + PaymentDeadline reuse (ADM-011), payment timeout + retry, escrow hold, assignment-after-payment (ADM-002/Option B), execution, completion, cancellation, disputes (exists).

- **Depends on:** Phase 4 (customer surfaces), Phase 2 (provider surfaces); binding decisions in `project docs/current/ACTIVE_ARCHITECTURE_DECISIONS.md`.
- **Complexity:** VERY HIGH. Concurrency-sensitive (one-selected-per-order constraint already in DB), payment/escrow coupling, gate enablement (G10) for deadline expiry.
- **Blocking items:** deadline-expiry gate verification (BG-007); pre-service payment gate (BG-008); fake-PSP-only limits end-to-end realism until Phase 8 outcome.
- **Acceptance criteria:** full offer lifecycle service with concurrency tests; selection creates hold + deadline; payment success → ACCEPTED + SupplierAssignment; timeout → EXPIRED + order back to marketplace; retry payment path; cancellation and dispute paths preserve escrow conservation equation; existing operator-assignment flow untouched (ADM-008).

### PHASE 6 — Invoice Workflow

**Scope:** Invoice generation (exists: execution, supplemental, pre-service), verification, approval, adjustments (settlement_adjustments exists — wire to UI), reports, exports (CSV/PDF).

- **Depends on:** Phase 5 (marketplace generates the volume), Phase 4 (customer invoice surfaces).
- **Complexity:** MEDIUM.
- **Blocking items:** none beyond Phase 5.
- **Acceptance criteria:** issue→verify→approve state machine documented and enforced in one service; adjustment audit trail; export formats tested; portal + admin surfaces complete.

### PHASE 7 — Financial Engine Architectural Review (REVIEW ONLY)

**Scope:** No implementation. Assess `finance`, `commission`, `pricing`, `wallet`: what is complete, what needs refactoring (legacy `finance.WalletAccount`/legacy escrow methods per `quality/LEGACY_AND_DEAD_CODE.md`), what needs extension (payout/accounting), what stays unchanged (escrow conservation core, commission snapshots).

- **Depends on:** Phases 5–6 outcomes (real usage patterns).
- **Complexity:** MEDIUM (analysis effort).
- **Acceptance criteria:** written recommendations document with per-module verdicts and evidence; no code changes.

### PHASE 8 — Payment & Settlement Review (REVIEW ONLY)

**Scope:** No implementation. Review gateway abstraction (real PSP readiness, callback signature verification — FR-004), escrow, wallet, settlement, commission, refund, payout, accounting/ledger. Determine remaining work; recommendations only.

- **Depends on:** Phase 7.
- **Complexity:** MEDIUM (analysis effort).
- **Acceptance criteria:** recommendations document covering PSP selection criteria, webhook security, payout design, and gate-enablement plan (G10).

---

## 4. CROSS-CUTTING BLOCKING ITEMS (tracked, scheduled inside phases or as hygiene)

| Item | When |
|------|------|
| Seed test race (G12 / BG-002) | DONE — merged in PR #1 (`eb51018`) |
| Tenant isolation hardening (FR-001), RBAC toggle audit (FR-002) | Recommendations in Phases 7–8; guardrail tests may be added any time |
| Real PSP (G8), real notifications (G9) | After Phase 8 recommendations |
| CI activation (G14) | Any time; recommended alongside P0 hygiene |

---

## 5. GOVERNANCE

- Every phase ends with: targeted tests + full regression, documentation sync of `project docs/current/` + traceability entries, and a stop for review.
- This file is the single active implementation order. `03_NEXT_TASK.md` points here (synchronized 2026-07-14).
