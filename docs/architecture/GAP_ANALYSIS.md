# Gap Analysis

Status: current as of the Epic 02 — Marketplace Operational Experience
sprint (branch `claude/epic-02-marketplace-operational-experience`), based
on `main` @ `73bb852ceeff3c551476a628a283a56248abdb6d` (PR #23's merge
commit).

## Where exactly are we today?

Twenty-one merged pull requests have built a real, disciplined, well-tested
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

- **Payment settlement bridge** — a `PaymentIntent` reaching `SUCCEEDED`
  never credits a `Wallet` or creates a `finance.PaymentTransaction`.
  ADR-005 names this explicitly: *"A future orchestration module would
  call `PaymentService.record_payment()` once a `PaymentIntent` reaches
  `SUCCEEDED` — deliberately not built now."* This is the single most
  consequential deferred bridge in the codebase.
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

1. **Financial Operations** (Module 05) — close the payment-to-settlement
   bridge. The prior art exists on both sides of the gap; this is
   mechanical, not exploratory.
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
  assignments. `RoleAssignment.scope_type`/`scope_id` exists on the model
  but is unused by any current code path.
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
