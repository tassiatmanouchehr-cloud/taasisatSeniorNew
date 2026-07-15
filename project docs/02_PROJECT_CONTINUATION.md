# PROJECT CONTINUATION

---

## PROJECT ID

| Field | Value |
|-------|-------|
| Repository name | taasisatSeniorNew |
| URL | https://github.com/tassiatmanouchehr-cloud/taasisatSeniorNew |
| Default branch | main |
| main HEAD SHA | f7b7b2be5abd42d85935f522cf1b7b9b27bb6da1 (merge of PR #7) |
| Feature branch HEAD | `phase2-caregiver-credentials-skills-experience-ui` (from main @ f7b7b2b) — PR to be created, not yet merged |
| Last verified date | July 15, 2026 |
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
| Current phase | **Phase 2 — Caregiver Professional Profile is ACTIVE**; this session implements **Sprint 2.2 — Caregiver Gallery and Media Portfolio** (see `IMPLEMENTATION_ROADMAP.md`) |
| Sprint 2.2 (+ file-lifecycle/image-safety remediation) | **MERGED to main** via PR #7 (merge commit `f7b7b2b`); caregiver gallery/media portfolio (`CaregiverGalleryItem`, `CaregiverGalleryService`) — owner-authorized upload/caption/reorder/visibility-toggle/remove, provider-portal management page, public-profile gallery section reusing the canonical BG-022 visibility policy. Remediation hardened `remove_item()` to a transaction-safe, post-commit deletion order and added decoded-image dimension/pixel-count limits + decompression-bomb handling to the shared `image_validation.validate_image()`. 61 tests (45 Sprint 2.2 + 16 remediation), 1 migration, full regression 1948/1948 green at merge. |
| Sprint 2.3 | Professional credibility layer IMPLEMENTED on `phase2-caregiver-credentials-skills-experience-ui` (branched from merged main @ f7b7b2b): precise verification badges (replacing one generic "Verified" pill), owner-facing skill/experience visibility toggles (`is_visible` columns existed since Phase 2.1, unused until now), derived highlights (public + provider-portal preview, zero/near-zero new queries), an owner-facing "expiring soon" credential state, and an explicit self-declared-vs-verified distinction on the public profile. 36 new tests, zero new migration. Skill catalog/normalization, certificates-as-visual-gallery, availability, and financial overview/orders remain separate, future sprints/backlog items. |
| Active blocker | `makemigrations --check` cosmetic drift only (pre-existing, exit 1, accounts/kernel field alters — no schema change intended) |
| Active work branch | `phase2-caregiver-credentials-skills-experience-ui` (from main @ f7b7b2b) |

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
