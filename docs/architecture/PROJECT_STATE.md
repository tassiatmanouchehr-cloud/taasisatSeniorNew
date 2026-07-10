# Project State

Status: current as of PR #28's merge (Epic 04 — Enterprise Organization
Isolation), `main` @
`13e91de8b6d2ff31091d70afa9b0bc53ab07ae8e` (PR #28's merge commit). This document is the
**single source of truth** for "where the project stands." It supersedes any
verbal summary given in chat, a PR description, or a prior conversation —
if this file and a conversation disagree, this file is right (or needs
updating).

Every statement below is evidence-based: derived from reading the actual
`requirements/*.txt`, `config/settings/*.py`, `.github/workflows/ci.yml`,
`docs/adr/*.md`, `docs/architecture/*.md`, source code, and a live
`python manage.py test` run — not inferred from PR titles or commit
messages. Anything not directly verifiable is explicitly marked **Needs
Verification** rather than assumed.

---

## Repository

| Field | Value |
|---|---|
| Repository URL | `github.com/tassiatmanouchehr-cloud/taasisatSenior` |
| Default Branch | `main` |
| Current `main` HEAD | `13e91de8b6d2ff31091d70afa9b0bc53ab07ae8e` (PR #28's merge commit) |
| Current Test Count | **1209 passing**, 0 failing (`python manage.py test`, run on this branch — 58 new tests over the PR #26 baseline of 1151, all from Epic 04 — Enterprise Organization Isolation: order-organization eligibility CRUD/query, real-thread `TransactionTestCase` assignment-concurrency proofs, organization-scoped RBAC sync mechanics, assignment-center eligibility enforcement, the `backfill_organization_role_assignments`/`reconcile_organization_provider_suppliers` commands, cross-organization affiliated-provider isolation, and provider-affiliation financial-isolation regression — see `DECISION_HISTORY.md`) |
| Python Version | **3.12** is the project's canonical version — declared in `pyproject.toml` (`requires-python = ">=3.12"`), pinned in CI (`.github/workflows/ci.yml`, `python-version: "3.12"`), and pinned in `src/docker/Dockerfile.dev` (`FROM python:3.12-slim`). Three independent sources agree. The one execution environment that disagrees is this specific sandboxed session, which runs **3.11.15** — a fact about this session's container, not about the repository's declared target. Not flagged as uncertain: the repository is internally consistent on 3.12; only this particular runtime differs from it. |
| Django Version | Installed: **5.2.16**. Declared requirement (`requirements/base.txt`): `django>=5.1,<5.3`. Consistent. |
| Database | **PostgreSQL 16**, optionally with **PostGIS** (`GIS_ENABLED` env var switches `django.db.backends.postgresql` ↔ `django.contrib.gis.db.backends.postgis`; CI uses the `postgis/postgis:16-3.4` image with `GIS_ENABLED=true`). SQLite is supported as a settings-level fallback (`DATABASE_ENGINE=sqlite`) but is not the platform's real target and is not exercised by CI. |
| Architecture Style | **Modular monolith** — a single Django project (`config/`) composed of 24 apps under `src/apps/`, each owning its own models/services/tests, communicating through service-layer calls and two deliberately separate event systems (see [Domain Events](#domain-events) below), not through network calls. No microservices, no separate deployable units. |
| Current Development Phase | **Product Experience phase, in progress; Financial Settlement Sprint 1 and Enterprise Organization Isolation (Epic 04) now merged.** Customer Experience Phase 1 and Phase 2, Provider Experience Phase 1, Organization Experience Phase 1, Epic 03 Sprint 1 (Financial Settlement & Money Flow), and Epic 04 (Enterprise Organization Isolation) are now built. See [Current Development Phase](#current-development-phase) below. |
| Current Project Status | Active development. 28 merged pull requests on `main` (PR #28, Epic 04 — Enterprise Organization Isolation, just merged; PR #27 was the preceding documentation-sync PR covering PR #26); this documentation-sync PR (covering PR #28) is open. A second Epic (PR #29, Epic 05 — Permission-Key Registry & Authorization Hardening) is open, stacked on the pre-merge Epic 04 branch, and awaits rebase onto this new `main` plus its own Architecture Review cycle before merge — not included in this document, per this repo's established "no unmerged work described as fact" rule. One documentation-maintenance PR (#21, opened after PR #20, predating Epic 02) remains open and now has merge conflicts against current `main` — not touched by this or any subsequent epic. No open incidents or known production deployment (no evidence of a live/production environment in this repository — infra config exists for one, but nothing indicates it is running). |
| Current Branching Strategy | Trunk-based: every unit of work branches from `main` (branch naming has drifted over time — see [Repository Structure](#repository-structure) → *A note on module numbering*), is reviewed as a pull request, and merges back to `main`. No long-lived release branches exist. `.github/workflows/ci.yml` also recognizes `phase-*/**` branches as a push trigger, though none currently exist. |
| Repository Structure | See [below](#repository-structure). |
| Current CI/Test Status | See [below](#current-ci--test-status). |
| Current Documentation | See [below](#current-documentation). |

---

## Repository Structure

```
taasisatSenior/
├── ARCHITECTURE_INTAKE_REPORT_v1.0.md       # pre-code Blueprint intake (93KB)
├── PHASE_0_5_ENTERPRISE_DOMAIN_MODEL_FREEZE.md   # frozen domain model (104KB)
├── PHASE_1_IMPLEMENTATION_PLAN.md           # original Phase 1 (kernel-only) plan (60KB)
├── build_architecture_records/
│   └── ADR_001_ARCHITECTURE_FREEZE_v1_0.md  # ADR-001 — 24 binding pre-code decisions
├── module/                                   # 25 Blueprint module spec packages (aspirational,
│                                               # pre-code — see PROJECT_MODULE_STATUS.md for what
│                                               # of each actually got built) + the correction package
├── docs/
│   ├── adr/                                   # ADR-002 .. ADR-008 — decisions made *during* build
│   └── architecture/                          # living reference docs + this file
└── src/                                        # the actual Django project
    ├── apps/                                    # 24 apps — see table below
    ├── config/                                   # settings, urls, celery, wsgi
    ├── templates/, static/, ui/                   # server-rendered UI (Django + HTMX + Alpine + Tailwind)
    ├── tests/visual/                               # Playwright visual/accessibility tests
    ├── locale/                                      # empty placeholder (.gitkeep only) — no .po files exist yet
    ├── requirements/                                 # base.txt / test.txt / dev.txt etc.
    └── .github/workflows/ci.yml                       # CI pipeline
```

### The 24 apps, one line each

| App | Owns |
|---|---|
| `kernel` | Tenant, Person, UserAccount, RBAC, ServiceSupplier, ConfigResolver, DomainEvent + EventOutbox/CES, AuditService |
| `accounts` | CustomerProfile, CaregiverProfile, OrganizationProfile, OrganizationMembership, affiliation requests, OTP/registration |
| `orders` | ServiceCategory/ServiceType catalog, `Order` lifecycle/status machine |
| `matching` | MatchRound/MatchCandidate — candidate generation, eligibility, ranking |
| `booking` | SupplierAssignment — the operative record of a supplier committing to an order |
| `execution` | ExecutionSession — on-the-ground service-delivery lifecycle |
| `finance` | FinancialParty, FinancialDocument, PaymentTransaction (ledger), FinancialObligation, LedgerEntry, SettlementBatch, plus a legacy/frozen wallet |
| `wallet` | Wallet, WalletTransaction — the one canonical internal stored-value ledger |
| `payments` | PaymentIntent/PaymentAttempt/PaymentCallback — gateway-facing orchestration |
| `availability` | ProviderWorkingWindow, AvailabilityBlockedPeriod, CapacityRule |
| `pricing` | PricingRule, Promotion, Quote |
| `discovery` | Read-only supplier search/ranking (owns no models) |
| `reviews` | Review, ReviewRating, ReputationSnapshot |
| `notifications` | Notification rows + dispatch pipeline (fake providers) |
| `jobs` | JobDefinition, JobRun, handler registry, `run_due_jobs` |
| `reporting` | Read-only aggregation over other apps' data (owns no models) |
| `api` | The `/api/v1/` DRF surface |
| `admin_portal` | Server-rendered, read-only internal dashboards |
| `portal` | Server-rendered customer dashboard, care recipient management, service request wizard, order timeline, share links, notification center |
| `provider_portal` | Server-rendered, supplier-generic provider workspace: dashboard, assignment accept/decline, visit start/complete, availability management, earnings summary, notifications |
| `organization_portal` | Server-rendered organization admin workspace: dashboard, staff (membership) management, manual assignment center, capacity overview, performance reports, notifications |
| `common` | Abstract base models (TimestampedModel, TenantAwareModel, SoftDeleteMixin) |
| `public_site` | Static, server-rendered marketing pages |
| `showcase` | Development-only UI component/design-system browser |

### A note on module numbering

Branch and PR names in this repository's history (`module-05`, `module-09`,
`module-12`, `module-20`, …) refer to **build order**, not the 25-module
Blueprint's own numbering (`module/MODULE_INDEX_COMPLETE_01_25.json`). They
do not match. For example, the branch `module-09-domain-events` shipped
what the Blueprint calls **Module 12 (Communication & Notification
Engine)**; the Blueprint's actual **Module 9 (Search, Discovery &
Filtering)** shipped under the branch name `module-12-search-discovery`.
**Always use Blueprint module numbers when discussing scope** —
`PROJECT_MODULE_STATUS.md` is the authoritative mapping between the two.

---

## Current CI/Test Status

`.github/workflows/ci.yml` defines five jobs on every push to `main`/`phase-*/**` and every PR into `main`:

| Job | What it checks |
|---|---|
| `lint` | `ruff check .` + `ruff format --check .` |
| `ui-quality` | Design-token, RTL, theme-consistency, and component-architecture validation scripts (`tools/validate_*.py`) |
| `tailwind` | Builds `static/css/output.css` from `ui/css/main.css`, verifies the output exists |
| `test` | `python manage.py check` → `migrate` → `test --verbosity=2`, against a real `postgis/postgis:16` + `redis:7` service pair |
| `visual-regression` | Playwright accessibility/visual-snapshot tests against a running dev server, gated on `tailwind` + `test` passing |

**Verified directly against the GitHub Actions API**: this workflow has **never actually run** — `GET /repos/tassiatmanouchehr-cloud/taasisatSenior/actions/workflows` returns zero registered workflows and zero runs. `ci.yml` is a real, complete, checked-in pipeline definition that GitHub has not yet executed even once (most likely because Actions has never been enabled/triggered for this repository, not because of a failure). There is therefore no CI pass/fail history to report — "green" or "red" does not yet apply. What *is* independently confirmed, locally, on this branch: `python manage.py check` reports 0 issues and `python manage.py test` reports **1209 passed, 0 failed**.

### Known, harmless migration-check quirk

`python manage.py makemigrations --check --dry-run` reports pending
cosmetic changes for `apps.accounts` and `apps.kernel` on every run — a
Django-version-skew artifact (`help_text`/index-naming differences with no
real schema difference) documented since the project's early history.
`python manage.py migrate` always reports "no migrations to apply" for
these, confirming there is no real drift. See
[`technical-debt-register.md`](technical-debt-register.md) for the full
entry.

---

## Current Documentation

Three layers exist, oldest/most aspirational to newest/most binding:

1. **The frozen pre-code Blueprint** — `ARCHITECTURE_INTAKE_REPORT_v1.0.md`, `PHASE_0_5_ENTERPRISE_DOMAIN_MODEL_FREEZE.md`, `PHASE_1_IMPLEMENTATION_PLAN.md`, `build_architecture_records/ADR_001_ARCHITECTURE_FREEZE_v1_0.md`, and the 25 `module/Senior_Platform_Module_*` spec packages. These describe the full aspirational system, written before any Django model existed. They are targets, not a progress tracker — see `PROJECT_MODULE_STATUS.md` for what of each was actually built.
2. **The as-built ADRs** (`docs/adr/ADR-002` .. `ADR-008`) — decisions made *during* implementation, each correcting or narrowing the Blueprint to what was actually needed. Indexed in [`DECISION_HISTORY.md`](DECISION_HISTORY.md).
3. **The living reference** (`docs/architecture/*.md`) — eight documents (plus this one and its four siblings added in this sprint) describing exactly what is built and what is known to be missing. This is the most trustworthy layer for "what exists today."

Full navigation: [`PROJECT_INDEX.md`](PROJECT_INDEX.md).

---

## Completed Foundations

Each item below: what it is, which app(s) own it, and its real maturity —
not its Blueprint-spec maturity. "Complete" here means *the foundation
itself is done, tested, and depended upon by other code* — not that every
capability the Blueprint imagined for that area exists. See
[`GAP_ANALYSIS.md`](GAP_ANALYSIS.md) and
[`PROJECT_MODULE_STATUS.md`](PROJECT_MODULE_STATUS.md) for exactly what's
missing from each.

### Kernel
`apps.kernel`. The shared foundation every other app depends on: `Tenant`,
`Person`, `UserAccount`, RBAC data model, `ServiceSupplier` (the universal
supply-side abstraction), `ConfigResolver`/`ConfigurationKey`/
`ConfigurationValue`, `FeatureFlag`, `PolicyDefinition`/`PolicyVersion`,
`AuditLog`, `EventOutbox`. The most heavily tested app in the repository.

### Multi-Tenancy
Shared-database, `tenant_id`-scoped model (not database-per-tenant or
schema-per-tenant) — frozen by ADR-001.12. `TenantScopedManager` is the
default pattern; a documented, known-safe list of ~10 models instead rely
on manual `tenant_id=` filtering at every call site (see
`technical-debt-register.md`).

### RBAC
`apps.kernel.services.permission_service.PermissionService` is the sole
evaluator of `Role`/`RoleAssignment` for any authorization decision —
fail-closed, no `is_superuser` bypass. `Role.permissions` is a freeform
JSON string list (no permission-key registry table exists — a documented
gap, see `rbac-permissions.md`). As of Epic 04, `RoleAssignment
.scope_type="organization"` finally has a production writer
(`apps.accounts.services.organization_rbac.OrganizationRoleSyncService`,
sole writer, idempotent, concurrency-safe via a partial unique
constraint) — but the three organization-facing permission keys it grants
are not yet checked by any `PermissionService.require()`/`.check()` call
site; every affected action is still authorized through the pre-existing
`ownership_authorized_by` fallback. See `rbac-permissions.md`'s "The
three organization permission keys" section and `GAP_ANALYSIS.md` for the
full accounting — wiring those call sites is Permission-Key Registry &
Authorization Hardening (Epic 05, not yet merged) scope.

### Authentication
Two independent, non-overlapping login paths: (1) phone/OTP for
customer-facing flows (`apps.accounts`, OTP delivery is currently
console-only in `DEBUG` — no real SMS provider is wired), and (2)
email/password for Django Admin and staff (`UserAccount.USERNAME_FIELD =
"email"`, fixed to no longer expose the UUID primary key as a login
identifier).

### Multi-role Users
One `Person`/`UserAccount` can hold multiple profiles (customer,
caregiver, organization admin, etc.) without duplicate accounts.
`ensure_customer_profile()`/`ensure_caregiver_profile()` in
`apps.accounts.services.profiles` attach a profile to an *existing*
account idempotently. No `FamilyMemberProfile` or similar concept exists
by design (ADR-008). The care recipient a customer requests service *for*
is separate, non-authenticating data — `ElderProfile`, extended in
Customer Experience Phase 1 to serve as ADR-008's "Care Recipient" — never
a `UserAccount`.

### Domain Events
Two deliberately separate systems (see `event-architecture.md`):
- **`DomainEvent`** (`apps.kernel.events`) — an in-memory, synchronous,
  frozen-dataclass fan-out. Its only current consumer creates
  `Notification` rows.
- **`EventOutbox`/CES** (`apps.kernel.models.event_outbox`) — a persisted,
  transactionally-written outbox with a Celery worker
  (`apps.kernel.tasks`) that polls and marks rows published — but that
  worker's consumer-dispatch step (`_dispatch_to_consumers`) is a
  documented no-op; no real subscriber exists yet.

### Background Jobs
`apps.jobs` — `JobDefinition`/`JobRun`, a handler registry, retry with
exponential backoff, dead-lettering, and a `run_due_jobs` management
command. Built deliberately without a Celery/Redis dependency. Two real
handlers are registered today: `notifications.dispatch_pending` and, as
of Epic 03 Sprint 1, `payments.settlement.retry` (`apps.payments.jobs`,
settlement-failure recovery — see Payments below); all others remain
demo/no-op.

### Notification Dispatch
`apps.notifications` — `NotificationDeliveryAttempt` audit trail,
`NotificationProviderRegistry`, retry/backoff/dead-letter dispatch service.
Every registered provider is fake (`FakeSmsProvider`, `FakeEmailProvider`,
`FakePushProvider`, `FakeInAppProvider`) — no real SMS/email/push SDK
exists anywhere in the repository (confirmed by full-tree search).

### Matching
`apps.matching` — `MatchRound`/`MatchCandidate`, eligibility evaluation,
deterministic ranking. Proposes candidates only; never assigns (assignment
stays with `apps.orders`). No customer-selection or candidate
accept/decline flow exists yet.

### Booking
`apps.booking` — `SupplierAssignment`, the operative record of a supplier
committing to an order. `Order.assigned_supplier` remains the source of
truth for the *current* assignment by design.

### Execution
`apps.execution` — `ExecutionSession`, the on-the-ground delivery
lifecycle layered on `Order.status`. No execution evidence/media capture
(that belongs to the not-yet-started Document/Media module).

### Finance
`apps.finance` — ledger, financial documents, obligations, settlement
batches. Contains a legacy, frozen wallet (`WalletAccount`/
`WalletTransaction`) explicitly superseded by `apps.wallet` (ADR-004,
guardrail-enforced).

### Wallet
`apps.wallet` — the one canonical internal stored-value ledger (ADR-004).
Referenced via `FinancialParty`, the universal financial-counterparty
abstraction shared with `finance` and `payments`.

### Payments
`apps.payments` — `PaymentIntent`/`PaymentAttempt`/`PaymentCallback`, a
provider-agnostic pre-settlement state machine, deliberately separate from
`finance.PaymentTransaction` (ADR-005). Only provider: a fake adapter. The
bridge from a successful payment to an actual wallet credit and finance
settlement record was closed in Epic 03 Sprint 1 (PR #26,
`apps.payments.services.SettlementOrchestrationService`): a `PaymentIntent`
reaching `SUCCEEDED` now resolves the order's `FinancialDocument`, records
a `finance.PaymentTransaction`, posts a balanced `LedgerEntry` group, and
credits the beneficiary's canonical `apps.wallet.Wallet` — Direct
Settlement only, with a `PaymentIntent` row lock plus two database
`UniqueConstraint`s guaranteeing concurrent-settlement safety, and a
durable `payments.settlement.retry` job (`apps.jobs`) recovering a failed
attempt rather than only logging it. Real commission/tax calculation,
escrow execution, provider payouts, and a real PSP adapter remain the
open gaps in the Financial Operations area — see `GAP_ANALYSIS.md`.

### Pricing
`apps.pricing` — `PricingRule`, `Promotion`, `Quote`. Deliberately upstream
of Finance (a future invoice would consume a Quote, not the reverse).

### Availability
`apps.availability` — `ProviderWorkingWindow`, `AvailabilityBlockedPeriod`,
`CapacityRule`. Feeds Matching/Booking; not a named Blueprint module of
its own.

### Discovery
`apps.discovery` — read-only supplier search/ranking. Owns no models of
its own. No full-text search engine, no geo-aware discovery.

### Reviews
`apps.reviews` — `Review`, `ReviewRating`, `ReputationSnapshot`. One known,
documented integrity bug: `ReviewSubmissionService` never verifies the
reviewer is the order's actual customer (see `GAP_ANALYSIS.md`).

### Reporting
`apps.reporting` — a pure, models-less read layer (ADR-006). Every report
computed live via ORM aggregation, DTOs only, no caching or
materialization.

### DRF API
`apps.api` — the `/api/v1/` surface, built on real Django REST Framework
(ADR-003, corrected mid-build after an initial hand-rolled version was
found to be based on an incomplete dependency check). Thin-controller
discipline is automated-guardrail-enforced (ADR-007).

### Public APIs
Five domains, roughly nine endpoints (discovery, pricing, reviews, wallet
read, payments) live under `/api/v1/` today — internal-facing only. No
partner/public API surface, no webhooks out, no API keys, no throttling,
no OpenAPI schema (`drf-spectacular` is installed and unused).

### Admin Portal
`apps.admin_portal` — server-rendered, strictly read-only internal
dashboards over `apps.reporting`. No write capability exists in this app
today.

### Provider Portal
`apps.provider_portal` — Provider Experience Phase 1. Built entirely
around `kernel.ServiceSupplier`, never `CaregiverProfile`, directly:
`apps.accounts.services.provider_identity.resolve_supplier_for_user()` is
the one boundary that turns a `UserAccount` into a `ServiceSupplier`, so
the portal itself is supplier-generic and reusable for future non-caregiver
supplier types without change. Assignment accept/decline is an explicit,
extensible transition table (`apps.booking.services.provider_actions.
ALLOWED_PROVIDER_TRANSITIONS`), not ad-hoc status writes — a new
`SupplierAssignmentStatus.DECLINED` value was added to support it. Visit
start/complete reuse `apps.execution.services.ExecutionService` unchanged
(`apps.execution.services.provider_actions.ProviderExecutionService` adds
only ownership verification). Availability management reuses
`apps.availability` services directly (two additive query-service methods
were the only availability change). Earnings reuse `apps.reporting`'s
existing `ProviderReportService`. No RBAC permission keys — ownership
(`resolve_supplier_for_user`) is the security boundary, mirroring
`apps.portal`'s established pattern.

### Organization Portal
`apps.organization_portal` — Organization Experience Phase 1, with
Enterprise Organization Isolation (Epic 04) hardening on top. Staff
management reuses `OrganizationMembership` (`apps.accounts.services.
organization_staff.OrganizationStaffService`) — no new membership model;
approve/suspend use the model's pre-existing `status`/`approved_by`/
`joined_at` fields, and (as of Epic 04) run inside `@transaction.atomic`
with a row lock, syncing an organization-scoped `RoleAssignment` in the
same transaction via `OrganizationRoleSyncService`. The assignment center
(`apps.booking.services.organization_assignment.OrganizationAssignmentService.
assign_manual()`) is one named strategy behind a service boundary designed
to hold future strategies (automatic, bulk, shift) without a breaking
change; it calls the existing `AssignmentService.assign()` unmodified — no
second booking/assignment engine. As of Epic 04, the assignment center's
"open work" query is organization-scoped, not tenant-wide: an order is
only claimable once an explicit `OrderOrganizationEligibility` grant
exists for that organization (`apps.orders.services.eligibility_service
.OrderEligibilityService`), closing the gap `GAP_ANALYSIS.md` previously
documented under "Organization Assignment Center is tenant-wide, not
organization-scoped." Capacity reuses
`apps.availability.services.capacity_service.CapacityService`. Reports
reuse `apps.reporting.services.provider_report_service.ProviderReportService`
(one new `list_reports_for_suppliers()` batch method). An admin's own
`OrganizationMembership` (role=ADMIN, status=ACTIVE) remains the primary
security boundary — RBAC permission keys now exist for three
organization-admin actions but are not yet the enforcement mechanism in
practice (see the RBAC section above). Deliberately scoped to exactly one
organization per admin (see `DECISION_HISTORY.md`).

### Architecture Guardrails
`apps/kernel/tests/test_architecture_guardrails.py` — automated,
source-inspection-based tests enforcing several of the rules below at CI
time (not just in documentation): thin-controller ORM discipline in
`apps.api`/`apps.admin_portal`, no reverse import of `apps.api`, no
duplicate Wallet/WalletTransaction model, `EventOutbox` touched only by
its two designated owners, no undocumented direct coupling to concrete
profile models outside `kernel.ServiceSupplier`.

### ADR System
Two tiers: ADR-001 (pre-code, 24 binding sub-decisions, lives in
`build_architecture_records/`) and ADR-002 through ADR-008 (as-built,
`docs/adr/`) — each documenting one real decision made while building,
with Context/Decision/Consequences. Indexed in
[`DECISION_HISTORY.md`](DECISION_HISTORY.md).

---

## Architecture Rules

These rules are already enforced today, either by convention (documented,
followed) or by an automated guardrail test (documented, enforced by CI).
Where a guardrail exists, it's named.

| Rule | Enforcement |
|---|---|
| **Thin controllers** — a view never contains a loop, a business-rule conditional, or a multi-row ORM query. | Guardrail: `ApiViewOrmDisciplineTest`, `AdminPortalOrmDisciplineTest`, `PortalOrmDisciplineTest`, `ProviderPortalOrmDisciplineTest`, `OrganizationPortalOrmDisciplineTest` |
| **Supplier-generic provider surfaces** — code that acts on behalf of "a provider" operates on `kernel.ServiceSupplier`, never a concrete profile type (`CaregiverProfile`, etc.) directly. | Convention: `apps.accounts.services.provider_identity.resolve_supplier_for_user()` is the one bridge; `apps.provider_portal` imports no concrete supplier-profile model |
| **Extensible transition tables for cross-actor actions** — an action one actor takes on another actor's record (accept/decline an assignment, assign staff to an order) is a named entry in a service-level table, not an inline status write in a view. | Convention: `apps.booking.services.provider_actions.ALLOWED_PROVIDER_TRANSITIONS`, mirroring the pre-existing `apps.payments.services.transitions.ALLOWED_TRANSITIONS` |
| **Services own business logic** — every mutating operation lives in a `services/` package, never in a model or a view. | Convention (`service-layer-guidelines.md`), ADR-007 |
| **Repository layering** — dependencies flow one way, roughly in Blueprint-adjacent order; a lower-numbered app never imports a higher-numbered one, with two named, guarded exceptions. | Convention (`dependency-graph.md`); guardrail: `NoReverseApiImportTest` |
| **Bounded contexts** — each app owns a clearly stated set of models and never reaches into another app's internals. | Convention (`bounded-contexts.md`) |
| **Domain Events vs. EventOutbox separation** — `DomainEvent` (in-memory) and `EventOutbox`/CES (persisted) never touch each other. | Convention (`event-architecture.md`); guardrail: `EventSystemSeparationTest` |
| **`apps.wallet` is canonical** — the one and only active wallet bounded context; `apps.finance`'s wallet is legacy/frozen. | ADR-004; guardrail: `NoDuplicateWalletModelTest` |
| **PaymentIntent boundary** — `apps.payments` never creates a `finance.PaymentTransaction`, `Wallet`/`WalletTransaction`, or `FinancialDocument` row. | ADR-005 |
| **Multi-role accounts** — one `Person`/`UserAccount` may hold several profiles; never a duplicate account per role. | Convention (`ensure_*_profile()` helpers), documented in this file above |
| **Care Recipient** — a reusable entity reachable from `CustomerProfile` (`ElderProfile`, extended in place — see `DECISION_HISTORY.md`), referenced by `Order`, never order-embedded. | ADR-008; `apps.accounts.services.care_recipients.CareRecipientService` |
| **Order Share Link** — invitation-based, single-order, read-only visibility for a non-account third party; the resolving view never authenticates and never resolves a `CustomerProfile`. | ADR-008; `apps.orders.services.share_links.OrderShareLinkService` |
| **ADR-first architecture** — any deviation from a frozen decision requires a new ADR with explicit approval, not an ad-hoc code change. | ADR-001.23 |
| **Guardrail tests** — several of the rules above are checked by source-inspection tests in `apps/kernel/tests/test_architecture_guardrails.py`, run as part of the normal test suite (not a separate CI job). | CI `test` job |

---

## Current Development Phase

**Foundation is largely complete. Product Experience is in progress
across all three sides of the marketplace, and the first Financial
Settlement sprint has landed on top of it.**

Concretely: the demand-side transaction loop — a customer can exist
(identity + multi-role profile), request something (via `Order`, standing
in for the not-yet-built Request aggregate), have it matched, assigned,
executed, priced, reviewed, and now **actually paid and settled** — is
real, tested, end-to-end walkable code. What it is *not* yet connected to
is the outside world: no request reaches a real payment processor (the
settlement mechanics are real, but only the fake PSP adapter exists), a
real SMS/email/push provider, a real map/geocoding service, or most
real background-job consumers. Every one of those edges is a documented,
intentional fake.

Epic 02 (Marketplace Operational Experience) added the operator-facing
side of the loop on top of the existing services, with no duplicated
architecture: a provider can now see and act on their own assignments and
visits (`apps.provider_portal`), and an organization admin can manage
staff and assign work (`apps.organization_portal`), alongside the
customer-facing work `apps.portal` already covered.

Epic 03 Sprint 1 (Financial Settlement & Money Flow — PR #26, merged)
closed the single most consequential gap that remained after Epic 02:
`apps.payments.services.SettlementOrchestrationService` now connects a
successful `PaymentIntent` all the way through to a real
`finance.PaymentTransaction`, balanced `LedgerEntry` postings, and a
credited `apps.wallet.Wallet`, wired from `PaymentCallbackService`,
concurrency-safe (`PaymentIntent` row lock plus two database
constraints), and recoverable on failure (a durable `apps.jobs` retry).
The platform now has a walkable, three-sided operational surface that
also actually moves and settles money internally — even though none of
it yet reaches a real external PSP, SMS, or geocoding provider. See
`GAP_ANALYSIS.md`'s technical-debt register for what remains open in the
settlement path specifically (retry-path test coverage, a periodic
reconciliation job, `LedgerEntry` constraint generalization, and others).

Epic 04 (Enterprise Organization Isolation — PR #28, merged) closed the
next most consequential gap after Epic 03: the organization portal's
Assignment Center was tenant-wide, not organization-scoped, meaning any
organization admin in a multi-organization tenant could see and claim
another organization's orders. `apps.orders.services.eligibility_service
.OrderEligibilityService` (backed by a new `OrderOrganizationEligibility`
junction model, sole-writer-guardrail-enforced) now gates the Assignment
Center to explicit, actor-attributed grants per (order, organization)
pair. `AssignmentService.assign()`/`replace()` gained
`Order.objects.select_for_update()` row-locking, proven safe under real
concurrent Postgres transactions. `RoleAssignment.scope_type="organization"`
evaluation — real since Module 08 but never written to — now has a
production writer (`OrganizationRoleSyncService`), though the permission
keys it grants are not yet consulted by any real call site (see the RBAC
section above). `SupplierType.ORGANIZATION_PROVIDER` (previously
unreachable) is now created for organization-affiliated caregivers, with
financial isolation verified unchanged by regression test. A stacked
follow-on Epic (05 — Permission-Key Registry & Authorization Hardening,
PR #29) is implemented and pending its own Architecture Review/merge
cycle; it closes the RBAC-enforcement gap Epic 04 left open, among other
authorization-hardening work, but is not yet part of `main` and is not
described as fact anywhere in this document.

This means the highest-leverage next work is not "build another
foundation module" — most of the foundation-shaped work left (Trust &
Governance, Document/Media, Workflow Automation, AI, Subscriptions,
Geospatial) is real, but lower urgency than **finishing the loops the
existing foundation already implies**: a real PSP adapter behind the now-
real settlement bridge, a notification that actually reaches someone, and
wiring the organization-scoped permission keys Epic 04 introduced to
their real enforcement call sites (Epic 05, pending merge) — see
`GAP_ANALYSIS.md`. See
[`GAP_ANALYSIS.md`](GAP_ANALYSIS.md) and
[`PRODUCT_ROADMAP.md`](PRODUCT_ROADMAP.md) for the detailed breakdown and
prioritization.

---

*This document does not track day-to-day progress. Update it when a
foundation is added, an architecture rule changes, or the CI/test
baseline changes — not on every PR.*
