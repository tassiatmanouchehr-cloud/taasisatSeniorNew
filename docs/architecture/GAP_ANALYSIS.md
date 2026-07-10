# Gap Analysis

Status: current as of PR #26's merge (Epic 03 Sprint 1 — Financial
Settlement & Money Flow), `main` @
`36e07c68c40a72d896a03af2a484ba2e2ab2b2ca` (PR #26's merge commit).

## Where exactly are we today?

Twenty-three merged pull requests have built a real, disciplined, well-tested
**foundation** — not a finished product. The demand-side transaction loop
(identity → order → matching → booking → execution → pricing → wallet →
reviews) is genuinely walkable end-to-end in code. What it does not yet
reach is the outside world: no request in this system currently arrives
at a real payment processor, a real SMS/email/push provider, a real
map/geocoding service, or a real background-job consumer beyond
notification dispatch. Every external edge is a documented, intentional
fake. Six to eight of twenty-five Blueprint modules have not been started
at all. The codebase's own delivery history has quietly drifted from the
Blueprint's module numbering without ever writing that fact down before
this sprint. See `PROJECT_MODULE_STATUS.md` for the full module-by-module
evidence behind every claim in this document.

---

## Completed capabilities

Nothing in this repository is "Completed" against its full Blueprint
scope (see `PROJECT_MODULE_STATUS.md`'s rollup) — every module's spec
describes more than any product needs on day one. Within that framing,
these capabilities are genuinely finished and unlikely to need
foundational rework:

- Person/UserAccount/Tenant identity model, with email-based Django Admin
  login (UUID no longer exposed as a login identifier).
- Multi-role account attachment (`ensure_customer_profile()` /
  `ensure_caregiver_profile()`), idempotent, no duplicate accounts.
- `PermissionService` as the sole, fail-closed RBAC evaluator.
- The append-only ledger pattern (`WalletTransaction`, `PaymentCallback`,
  `PaymentTransaction` all override `save()`/`delete()` to forbid
  mutation after creation).
- The thin-controller / service-layer discipline, automated-guardrail
  enforced across `apps.api` and `apps.admin_portal`.
- The `DomainEvent` vs. `EventOutbox` separation, automated-guardrail
  enforced.
- `apps.wallet` as the sole canonical wallet, automated-guardrail
  enforced (a third `Wallet`/`WalletTransaction` model would fail CI).

## Mostly completed capabilities

(Blueprint status "Mostly Complete" — see `PROJECT_MODULE_STATUS.md` for
each module's exact remaining work.)

- **Booking & Assignment** (Module 03) — real lifecycle, thinner on
  reassignment/conflict depth.
- **Financial Operations** (Module 05) — the deepest subsystem in the
  repository (30 test files across `finance`/`wallet`/`payments`
  combined), gated end-to-end on one missing bridge (see *Deferred
  architecture* below).
- **Identity, Roles, Profiles & Access** (Module 08) — real auth and
  multi-role identity, gated on a missing permission-key registry and
  incomplete default-role permission seeding.
- **Review, Rating & Reputation** (Module 14) — real and tested, with one
  known integrity bug (see *Known limitations* below).
- **Background Jobs & Scheduler** (Module 22) — real, tested execution
  infrastructure with almost no real handlers registered against it yet.
- **Platform Kernel & Shared Contracts** (Module 25) — the best-maintained
  part of the system; some Phase-0.5-frozen entities (`Branch`,
  `Department`, `Team`, `Capability`/`Skill`/`Certification`) were specced
  but never built.

## Partial capabilities

(11 modules — see `PROJECT_MODULE_STATUS.md` rows for Modules 02, 04, 07,
09, 11, 12, 17, 18, 19, 23, 24.) The common shape across all eleven: a
real, tested, well-architected foundation exists, but it is disconnected
from either (a) a completing workflow step (Matching has no customer
selection; Execution has no evidence capture), (b) a real external
integration (Communication has no real provider; API Gateway has no
public/partner surface), or (c) most of the module's actual described
scope (Incentives has pricing but not referrals; i18n has one locale, not
a framework; Config/Flags has the primitive but no product feature uses
it).

## Missing capabilities

(8 modules with zero code — see `PROJECT_MODULE_STATUS.md` rows for
Modules 01, 06, 10, 13, 15, 16, 20, 21.)

- **Request Engine** — no `Request` aggregate; `Order` proxies for it.
- **Trust, Compliance & Governance** — no dispute/appeal/fraud model.
- **Geospatial, Maps & Location** — no addresses, geocoding, or distance
  logic anywhere.
- **Document, Media & File Management** — no file/storage model at all.
- **Knowledge, CMS & Content** — `public_site`/`showcase` are static
  shells, not a content system.
- **Workflow & Automation Engine** — not to be confused with `apps.jobs`
  (Module 22); no stateful, event-triggered workflow engine exists.
- **AI & Recommendation Engine** — zero AI/ML code anywhere.
- **Subscription, Plans & Licensing** — no plan/quota/entitlement model.

---

## Technical debt

A full-tree search (`src/`, excluding migrations and `__pycache__`) found
**one** open `TODO`, **zero** `FIXME`s, **zero** `HACK`s, **zero**
dead-code comments, and **zero** `raise NotImplementedError`. Debt in this
codebase is documented in module docstrings ("LEGACY/FROZEN," "foundation
only," "deferred") rather than left as scattered inline apologies.
Registered, tracked debt:

| Item | Location | Risk | Resolution |
|---|---|---|---|
| Accounts/kernel migration-check drift | `makemigrations --check --dry-run` | Low — cosmetic, `migrate` always reports no real changes | Would require pinning/regenerating a clean Django-version baseline; out of scope for a docs sprint |
| Legacy frozen Finance wallet | `apps/finance/models/wallet.py`, `apps/finance/services/wallet_service.py` | Low — guardrail-enforced against accidental reuse | Would require a real migration (dropping tables); not worth doing without an unrelated reason to touch Finance |
| Review reviewer-ownership gap | `apps.reviews.ReviewSubmissionService.submit_review()` | Medium in production (reputation integrity), low today (no real external API consumers yet) | Small, targeted service-layer fix — add `order.customer_profile.person_id == reviewer_person_id` |
| Tenant-scoping manager inconsistency | 10 models across `kernel`/`accounts`/`reviews`/`wallet`/`finance`/`pricing` | Low today (every call site filters correctly by hand), structurally fragile | Additive `TenantScopedManager` retrofit — schema-safe, no migration required |
| Default roles ship with empty permissions | `apps/kernel/management/commands/seed_tenant.py` | Real gap for any fresh deployment wanting the API/RBAC-gated features usable | Product/security decision needed: which roles get which keys, seeded explicitly |
| No permission-key registry | `apps.kernel.models.rbac.Role.permissions` (freeform JSON string list) | Low today, real long-term risk (a typo'd key silently grants nothing, forever) | A registry table validating `permission_key` against a canonical list — a real RBAC-hardening module |
| Two parallel async-execution mechanisms | `apps.jobs` vs. `kernel.tasks`'s Celery/EventOutbox worker | Low today (each was a reasonable local decision), confusing long-term | Reconcile into one story before either grows further — see *Duplicated concepts* below |
| Settlement retry-job mechanism has no dedicated test coverage | `apps.payments.jobs`, `PaymentCallbackService._trigger_settlement` | Medium — the recovery path for Critical Finding 1 is architecturally sound but unverified by test evidence | Add tests: job creation on callback-triggered failure, handler execution via `JobService.execute_job()`, idempotent re-enqueue, direct-call failures not enqueuing |
| Settlement enqueue-failure not hardened | `PaymentCallbackService._trigger_settlement` | Low probability, real when it occurs — an enqueue failure propagates out of `process_callback()` uncaught, breaking its "never re-raised" contract | Wrap `JobService.enqueue(...)` in its own try/except inside the existing except-block |
| Settlement process-crash window | Between callback commit and retry-job enqueue in `_trigger_settlement` | Low — narrow (single-digit ms), no real traffic yet | A periodic reconciliation sweep (`PaymentIntent` SUCCEEDED without a matching `PaymentTransaction`) would close it; not yet built |
| `PaymentTransaction.provider_reference` semantic overload | `apps/finance/models/payment.py` | Low today (single producer, single meaning); will need attention once a real PSP integration needs the field for its original purpose | Separate the internal settlement-idempotency key from any future real external-provider reference field |
| `LedgerEntry` uniqueness constraint not forward-compatible | `apps/finance/models/ledger.py`, `uq_ledger_entry_payment_txn_account_code` | Medium — as scoped (`payment_transaction`, `account_code`), it would block legitimate future split-payment/multi-beneficiary/correction postings | Add `party`/`entry_type` to the constraint, or rescope to `entry_group_id`-based, before any multi-beneficiary settlement work begins |
| Settlement callback-status test gaps | `apps/payments/tests/test_settlement_orchestration.py` | Low — behavior is correct by code inspection (terminal-state transition guard), just unproven for these specific cases | Add tests for `AUTHORIZED`/`EXPIRED` callbacks and a differently-`provider_event_id`'d callback arriving after terminal `SUCCEEDED` |
| Adjustment pipeline has no internal arithmetic invariants | `apps.payments.services.settlement_adjustments.SettlementAdjustmentPipeline` | Low today (identity function, trivially balanced); real risk once a non-trivial rule is added | Add a `net == gross - commission - tax + discount_recovery` consistency assertion inside `run()` |
| Escrow warning is log-only and re-fires on every retry | `SettlementOrchestrationService.settle_payment_intent` | Low — operationally noisy, not incorrect; every settlement today logs it since `financial.escrow.enabled` is unseeded and defaults `True` | Persist a queryable/alertable record, or seed the config key explicitly per tenant, or deduplicate per intent |
| Retry-triggered settlements not distinguishable from first-attempt in audit trail | `PermissionService.require(actor=None, ...)` system-context logging, used identically by both paths | Low — consistent with existing system-context precedent, just imprecise | Record `job.id`/a "settled_via" marker in the relevant audit/event payload if this distinction is ever needed operationally |

## Known limitations

- OTP codes are logged to console in `DEBUG` mode only; no real SMS
  provider exists (`apps/accounts/services/otp.py:99`, the repository's
  one open `TODO`).
- `apps.reporting` recomputes every report live on every request — no
  caching, documented as acceptable at current data volumes, not at
  production scale (ADR-006).
- `apps/api/views/*.py` don't share request-parsing helpers beyond
  pagination/permissions — the "resolve tenant-scoped object from a
  request-body ID" pattern is duplicated in `views/pricing.py` and
  `views/reviews.py`. Judged not worth abstracting at 2–3 call sites;
  worth revisiting past 4–5.

## Temporary implementations

- `kernel.tasks._dispatch_to_consumers` — logs and returns; the Celery
  outbox worker fully polls, retries, and dead-letters `EventOutbox` rows,
  but nothing downstream ever actually consumes one. The docstring itself
  says: *"Phase 1: No external consumers registered yet."*
- `kernel.tasks.refresh_config_cache` — docstring: *"This task exists as a
  placeholder for future cache warming or consistency checks."*

## Fake providers

All intentionally named `Fake*`, all documented as explicit stand-ins, all
guardrail-adjacent (a real provider being added is expected to *add* an
adapter, not replace these in place):

- `apps.payments.providers.fake.FakePaymentProviderAdapter` — the only
  registered PSP adapter. `PaymentProviderRegistry` maps
  `PaymentProvider.FAKE` to it; nothing else is registered.
- `apps.notifications.providers.fake` — `FakeSmsProvider`,
  `FakeEmailProvider`, `FakePushProvider`, `FakeInAppProvider`. Confirmed
  by repository-wide search: no real SMS/email/push SDK (Twilio,
  SendGrid, Kavenegar, Firebase, OneSignal, Mailgun, etc.) exists
  anywhere.
- `apps.jobs.handlers` — `demo.no_op`, `demo.always_fail`, `demo.echo`.
  Docstring: *"They have no business side effects and must never be
  pointed at real domain state."*

## Deferred architecture

- ~~**Payment settlement bridge**~~ — **closed by Epic 03 Sprint 1** (PR
  #26, merged). A `PaymentIntent` reaching `SUCCEEDED` now resolves the
  order's `FinancialDocument`/`FinancialObligation`, records a
  `finance.PaymentTransaction`, posts a balanced `LedgerEntry` group, and
  credits the beneficiary's canonical `apps.wallet.Wallet` —
  `apps.payments.services.SettlementOrchestrationService`, triggered from
  `PaymentCallbackService.process_callback()`. Direct Settlement only; all
  commission/tax/discount adjustments still zero (see
  `SettlementAdjustmentPipeline`, the preserved extension point).
  Concurrent settlement attempts are serialized on a `PaymentIntent` row
  lock, backed by two database `UniqueConstraint`s (verified by a real
  multi-thread test). A failed settlement durably enqueues a
  `payments.settlement.retry` job (`apps.jobs`) rather than only logging.
  Still deferred, now tracked as their own technical-debt items below:
  real commission/tax calculation, escrow execution (config seam exists
  and is read, but always warns-and-falls-back to Direct Settlement),
  provider payout batches, real PSP adapters.
- **Real PSP signature/HMAC verification** — the fake payment callback
  endpoint requires no authentication by design (it simulates an
  unauthenticated PSP webhook). A real adapter's callback route must add
  signature verification; the fake endpoint should not be copied as a
  template without adding it.
- **CES event consumers** — the outbox worker infrastructure is complete
  and scheduled; no subscriber has ever been registered against it.
- **Reporting materialization** — explicitly deferred since Module 16; if
  ever needed, should be introduced additively behind the existing
  `ReportingService` call sites.

## Future placeholders — resolved by Customer Experience Phase 1

Both items ADR-008 scoped as future work are now implemented:

- **Care Recipient** — built by extending the pre-existing `ElderProfile`
  model in place (`apps.accounts.models.profiles.ElderProfile`), rather
  than introducing a duplicate model — reachable from `CustomerProfile`
  via `customer_profile.elder_profiles`, referenced by `Order.elder_profile`
  (an FK that already existed). `apps.accounts.services.care_recipients.CareRecipientService`
  owns create/update/list/ownership-scoped-get. Product/UI vocabulary says
  "Care Recipient"; the Django model class name stays `ElderProfile`.
- **Order Share Link** — `apps.orders.models.OrderShareLink` +
  `apps.orders.services.share_links.OrderShareLinkService`: an
  unguessable token (`secrets.token_urlsafe(32)`), time-limited (14-day
  default), revocable, read-only, scoped to exactly one order. The public
  resolve view (`apps.portal.views.shared_order_view`) never authenticates
  and never resolves a `CustomerProfile`, so it structurally cannot reach
  wallet/payments/profile/notifications/other-orders/dashboard.

Both ship as part of the new `apps.portal` app (Customer Experience Phase
1) — a server-rendered customer dashboard, care recipient management,
service request wizard, order timeline, and notification center — none of
which is a numbered Blueprint module (mirrors `apps.admin_portal`'s
cross-cutting, unnumbered status).

## Future placeholders — resolved by Epic 02 (Marketplace Operational Experience)

Provider Experience's and Organization Experience's "matching is worthless
if the matched provider never gets to act on it" gap (see
`PRODUCT_ROADMAP.md`) is now partially closed:

- **Provider assignment accept/decline** — `SupplierAssignmentStatus`
  gained a `DECLINED` value; `apps.booking.services.provider_actions.
  ProviderAssignmentActionService` (an explicit, extensible transition
  table, not ad-hoc status writes) lets a provider confirm or decline
  their own assignment from the new `apps.provider_portal` app.
  Confirming also creates the `ExecutionSession` (orchestrated at the
  portal-view layer, since `apps.booking` cannot import `apps.execution`
  — see `dependency-graph.md`).
- **Provider visit execution** — `apps.execution.services.provider_actions.
  ProviderExecutionService` wraps the unmodified `ExecutionService.
  start_session()`/`complete_session()` with ownership verification, reached
  from `apps.provider_portal`. No second execution lifecycle.
- **Provider availability, earnings** — `apps.provider_portal` exposes the
  pre-existing `apps.availability` services directly and a read-only
  earnings view backed by `apps.reporting.ProviderReportService`.
- **Organization staff & assignment** — `apps.organization_portal` exposes
  `OrganizationMembership` staff lifecycle (approve/suspend, using fields
  that already existed on the model) and a manual staff-assignment center
  (`OrganizationAssignmentService.assign_manual()`, reusing
  `AssignmentService.assign()` unmodified — the service boundary is shaped
  to hold future automatic/bulk/shift assignment strategies, none of which
  are implemented yet).

Still open after Epic 02: candidate accept/decline *at the Matching
proposal stage* (Module 02) — what Epic 02 built is acceptance of an
already-created `SupplierAssignment`, one step downstream of Matching
itself, which remains unchanged. See `PROJECT_MODULE_STATUS.md` Module 02.

### Organization Assignment Center is tenant-wide, not organization-scoped

**Current behavior** (verified against `apps.orders.services.queries.
OrderQueryService.list_unassigned_for_tenant()`, which
`apps.organization_portal.views.assignment_center_view` calls directly):
the Assignment Center shows *every* unassigned, non-final order in the
caller's tenant — filtered only by `tenant_id` and `assigned_supplier
__isnull=True`, with no filter on which organization the order is
"for," no service-category eligibility filter, and no concept of "orders
this organization should see" versus "orders any organization could see."
Any organization admin in a tenant sees the identical open-work list as
every other organization admin in that same tenant.

**Why this is acceptable for the first vertical slice**: this epic's
scope was proving the assign-a-staff-member-to-an-order mechanism end to
end (`OrganizationAssignmentService.assign_manual()` → the existing,
unmodified `AssignmentService.assign()`), reusing the existing `Order`
model, which has no organization-eligibility field to filter on yet. Every
test fixture and every demo scenario built against this epic assumes a
single organization per tenant, so the gap has not yet been exercised
against real data.

**Multi-organization visibility risk**: in any tenant that hosts more
than one organization — which the platform's multi-tenant/white-label
design otherwise supports — every organization admin can currently see
(though not directly read customer PII beyond what `Order` already
exposes) and, critically, *assign their own staff to*, an order that a
competing organization has no claim to. This is a real business-logic
gap, not merely a cosmetic one: the assignment center as built does not
distinguish "an order this organization should compete for or has been
routed to" from "any unclaimed order in the tenant."

**Required future improvement**: an eligibility/routing concept between
`Order` and `OrganizationProfile` (e.g., service-category-to-organization
routing, an explicit "open to bid" vs. "assigned to this organization"
order state, or a matching-engine hand-off restricted to one organization)
must exist before `list_unassigned_for_tenant()` can be narrowed from
tenant-wide to organization-scoped. No such concept exists in the domain
model today — this is model work, not a query-filter change.

**Production readiness**: this feature is **not yet production-ready for
any tenant containing more than one organization with unrelated or
competing interests.** It is safe and correct only for the case this
epic actually targeted: a tenant operating as (or standing in for) a
single organization. Deploying it as-is to a tenant with multiple
independent organizations would let each one see and act on every other
one's open orders.

## Duplicated concepts

| Concept | Where | Status |
|---|---|---|
| Wallet | `apps.finance.models.wallet.WalletAccount` vs. `apps.wallet.Wallet` | **Resolved** — legacy marked, guardrail-enforced (ADR-004) |
| "Run this later" | `apps.jobs` (plain Django + management command) vs. `kernel.tasks` (Celery + `EventOutbox` worker, scheduled via `CELERY_BEAT_SCHEDULE`) | **Open** — two different async-execution stories exist in parallel, each individually reasonable, never reconciled |
| Module numbering | PR/branch labels ("module-09," "module-12," "module-20") vs. Blueprint module numbers | **Resolved by this sprint** — `PROJECT_MODULE_STATUS.md` is now the canonical mapping |
| "Event" vocabulary | `DomainEvent` (in-memory) vs. `EventOutbox`/CES (persisted) | **Not a defect** — deliberately separate, documented, guardrail-enforced; flagged here only because the shared word invites confusion without that documentation |

## Deprecated ideas

None found. `PolicyStatus.DEPRECATED` is a real, intentional lifecycle
state on `PolicyDefinition` (a policy can be deprecated as a product
action) — not a marker of unmaintained code. No module, service, or model
in this repository is marked deprecated in the sense of "should not be
used and is scheduled for removal," aside from the already-covered legacy
Finance wallet (which is *frozen*, not deprecated — its own tests still
pass and it is intentionally kept, not scheduled for deletion).

---

## Modules that should never change again

Bound by ADR-001.23 (*"any deviation requires a new ADR with owner
approval"*) and reaffirmed by every module built on top of them without
needing to bend:

- Person ≠ UserAccount ≠ Provider identity chain.
- `ServiceSupplier` as the sole supply-side abstraction.
- Shared-database, `tenant_id`-scoped multi-tenancy (not
  database-per-tenant or schema-per-tenant).
- `PermissionService` as the sole RBAC evaluator.
- The thin-controller / service-layer discipline.
- The append-only ledger invariant.
- The `DomainEvent` / `EventOutbox` separation.
- `apps.wallet` as the one canonical wallet.

## Modules needing expansion

Ranked by leverage, not by module number:

1. **Financial Operations** (Module 05) — the payment-to-settlement bridge
   is closed (Epic 03 Sprint 1, PR #26, Direct Settlement only). Remaining:
   real commission/tax/discount rules behind the `SettlementAdjustmentPipeline`
   extension point, escrow execution, provider payout batches, real PSP
   adapters — plus the operational-hardening technical debt listed below
   (retry-path test coverage, `LedgerEntry` constraint generalization,
   `provider_reference` semantics).
2. **Identity, Roles, Profiles & Access** (Module 08) — finish the
   permission-key registry and general default-role permission seeding.
   Every RBAC-gated feature in a fresh deployment is silently inert
   without it.
3. **Background Jobs & Scheduler** (Module 22) — register real handlers.
   The hard infrastructure work is already done; only consumers are
   missing.
4. **Matching Engine** (Module 02) — a customer-selection flow. Matching
   currently proposes candidates that nothing lets a customer act on.

## Modules needing refactoring

- `apps.reviews.ReviewSubmissionService` — a small, targeted fix (add the
  missing reviewer-ownership check), not a redesign.
- The ten tenant-scoping-inconsistent models — a mechanical,
  additive-only `TenantScopedManager` retrofit.
- The async-execution duality (`apps.jobs` vs. `kernel.tasks`'s Celery
  worker) — a decision, not necessarily a code rewrite: choose one story
  and document which future work goes where.

## Business gaps

- No request in the system can currently reach a real customer's phone,
  inbox, or push notification — the platform cannot notify a real person
  today.
- No request can currently be paid for through a real payment method.
- No caregiver can be found by real-world proximity — no geospatial
  capability exists.
- No dispute, complaint, or fraud signal can currently be captured,
  investigated, or resolved anywhere in the platform.
- A customer cannot select who they want from a set of matched
  candidates — matching proposes, nothing lets them choose. (A provider
  *can* now accept/decline a `SupplierAssignment` once one exists — Epic
  02 — but the upstream candidate-selection step itself is unchanged.)

## Architecture gaps

- No permission-key registry — a typo in a granted permission string
  fails silently, forever. All three server-rendered portals today
  (`apps.portal`, `apps.provider_portal`, `apps.organization_portal`) use
  ownership as their security boundary instead of RBAC permission keys —
  a deliberate, consistent choice (see `DECISION_HISTORY.md`), not drift —
  because no infrastructure exists yet to seed org/provider-scoped role
  assignments.
- **Organization-scoped RBAC seeding does not exist yet** (Enterprise
  Architecture Review follow-up, finding #5). `RoleAssignment.scope_type`/
  `scope_id` and `PermissionService`'s own `_scope_matches()` evaluation
  logic are real and exercised (`PermissionService.check()`/`require()`
  both honor an explicit `scope` kwarg) — but nothing in the codebase
  today creates a `RoleAssignment(scope_type="organization",
  scope_id=<org.id>)` row for an organization admin, and
  `OrganizationAssignmentService.assign_manual()` doesn't pass a `scope`
  kwarg either. Building this properly requires real product decisions
  (a `Role` taxonomy for organization admins, a hook point — likely
  wherever an `OrganizationMembership` becomes `ADMIN`/`ACTIVE` — that
  creates the `RoleAssignment`, and a backfill story for any admin
  memberships that predate the mechanism) — judged too large to safely
  improvise as part of a remediation pass. Until it lands,
  `OrganizationAssignmentService.assign_manual()` calls
  `AssignmentService.assign(ownership_authorized_by=actor)`:
  `PermissionService.require()` tries the real actor as a normal RBAC
  actor first (so this starts enforcing for free the moment seeding
  exists — no code change needed at that point) and only falls back to an
  explicit, correctly actor-attributed `rbac.permission.ownership_authorized`
  audit entry when no matching role exists — never silently logged as
  `system_context`, and the real actor is always the recorded
  `SupplierAssignment.assigned_by`. See `DECISION_HISTORY.md` for the full
  reasoning.
- No public API surface — nothing external can integrate with this
  platform today.
- No metrics, tracing, or alerting beyond a single health-check endpoint
  and structured audit logs — an incident would be diagnosed by reading
  logs, not by a dashboard.
- No true multi-locale framework — the platform is architecturally
  multi-tenant/white-label-capable (per the Phase 0.5 freeze) but is not
  yet exercised past a single hardcoded locale.
- Two parallel async-execution mechanisms with no documented decision
  about which one future work should extend.

---

See [`PRODUCT_ROADMAP.md`](PRODUCT_ROADMAP.md) for how this analysis
translates into a prioritized plan grouped by business value, and
[`PROJECT_MODULE_STATUS.md`](PROJECT_MODULE_STATUS.md) for the
module-by-module evidence behind every claim above.
