# PROJECT BASELINE

**This is the canonical, always-current snapshot of the project.** A new engineer
or AI should be able to answer "where are we now" from this file alone, without
reading prior conversations. When this file and any other active document
disagree, update the other document — this file is authoritative for current
state, per `01_PROJECT_RULES.md`'s source-of-truth order.

This file is a **living document** — update it in place as the project moves.
For the frozen, point-in-time evidence this baseline was built from, see
`project docs/assessments/2026-07-20_ENTERPRISE_BASELINE.md` (immutable; a later
assessment creates a new dated file rather than editing that one).

---

## 1. Repository identity

| Field | Value |
|---|---|
| Repository | `tassiatmanouchehr-cloud/taasisatSeniorNew` |
| URL | https://github.com/tassiatmanouchehr-cloud/taasisatSeniorNew |
| Default branch | `main` |
| Product | سالمندیار (Salmandyar) — Senior Care Marketplace, built on a deliberately generic Enterprise Service Marketplace Platform architecture (see `01_PROJECT_RULES.md`'s sibling, `project docs/current/SYSTEM_OVERVIEW.md`) |
| Stack | Django 5.2, PostgreSQL 16, server-rendered templates, HTMX, Alpine.js, TailwindCSS, RTL/Persian-first |

## 2. Current main SHA

| Field | Value |
|---|---|
| `main` HEAD | `7ef39ce192aa615fa2168a349112c1c45f490c0d` |
| Last merged PR | #38 — "docs: record PR #37 accessibility guardrail", merge commit `7ef39ce192aa615fa2168a349112c1c45f490c0d`, 2026-07-21 |
| Working tree at last verification | Clean |

## 3. Current project version / baseline

There is no semantic-version scheme for this platform (no `VERSION` file, no
release tags) — versioning is tied to `main`'s SHA and the assessment date, per
this repository's own established convention (compare `02_PROJECT_CONTINUATION.md`'s
"main HEAD SHA" row).

**Baseline identifier: `BASELINE-2026-07-20` (main @ `8ee1c67`)**

This is the first formally-adopted, assessment-backed baseline. Every future
baseline supersedes this one in place (this file is updated, not replaced); the
assessment it was built from is preserved immutably (see the note at the top of
this file).

## 4. Completed phases

Roadmap phases (see `IMPLEMENTATION_ROADMAP.md` for full detail):

- **Phase 1 — Registration & Verification Workflows** — CLOSED, merged via PR #5.
- **Phase 2 — Caregiver Professional Profile** — CLOSED, merged via PR #11 (Sprint 2.1–2.6).
- **Phase 3 — Company Portal** — FORMALLY CLOSED, merged via PR #12–#15 (Sprint 3.1–3.3).
- **Phase 4 — Customer Portal** — FORMALLY CLOSED, merged via PR #16–#17 (Sprint 4.1).
- **Core Profile-ServiceSupplier Invariant Remediation** — cross-cutting bug-fix, merged via PR #18.
- **FR-015 through FR-019 — Public Site Tenant Resolution and Caregiver Marketplace Remediation** — cross-cutting bug-fix/UX remediation, merged via PR #19–#23.

Within those phases, per the 2026-07-20 assessment, the following are verified
**Production Ready or Functionally Complete** end-to-end: identity/registration/
login/verification/activation/RBAC (except OTP delivery), the full Customer
Portal order-placement path, the entire Caregiver Portal and its public profile,
the Organization Portal's affiliation lifecycle and public profile/directory, the
Admin Portal's moderation/activation queues, the public marketplace (directories,
search, ranking, tenant resolution), and Order Workflow Core (lifecycle, state
machine, matching, booking, execution, reviews).

## 5. Partially completed phases

- **Order Workflow — Offer Marketplace layer.** Order Workflow *Core* (§4) is
  complete; the Offer Marketplace layer on top of it (`OrderOffer` model exists,
  no `OrderOfferService`) is not — see §6.
- **Financial Engine.** Every primitive exists and is well-tested in isolation;
  three critical wiring points do not exist in production code (commission
  allocation, escrow release, real PSP) — see §8, §19.
- **Admin/Organization operability.** Moderation is complete; observability
  (audit browsing, logs, job visibility, live configuration) is not — see §8.
- **Infrastructure operability.** CI is built but never executed; Docker exists
  for development only; no production deployment path exists — see §8, §19.

## 6. Not started phases

- **Phase 5 — Marketplace Order Workflow (Offer Marketplace / `OrderOfferService`).**
  Roadmap-ordered next feature phase. Requires its own Architecture Assessment
  before implementation, per this repository's own established governance
  pattern (Phase 3→4 and Phase 4→5 both required one). **Not the current next
  implementation target — see §15.**
- **Phase 6 — Invoice Workflow**, **Phase 7 — Financial Engine Architectural
  Review**, **Phase 8 — Payment & Settlement Review.** All explicitly depend on
  Phase 5's own implementation or usage patterns (per `IMPLEMENTATION_ROADMAP.md`);
  none can be legitimately reordered ahead of Phase 5 without new evidence.
- Admin-portal log viewer, background-job dashboard, system-configuration UI —
  no work has begun on any of these.
- Any production deployment infrastructure (CD, orchestration, reverse proxy,
  start scripts).

## 7. Current implementation matrix (summary)

77 sub-areas were assessed individually on 2026-07-20; full detail (per-sub-area
evidence, missing pieces, risk notes) is in
`project docs/assessments/2026-07-20_ENTERPRISE_BASELINE.md` §2. Domain-level
rollup:

| Domain | Production Ready | Functionally Complete | Partial | Not Started |
|---|---|---|---|---|
| Identity & Access (9) | 0 | 7 | 2 | 0 |
| Customer Portal (8) | 0 | 4 | 4 | 0 |
| Caregiver Portal & Public Profile (9) | 6 | 3 | 0 | 0 |
| Organization Portal (7) | 1 | 4 | 2 | 0 |
| Admin Portal (7) | 0 | 2 | 2 | 3 |
| Marketplace / Public Site (6) | 4 | 2 | 0 | 0 |
| Order Workflow (8) | 0 | 6 | 1 | 1 |
| Financial Engine (9) | 0 | 3 | 6 | 0 |
| Infrastructure (14) | 1 | 8 | 5 | 0 |
| **Total (77)** | **21** | **30** | **21** | **5** |

## 8. Current risks

Ranked by severity, from `project docs/assessments/2026-07-20_ENTERPRISE_BASELINE.md` §7:

| Severity | Risk | Status as of this baseline |
|---|---|---|
| **Critical** | RBAC enforcement kill-switch (`rbac.enforcement.enabled`) has no admin UI and no audit trail on its own toggle | **Resolved** — PR #24 (merge commit `88b39bc`, 2026-07-20) added a read-only admin page, audited management command, architecture guardrails, and 81 tests. Documentation had not yet been synchronized with the repository state after the RBAC remediation was merged. |
| High | OTP has no SMS provider (`_send_sms()` never defined) | Open |
| High | No real payment-service-provider adapter anywhere | Open |
| High | `ReleaseInstruction` never reaches `CONSUMED` — escrow release has no wallet-crediting consumer | Open, latent (feature gated off by default) |
| High | `AllocationCalculator` (commission split math) has zero production callers | Open, latent (feature gated off by default) |
| High | Order cancellation (`status_machine.request_cancellation/approve_cancellation`) has no `PermissionService.require()` call | Open |
| Medium | No tenant-scoping middleware — isolation is per-developer discipline, not structurally enforced | Open, currently mitigated by per-model/per-app tests |
| Medium | `SupplierSearchService.filter_suppliers()` has no DB-level `LIMIT` before ranking | Open |
| Medium | CI pipeline fully built, never executed; no production deployment infrastructure | Open |

## 9. Current technical debt

- **Dual role catalogs** — `DEFAULT_TENANT_ROLES` (12, underscored) vs.
  `DEV_BOOTSTRAP_ROLES` (14, hyphenated), deliberately unreconciled, acknowledged
  in the code's own comments.
- **Dual wallet implementations** — `apps.finance.WalletAccount` (explicitly
  LEGACY/FROZEN, zero production callers) vs. `apps.wallet.Wallet` (canonical).
  Consistently and correctly documented everywhere it's mentioned.
- **Dual settlement mechanisms** — the live Direct Settlement path vs. an
  unused `SettlementBatch`/`SettlementItem` net-position primitive that can
  never reach `APPROVED`/`PAID`. Appears to be historical accretion, not a
  deliberate parallel design (unlike the wallet duplication).
- **`DiscoveryService.search()`** self-describes as "the single public entry
  point" but is bypassed entirely by both public directory services, which call
  the lower-level search/ranking primitives directly — a documented, defensible
  choice, but the discovery service's own limit/offset bounding is dead code
  from the public site's perspective.
- **Organization RBAC sync scope** — `OrganizationRoleSyncService` hardcodes
  `_SYNCED_ROLE_TYPES = {ADMIN}`; 4 of the model's 6 `OrgMembershipRole` values
  have no RBAC representation.
- **No flash-message/error-surfacing framework** (KL-022) across `portal`,
  `provider_portal`, `organization_portal` — every failing mutating POST
  silently no-ops with a redirect.

## 10. Current documentation quality

Assessed 2026-07-20 against ~40 specific, independently-checked claims across
eight domain investigations. **Quality is high** — the large majority matched
exactly, including precise test counts, exact resolution orders, and exact
query-count figures. Five confirmed mismatches, all minor except one:

1. `PORTALS_AND_APIS.md` undercounts Admin Portal routes (12 claimed vs. 20 actual).
2. `PERMISSIONS_AND_TENANCY.md` conflates the two role catalogs' names/counts.
3. `IMPLEMENTATION_STATE.md`'s orders-app test count (175 claimed) does not
   reconcile against a direct file-by-file count (135).
4. **`FINANCIAL_SYSTEM.md` describes commission/escrow-release machinery without
   disclosing that the allocation calculator and the release consumer are both
   unwired** — the single most consequential documentation gap found.
5. A code comment in `apps/orders/models.py` cites a guardrail test class that
   does not exist anywhere in the repository.

Full detail: `project docs/assessments/2026-07-20_ENTERPRISE_BASELINE.md` §4.

## 11. Current test baseline

| Metric | Value |
|---|---|
| Test files (repo-wide) | 238 |
| Full regression (last independently re-run, on synced `main` @ `8ee1c67`) | **2,459 / 2,459 green** |
| `manage.py check` | Clean, 0 issues |
| `makemigrations --check --dry-run` | Pre-existing cosmetic drift only (RISK-009, `kernel` app field/index metadata — no schema change, unrelated to any recent merge) |

Coverage is deep and concurrency-proven in booking, availability, affiliation,
and RBAC guardrails. It is thin or absent exactly where the risk register above
says it should be: `apps/common`'s own base classes, customer-portal
notifications, `OrderOffer` (model-only), `AllocationCalculator`'s live
integration point, and order-cancellation authorization. See
`project docs/assessments/2026-07-20_ENTERPRISE_BASELINE.md` §5 for detail.

## 12. Current architecture status

No redesign is warranted. Layer separation and ORM discipline are enforced by
executed AST/regex guardrail tests, not reviewer convention. Tenant isolation is
soundly designed (`TenantAwareModel` + per-app isolation tests) but has no
middleware-level structural backstop. The `ownership_authorized_by` RBAC
fallback is a single, well-documented trust boundary exercised at many
organization-mutation call sites. Two structural dead ends exist
(`DiscoveryService.search()`, `AllocationCalculator`/`SettlementBatch`) with no
live consumer. One previously-undetected scalability risk: unbounded candidate-
set materialization in `SupplierSearchService.filter_suppliers()`. Full detail:
`project docs/assessments/2026-07-20_ENTERPRISE_BASELINE.md` §6.

## 13. Previous milestone

**RBAC Enforcement-Toggle Visibility & Audit Remediation — completed via PR #24**
(merge commit `88b39bc3fb6eaf7f95c1ef7e0cdbe51077a7c331`, 2026-07-20). Added a
read-only admin portal status page (`/admin-portal/system/rbac-enforcement/`),
a `set_rbac_enforcement` management command as the sole audited write path,
architecture guardrail tests enforcing the no-mutation-surface design, and
comprehensive test coverage (81 new tests, full regression 2517/2517 at merge).
This was a cross-cutting security remediation, not a numbered product phase.

## 14. Current milestone

**Phase 5 — Marketplace Order Workflow (active product phase).**

This is the next roadmap-sequenced feature phase. The `OrderOffer` model,
migration (`orders/0008_orderoffer.py`), and 40 model-level tests exist on
`main`. No `OrderOfferService` (the business-logic layer for submit/edit/
withdraw/select/hold/accept) exists anywhere in the repository. The phase
requires a dedicated Architecture Assessment before implementation begins,
per this repository's established governance pattern (Phase 3→4 and Phase 4→5
both required one).

## 15. Next milestone

**Phase 5 — Marketplace Order Workflow Architecture Assessment.** A code-free,
governance-first activity that determines the bounded first-sprint scope from
direct repository evidence. The RBAC remediation (§13) is complete and no longer
blocks this.

**Recommended order after the Phase 5 assessment** (from the 2026-07-20
assessment's own final ranking, carried forward unchanged): OTP real SMS
provider → order-cancellation permission check → an explicit decision on the
escrow-release/commission-allocation wiring gap before either feature flag is
ever enabled for a real tenant → real CI execution + a minimal production
deployment path.

## 16. Known blockers

These block a claim of "production ready" (see §19) but do not block continued
feature development on `main`:

- **OTP SMS delivery** — `_send_sms()` undefined; blocks real-world login/
  registration outside `DEBUG`.
- **No real PSP adapter** — blocks real payment collection; the fake adapter
  lets a customer self-confirm their own payment today.
- **No production deployment path** — no Dockerfile/compose/CD/reverse-proxy/
  start script for `production.py`; CI has never executed per FR-013.
- **Escrow-release and commission-allocation wiring gaps** — block safely
  enabling `commission.escrow_production.enabled` /
  `commission.dispute_release.enabled` for any real tenant; currently harmless
  because both default off.

## 17. RBAC Enforcement-Toggle Remediation — COMPLETED

**Status: RESOLVED** — implemented via PR #24 (merge commit
`88b39bc3fb6eaf7f95c1ef7e0cdbe51077a7c331`, branch
`fix/rbac-enforcement-emergency-control`, merged 2026-07-20T05:51:43Z).
Full regression at merge: 2,517/2,517 green.

Documentation had not yet been synchronized with the repository state after
the RBAC remediation was merged. The §17 specification below is preserved for
traceability — all acceptance criteria are satisfied by the implementation on
`main`.

**Title:** RBAC Enforcement-Toggle Visibility &amp; Audit Remediation

**Why it is next:** the single highest-severity open finding in the 2026-07-20
assessment (§8, Critical). `RBACConfiguration.get_enforcement_enabled(tenant_id)`
can disable all permission checks for an entire tenant, and no surface in the
repository — not Django admin, not `admin_portal`, not `AuditLog` — lets an
operator see, change history for, or be alerted about that flag. It is small
and fully scoped by direct evidence already gathered (no separate architecture
assessment is needed, unlike `OrderOfferService`), and closing it reduces the
blast radius of every other RBAC-dependent finding in this baseline before any
of them are addressed individually.

**Dependencies already satisfied:**
- `ConfigurationKey`/`ConfigurationValue` models exist and are stable
  (`apps.kernel.models.configuration`).
- `AuditLog` is a real, append-only, already-integrated audit mechanism
  (`apps.kernel.models.audit`), called from 25+ existing production sites —
  no new audit infrastructure is required, only a new call site.
- `admin_portal`'s existing permission-gating pattern
  (`require_admin_permission()`) is directly reusable for a new view.
- `PermissionService` and the `rbac.enforcement.enabled` key itself already
  exist and are read correctly at every enforcement point (§8 confirms the
  *read* path is sound — only *visibility into changes* is missing).

**Dependencies still missing:**
- No admin-portal view, URL, or template for browsing `ConfigurationKey`/
  `ConfigurationValue` at all (§3.5 of the assessment) — this target requires
  building the first one, scoped narrowly to RBAC-relevant keys rather than a
  general-purpose configuration editor.
- No existing call site writes an `AuditLog` entry when a `ConfigurationValue`
  changes — this write path does not exist for *any* configuration key today,
  not just the RBAC one, and must be added.

**Acceptance criteria:**
1. An admin-portal-permission-gated view exists that displays the current
   value and change history of `rbac.enforcement.enabled` per tenant.
2. Every write to `ConfigurationValue` for a security-sensitive key (starting
   with `rbac.enforcement.enabled`) is recorded in `AuditLog`, including actor,
   before/after value, and timestamp — reusing the existing `AuditService`, not
   a new logging mechanism.
3. A regression test proves that disabling RBAC enforcement for a tenant
   produces a real, queryable `AuditLog` row.
4. A regression test proves the new view correctly denies access without the
   relevant admin permission (matching every other `admin_portal` view's
   established pattern).
5. No existing RBAC enforcement behavior, `PermissionService` read path, or
   tenant-isolation guarantee changes — this target is additive observability
   only.
6. `manage.py check`, `git diff --check`, and the affected test suites pass;
   full regression is re-run and the new baseline count recorded in this file
   per the governance rule in §18.

**Out of scope:**
- A general-purpose `ConfigurationKey`/`ConfigurationValue`/`FeatureFlag` CRUD
  UI (§3.5's broader "System configuration UI — Not started" finding) — this
  target closes the RBAC-specific instance of that gap, not the whole class of
  gap. The general UI remains a separate, not-yet-scoped future target.
- Any change to `PermissionService`, `RBACConfiguration`, or how enforcement
  itself is evaluated.
- OTP SMS delivery, real PSP integration, escrow/commission wiring, CI
  execution, or production deployment infrastructure — each is real and
  ranked in §8/§15, but each is independent of this target and out of scope
  for it specifically.
- Any admin-portal log viewer or background-job dashboard (separate,
  not-started findings, §6).

## 18. Governance rule — mandatory going forward

> **Every significant implementation milestone or Epic completion must conclude
> with, in order:**
> **1. Repository assessment** — evidence-based, code-and-tests-first, verified
>    against current documentation rather than assumed from it.
> **2. Documentation synchronization** — every active document whose claims the
>    milestone changed is corrected in place; stale "pending"/"not started"
>    language contradicted by the new state is removed, not merely footnoted.
> **3. `PROJECT_BASELINE.md` update** — this file is updated in place (§1–§19)
>    to reflect the new current state; the assessment that produced it is filed
>    as a new, immutable, dated file under `project docs/assessments/`.
> **4. Next-milestone update** — §14/§15/§17 of this file are re-derived from
>    fresh evidence, never carried forward by default numbering alone.
>
> This is binding on all future work in this repository and supersedes any
> conflicting informal practice. It has been added to `01_PROJECT_RULES.md`'s
> and `DOCUMENTATION_RULES.md`'s Rules sections as of this baseline.

## 19. Production readiness assessment

**Verdict: NOT production ready.** The platform is feature-complete across most
business domains and architecturally sound, but three independent, hard
blockers exist, none of which are cosmetic:

1. **Users cannot authenticate in production.** OTP challenges are generated and
   stored but never delivered — `_send_sms()` is not implemented anywhere.
2. **Real money cannot move through the system.** The only payment-provider
   adapter is a fake one; if a tenant enabled escrow production or commission
   dispute-release today, held funds would have no code path to reach a
   caregiver's wallet.
3. **There is no way to deploy this to production.** Django-level hardening in
   `config/settings/production.py` is correct, but no Dockerfile, compose
   variant, CD pipeline, reverse-proxy config, or start script exists to
   actually run it anywhere — and the CI pipeline that would gate a deployment
   has, per the project's own defect register, never executed.

None of these are architectural flaws requiring redesign — each is a concrete,
well-scoped, additive piece of missing wiring against an otherwise sound
foundation. The recommended sequence in §15 addresses the highest-leverage
subset of this list first (the RBAC visibility gap, which is a governance/
observability risk independent of the three launch-blockers above) before
tackling the launch-blockers themselves in the "recommended order after this
milestone."
