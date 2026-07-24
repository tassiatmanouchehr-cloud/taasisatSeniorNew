# IMPLEMENTATION ROADMAP

## Purpose

This document defines the platform delivery phases, their dependencies, acceptance criteria, and sequence. It is the authoritative source for:

- What each phase delivers
- What must be true before a phase begins
- What must be true before a phase can close
- The dependency ordering between phases

**Frequently changing completion status** (which phases are done, test baselines, current HEAD) belongs in `04_IMPLEMENTATION_STATUS.md`, not here.

**Permanent testing policies** (required checks, test types, CI jobs) belong in `08_TESTING_AND_QUALITY.md`, not here.

---

## Phase Sequence

| # | Phase | Status | Dependency |
|---|---|---|---|
| 1 | Registration & Verification Workflows | **COMPLETE** | None |
| 2 | Caregiver Professional Profile | **COMPLETE** | Phase 1 |
| 3 | Company Portal | **COMPLETE** | Phases 1–2 |
| 4 | Customer Portal | **COMPLETE** | Phases 2–3 |
| 5 | Marketplace Order Workflow | **COMPLETE** (Sprint 5.1, 5.2, 5.3A, 5.3B all merged) | Phase 4 |
| 6 | Financial Integration | **IN PROGRESS** (Phase 6.1 complete — release consumer) | Phase 5 |
| 7 | Financial Engine Review (analysis only) | PLANNED | Phases 5–6 |
| 8 | Payment & Settlement Review (analysis only) | PLANNED | Phase 7 |

---

## Phase 1 — Registration & Verification Workflows

**Objective:** Complete customer/caregiver/company registration, profile activation, identity and professional-license verification by platform staff.

**Scope:**
- Phone/OTP registration (3 paths)
- Document upload and admin review workflow
- Profile verification rollup
- Required-document tenant-configurable policy
- Profile activation lifecycle (DRAFT → ACTIVE)
- Activation eligibility checks
- AI verification extension point (interface only)

**Acceptance Criteria:**
1. All three registration flows produce correct profiles, roles, and affiliation requests
2. Platform admin can list pending documents, view file, approve/reject with reason
3. Profile `verification_status` transitions derived by one service, tested for every path
4. Verification strategy interface exists with manual implementation only
5. Profile completion percent deterministic, computed by one service
6. Activation is authorized, audited, and transitions profile status

**Status:** COMPLETE (PR #5, merge commit `0c9d70c`)

---

## Phase 2 — Caregiver Professional Profile

**Objective:** Full caregiver public professional profile — gallery, skills, experience, credentials, availability, dashboard, and public marketplace presence.

**Scope:**
- Skills and experience management
- Professional gallery (portfolio images)
- Verification credential public presentation
- Availability schedule (weekly windows, time-off)
- Professional dashboard (work summary, financials, reviews)
- Public profile finalization (SEO, accessibility, query performance)
- Directory/search query-performance resolution (KL-012)

**Acceptance Criteria:**
- Caregiver can manage gallery/skills/experience from provider portal
- Public profile renders all professional sections
- Unverified/rejected documents never leak publicly
- Query behavior bounded regardless of candidate count
- Full Phase 2 acceptance lifecycle test passes

**Status:** COMPLETE (PR #11, merge commit `90e608d`)

---

## Phase 3 — Company Portal

**Objective:** Company-caregiver affiliation lifecycle, company professional profile, and public company directory.

**Scope:**
- Company-caregiver affiliation (join-by-code, invitation, accept/decline, termination)
- Immutable affiliation history (one row per period)
- Company professional profile (headline, logo, services)
- Canonical public visibility policy applied to organizations
- Public organization directory with search/filter/pagination
- Permission-gated media management

**Acceptance Criteria:**
- Company can invite, caregiver can join by code
- Approve/reject/accept/decline/terminate/leave lifecycle tested including concurrency
- Company professional profile with canonical visibility, permission-gated management
- Public directory with search, city/service filters
- One active company per caregiver (concurrent activation race closed)

**Status:** COMPLETE (PRs #12–#15)

---

## Phase 4 — Customer Portal

**Objective:** Complete customer-facing portal including the one confirmed gap (favorites).

**Scope:**
- Customer favorites (save/unsave suppliers, portal list page)
- Verification that all pre-existing Epic 07 capabilities are production-complete

**Acceptance Criteria:**
- Favorites add/remove/list with tenant scoping and ownership
- Full regression passes
- All pre-existing capabilities verified functional

**Status:** COMPLETE (PR #16, merge commit `544de34`; formal closure PR #17)

---

## Phase 5 — Marketplace Order Workflow

**Objective:** Implement the `OrderOfferService` — the complete offer marketplace lifecycle from submission through acceptance and assignment.

**Scope:**
- Sprint 5.1: submit_offer, edit_offer, withdraw_offer (MERGED — PR #41)
- Sprint 5.2 (PLANNED): select_offer, accept_offer, expire_held_offers, cancel_offers_for_order
- Selection creates 30-minute hold via SELECTED status
- Payment timeout → EXPIRED → order returns to marketplace
- Assignment triggered on acceptance
- Cancellation/dispute paths preserve escrow conservation

**Sprint 5.1 Acceptance Criteria:**
1. `OrderOfferService.submit_offer()` enforces `orders.offer.submit` permission
2. Offers submittable only when `order.status == NEW`
3. One offer per (order, supplier) — database-enforced
4. Edit and withdraw are owner-only, status-gated
5. All mutations atomic with row locking and audit
6. Full regression passes

**Sprint 5.1 Status:** COMPLETE (PR #41 merged, 29 service tests + 28 guardrails, 2546/2546 PASS)

**Sprint 5.2 Acceptance Criteria (planned):**
1. Selection creates SELECTED status + 30-minute hold
2. Payment success → ACCEPTED + triggers assignment
3. Hold timeout → EXPIRED
4. Cancel propagates to active offers
5. Concurrency tests for one-selected-per-order constraint

**Sprint 5.2 Status:** COMPLETE (PR #44, 32 selection tests + 29 service tests, 2578/2578 PASS, real PostgreSQL concurrency validation)

**Sprint 5.2 Delivered:**
1. `OrderOfferService.select_offer()` — SUBMITTED → SELECTED with 30-minute hold
2. `OrderOfferService.expire_held_offers()` — SELECTED → EXPIRED for timed-out holds
3. Bulk-rejection of competing SUBMITTED offers on selection
4. Customer-profile ownership authorization (dual-path: person_id + created_by fallback)
5. Real concurrency test (`TransactionTestCase` + `threading.Barrier`) on PostgreSQL
6. 32 new tests in `test_order_offer_selection.py`; no migration created
7. All 5 CI checks green

**Sprint 5.2 Known Limitations:**
1. Hold duration hardcoded at 30 minutes (not tenant-configurable)
2. Rejected competing offers are NOT restored on hold expiry (by design)
3. Customer cannot cancel/revert a selection (unresolved business decision)
4. No scheduler infrastructure wired — `expire_held_offers()` is independently callable
5. Pre-existing `kernel` app migration drift remains (RISK-009, unrelated)

**Sprint 5.3A — Cancellation Authorization Enforcement:**

**Sprint 5.3A Acceptance Criteria:**
1. `request_cancellation()` enforces `orders.cancellation.request` permission (strict RBAC)
2. `approve_cancellation()` enforces `orders.cancellation.approve` permission (strict RBAC)
3. Actor without required permission receives `PermissionDenied` (hard deny)
4. Actor=None (system context) is audited and allowed (trusted internal orchestration)
5. Tenant scope derived from the locked order (authoritative)
6. Denied operations produce no state mutation or side effects
7. Cross-tenant actors denied regardless of permission in their own tenant
8. Seed walkthrough aligned with strict authorization (system-context path)

**Sprint 5.3A Status:** COMPLETE (PR #45, 14 cancellation authorization tests, 2,543/2,543 PASS, all 5 CI checks green)

**Sprint 5.3A Delivered:**
1. `PermissionService.require()` enforcement in `request_cancellation()` — strict RBAC, no fallback
2. `PermissionService.require()` enforcement in `approve_cancellation()` — strict RBAC, no fallback
3. Permission keys `orders.cancellation.request` and `orders.cancellation.approve` registered
4. Authoritative tenant scope derived from the locked order (not caller-supplied)
5. Deliberate trusted system-context (`actor=None`) audited and allowed for internal orchestration
6. 14 new authorization tests (7 per function) covering positive, negative, cross-tenant, state-machine, and registry verification
7. Seed walkthrough command aligned (system-context for internal state transitions)
8. No migration created, no schema change

**Sprint 5.3A Authorization Model:**
- Actor with permission → operation succeeds (normal RBAC path)
- Actor without permission → `PermissionDenied` (hard denial, no state mutation)
- `actor=None` (system context) → audited via `AuditService.log_security()`, allowed
- Public callers MUST supply a real authenticated actor — `actor=None` is a trusted system-context mechanism for background jobs, cascading operations, and internal infrastructure only

**Dependencies:** Phases 1–4 complete (all satisfied)

---

## Phase 6 — Invoice Workflow

**Objective:** Invoice generation, verification, approval, adjustments, reports, and exports.

**Scope:**
- Invoice lifecycle: issue → verify → approve
- Adjustment audit trail
- Export formats (CSV/PDF)
- Portal and admin surfaces complete

**Dependencies:** Phase 5 (marketplace generates invoice volume)

**Status:** NOT STARTED

---

## Phase 7 — Financial Engine Architectural Review

**Objective:** Analysis only — no implementation. Assess the financial subsystem.

**Scope:**
- Review `finance`, `commission`, `pricing`, `wallet` apps
- Determine what is complete vs. needs refactoring vs. needs extension
- Address legacy `finance.WalletAccount`/legacy escrow methods
- Determine payout/accounting requirements

**Deliverable:** Written recommendations document with per-module verdicts

**Dependencies:** Phases 5–6 outcomes (real usage patterns needed)

**Status:** NOT STARTED

---

## Phase 8 — Payment & Settlement Review

**Objective:** Analysis only — no implementation. Review payment gateway readiness.

**Scope:**
- Gateway abstraction (real PSP readiness, webhook security)
- Escrow/wallet/settlement/commission/refund/payout/accounting review
- Gate-enablement plan for `deadline_activation_enabled` / `preservice_payment_enabled`

**Deliverable:** Written recommendations covering PSP selection, webhook security, payout design

**Dependencies:** Phase 7

**Status:** NOT STARTED

---

## Rules for Phase Completion

A phase is COMPLETE only when:

1. All acceptance criteria above are met (verified from code + tests)
2. Full regression passes
3. `manage.py check` reports 0 issues
4. `git diff --check` is clean
5. Documentation synchronized per governance §18
6. Completion recorded in `04_IMPLEMENTATION_STATUS.md`

A phase CANNOT be marked complete based on:
- Documentation claims alone
- Partially passing test suites
- Future intent to fix known failures

---

## Cross-Cutting Remediations (not numbered phases)

| Remediation | Status | PRs |
|---|---|---|
| Seed order-number collision (BG-002) | COMPLETE | PR #1 |
| RBAC enforcement-toggle visibility | COMPLETE | PR #24 |
| Core Profile-ServiceSupplier invariant | COMPLETE | PR #18 |
| Public site tenant resolution (FR-015–FR-019) | COMPLETE | PRs #19–#23 |
| Accessibility remediation | COMPLETE | PR #34 |
| Order cancellation permission gap | **COMPLETE** | PR #45 (Sprint 5.3A) |
