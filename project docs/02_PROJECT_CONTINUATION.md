# PROJECT CONTINUATION

---

## PROJECT ID

| Field | Value |
|-------|-------|
| Repository name | taasisatSeniorNew |
| URL | https://github.com/tassiatmanouchehr-cloud/taasisatSeniorNew |
| Default branch | main |
| main HEAD SHA | 49b643e130018b959938907e9a5d1ae491d51f6c (merge of PR #13) |
| Feature branch HEAD | none — `phase3-company-professional-profile` merged to `main` via PR #13; no active feature branch |
| Last verified date | July 16, 2026 |
| Python version | 3.12 (owner dev); 3.11.15 (cloud verification environment) |
| Django version | 5.2.16 |
| PostgreSQL | 16 |

---

## CURRENT STATE

| Field | Value |
|-------|-------|
| Working tree | Clean at verification time |
| Offer Marketplace Phase 1 | **COMMITTED** in `ce3b30e`, now on main (OrderOffer model, migration `orders/0008_orderoffer.py`, admin, 40 tests) |
| BG-002 | **MERGED to main** via PR #1 (merge commit `eb51018`); full regression 1680/1680 green at merge |
| Phase 1 | **COMPLETE and MERGED to main** via PR #5 (merge commit `0c9d70c`); all acceptance criteria met; full regression 1824/1824 green at merge (includes Phase 1.1 PR #3 `278098b`, Phase 1.2 PR #4 `860640e`, Phase 1.3 + remediation PR #5 `0c9d70c`) |
| Phase 2.1 (+ BG-022 remediation) | **MERGED to main** via PR #6 (merge commit `c5259b3`); skills (`CaregiverSkill`), experience (`CaregiverExperience`), verified-credential public summary (`PublicCredentialSelector`), and the canonical public-visibility policy (`common.is_publicly_visible_attrs()`, applied uniformly by directory/home-page/detail page) all now on `main`. 63 tests (50 Phase 2.1 + 13 BG-022 remediation), 1 migration, full regression 1887/1887 green at merge. |
| Current phase | **Phase 2 — CLOSED and MERGED to main** (PR #11, merge commit `90e608d`). **Phase 3 — Company Portal is ACTIVE**; **Sprint 3.1 — Company Foundation and Caregiver Management is CLOSED and MERGED to main** (PR #12, merge commit `ffb82a4`); **Sprint 3.2 — Company Professional Profile and Public Presence is CLOSED and MERGED to main** (PR #13, merge commit `49b643e`) — see `IMPLEMENTATION_ROADMAP.md`. No Sprint 3.3 work has started. |
| Sprint 2.2 (+ file-lifecycle/image-safety remediation) | **MERGED to main** via PR #7 (merge commit `f7b7b2b`); caregiver gallery/media portfolio (`CaregiverGalleryItem`, `CaregiverGalleryService`) — owner-authorized upload/caption/reorder/visibility-toggle/remove, provider-portal management page, public-profile gallery section reusing the canonical BG-022 visibility policy. Remediation hardened `remove_item()` to a transaction-safe, post-commit deletion order and added decoded-image dimension/pixel-count limits + decompression-bomb handling to the shared `image_validation.validate_image()`. 61 tests (45 Sprint 2.2 + 16 remediation), 1 migration, full regression 1948/1948 green at merge. |
| Sprint 2.3 | **MERGED to main** via PR #8 (merge commit `20c532e`); professional credibility layer — precise verification badges (replacing one generic "Verified" pill), owner-facing skill/experience visibility toggles (`is_visible` columns existed since Phase 2.1, unused until now), derived highlights (public + provider-portal preview, zero/near-zero new queries), an owner-facing "expiring soon" credential state, and an explicit self-declared-vs-verified distinction on the public profile. 36 tests, zero new migration, full regression 1984/1984 green at merge. |
| Sprint 2.4 | **MERGED to main** via PR #9 (merge commit `125dd3b`, includes the concurrency remediation): weekly working-hour intervals with overlap/duplicate refusal (now concurrency-proven via supplier-row locking), provider-portal edit/enable-disable UI, one canonical structured availability evaluator (`AvailabilityQueryService.evaluate()`), and a privacy-safe public availability summary. 49 tests (40 Sprint 2.4 + 9 concurrency remediation), zero new migration, full regression 2033/2033 green at merge. |
| Sprint 2.5 | **MERGED to main** via PR #10 (merge commit `9a26024`); caregiver professional dashboard: work summary (current/upcoming/completed/cancelled, `Order.status`-derived), financial overview (existing wallet), wallet movements, invoice summary (new beneficiary-side `FinancialDocument` selector), reviews/reputation, and professional statistics — all read-only, all sourced from canonical selectors. 44 tests, zero new migration, full regression 2077/2077 green at merge. Bonus/penalty confirmed to have no canonical representation anywhere in this repository — documented as a gap, not invented. |
| Sprint 2.6 | Public Profile Finalization and Phase 2 Acceptance IMPLEMENTED on `phase2-caregiver-public-profile-finalization` (branched from merged main @ 9a26024): integration matrix confirmation, SEO `page_url`/canonical-URL fix, accessibility fixes (gallery alt-text fallback, label associations), removed a redundant/always-true verification badge, privacy/security acceptance pass, query/performance measurement across 7 pages, cache/public-API/provider-preview review (all confirmed sufficient as-is, no new infra added), 5 new Phase 2 end-to-end acceptance tests, and one unrelated pre-existing flaky-test fix. Zero new migration, full regression 2082/2082 green. **PR #11 review remediation:** the directory/home query-count growth initially measured and left unfixed (KL-012) was found inconsistent with the "bounded"/"no blocker" acceptance criteria it was reported under — resolved by batching 3 per-candidate query sources (`DiscoveryRankingService` capacity check, `SupplierSearchService` city filter, `CaregiverDirectoryService` card building) at their canonical selector boundaries, with zero change to ranking/filter/visibility semantics. Directory/search/home query counts are now fully flat (16/17/17) regardless of candidate count. 12 new tests, zero new migration, full regression 2094/2094 green. **Phase 2 acceptance criteria satisfied** except the accepted bonus/penalty dependency (KL-020). See `project docs/PHASE_2_COMPLETION_REPORT.md`. |
| PR #11 | **MERGED to main** (merge commit `90e608dc5d14ff4f367abafc022f756819734f6d`, 2026-07-16); Sprint 2.6 + PR #11 KL-012 remediation both included. Full regression 2094/2094 green at merge. **Phase 2 (Caregiver Professional Profile) is now CLOSED.** |
| Sprint 3.1 | Company Foundation and Caregiver Management, plus the PR #12 architecture-review remediation: extends the pre-existing `OrganizationMembership`/`CompanyAffiliationRequest` models (no new models) with a full affiliation lifecycle — join-by-code, company invitation, approval/rejection, mutual termination, per-cycle history (each affiliation period is a separate, immutable `OrganizationMembership` row; terminal rows are never reactivated; two conditional `UniqueConstraint`s enforce live-state invariants; `closure_reason` distinguishes terminal outcomes; `CompanyAffiliationRequest` has a matching conditional pending-request constraint) — across `apps.accounts.services.affiliations`, new organization_portal and provider_portal UI, and 4 new permission keys. Two migrations (`accounts/0008_...`, `accounts/0009_...`). 56 new/rewritten tests, full regression 2150/2150 green at merge. **MERGED to main via PR #12** (merge commit `ffb82a4767ba115dc158cb845b92211ccbc30d00`, 2026-07-16). See `traceability/ARCHITECTURE_DECISION_LOG.md` ADM-023 and its remediation note. |
| Sprint 3.2 | Company Professional Profile and Public Presence, plus the PR #13 architecture-review remediation: current-state inspection found most target capabilities already built (`OrganizationProfile` public/contact fields, `OrganizationProfileUpdateService`, logo/cover upload, the public organization-profile page) — closed the genuinely missing/broken pieces instead of rebuilding: added `OrganizationProfile.headline` (professional headline/short intro, one migration); fixed `OrganizationPublicProfileService.get_profile()` to use the canonical `common.is_publicly_visible_attrs()` (it previously only checked `profile_status`, so an unverified organization or one with a deactivated admin account was incorrectly publicly visible); fixed the organization public-profile page's SEO canonical URL (KL-021/BG-027, previously deferred); permission-gated the organization logo/cover upload/remove methods (`ORGANIZATION_PROFILE_UPDATE`, reused); made `ProfileMediaService._replace()` transaction-safe; renders the organization's real uploaded logo publicly (`logo_url`, initials fallback only when no logo/no usable URL — the sprint's original initials-only decision was superseded, not a redesign), still gated by the canonical visibility policy. One migration (`accounts/0010_organizationprofile_headline.py`). 17 new/rewritten tests total, full regression 2160/2160 green at merge. **MERGED to main via PR #13** (merge commit `49b643e130018b959938907e9a5d1ae491d51f6c`, 2026-07-16). See `traceability/ARCHITECTURE_DECISION_LOG.md` ADM-024 and its remediation note. |
| Active blocker | `makemigrations --check` cosmetic drift only (pre-existing, exit 1, accounts/kernel field alters — no schema change intended) |
| Active work branch | none — `main` is the current branch; Sprint 3.3 has not started |

---

## ACTIVE DOCUMENTATION

All active documentation is under: **`project docs/`**

Start with: **`project docs/00_START_HERE.md`**

The active implementation order is: **`project docs/IMPLEMENTATION_ROADMAP.md`**

`canonical docs/` and `mimo change/` are NOT active paths — their content was
reorganized into `project docs/` and the originals archived under `_archive/`.

---

## HOW TO CONTINUE

1. Read `project docs/00_START_HERE.md` for documentation structure
2. Read this file for current state
3. Read `project docs/03_NEXT_TASK.md` for the immediate next objective
4. Read `project docs/IMPLEMENTATION_ROADMAP.md` for the phase order
5. Always inspect the repository — never trust memory or previous reports
6. Continue only from the current repository state
7. Never skip documentation — update `project docs/traceability/` for every change
8. Never skip testing — run targeted tests and full regression
9. Never expand scope — complete only what is approved
10. Wait for review before continuing to next phase
