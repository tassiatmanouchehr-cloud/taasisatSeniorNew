# IMPLEMENTATION ROADMAP

**Created:** 2026-07-14
**Verified against HEAD:** ce3b30e0f3c06d7b058587f3e75c357bfe588415 ("Repository documentation reorganization")
**Post-merge update:** 2026-07-14 — PR #1 merged to main (`eb51018`): documentation sync + BG-002 fix are on main; P0 hygiene complete; **Phase 1 is the active phase**
**Phase 1.1 update:** 2026-07-15 — manual document verification workflow merged to main via PR #3 (merge commit `278098b`); full regression 1721/1721 green at merge
**Phase 1.2 update:** 2026-07-15 — verification completion and activation rules implemented on branch `phase1-verification-activation-rules` (from main @ `278098b`); no migration; PR not yet merged
**Phase 1.3 update:** 2026-07-15 — deterministic profile completion + controlled activation implemented on branch `phase1-activation-completion-final` (from main @ `860640e`, the merged Phase 1.2 PR #4); no migration; PR not yet merged; **Phase 1 acceptance criteria now fully met**
**Branch verified:** main (via claude/taasisat-senior-state-verify-9dzzlm)
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

### PHASE 2 — Caregiver Profile (production complete)

**Scope:** Instagram-like public profile: gallery (new model + upload service + moderation flag), certificates (surface VERIFIED `VerificationDocument`s of certificate/license types), structured skills, experience, reviews (exists), availability display (exists), financial overview (extend earnings), orders + history.

- **Depends on:** Phase 1 (verified documents feed the certificates section).
- **Complexity:** MEDIUM-HIGH. New models (GalleryItem, Skill/CaregiverSkill), new provider-portal management pages, public-profile rendering, image validation reuse from `profile_media_service.py`.
- **Blocking items:** media storage strategy for production (currently local `FileField`).
- **Acceptance criteria:** caregiver can manage gallery/skills/experience from the provider portal; public profile renders gallery, certificates, skills, reviews, availability; unverified/rejected documents never leak publicly (existing rule in `media.py` docstring enforced by tests); earnings/orders/history pages complete.

### PHASE 3 — Company Portal (inherits caregiver capability)

**Scope:** Company staff management (exists partially), caregiver management, **invitation system** (company-initiated invite + join-by-code), approval (exists), removal (new), assignment management (exists), company financial overview + reports (extend), company public profile parity with caregiver profile (gallery/certificates from Phase 2 generalized to organizations).

- **Depends on:** Phases 1–2 (verification + profile media foundations).
- **Complexity:** HIGH. New invitation model/flows, membership removal with supplier-bridge consistency (`accounts/services/supplier_bridge.py`), profile parity work.
- **Blocking items:** decision on invitation delivery channel while SMS is fake (in-app code acceptable).
- **Acceptance criteria:** company can invite by phone/code; caregiver can join by code post-registration; approve/suspend/remove lifecycle fully tested incl. effect on assignments; company financial overview and reports production-complete.

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
