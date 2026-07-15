# PROJECT CONTINUATION

---

## PROJECT ID

| Field | Value |
|-------|-------|
| Repository name | taasisatSeniorNew |
| URL | https://github.com/tassiatmanouchehr-cloud/taasisatSeniorNew |
| Default branch | main |
| main HEAD SHA | 278098b9f838dc44a40d7f646cbc9c1027a379c0 (merge of PR #3) |
| Feature branch HEAD | `phase1-verification-activation-rules` (from main @ 278098b) — PR not yet merged |
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
| Current phase | **Phase 1 — Registration and Verification Workflows is ACTIVE** (see `IMPLEMENTATION_ROADMAP.md`) |
| Phase 1.1 | Manual document verification (caregiver + organization) **MERGED to main** via PR #3 (merge commit `278098b`); full regression 1721/1721 green at merge |
| Phase 1.2 | Verification completion and activation rules (required-document policy, profile roll-up, resubmission lifecycle, activation eligibility) IMPLEMENTED on `phase1-verification-activation-rules`; 47 new tests, no migration; PR pending, not yet merged |
| Active blocker | `makemigrations --check` cosmetic drift only (pre-existing, exit 1, accounts/kernel field alters — no schema change intended) |
| Active work branch | `phase1-verification-activation-rules` (from main @ 278098b) |

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
