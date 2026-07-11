# Gap Analysis

Status: current as of PR #32's merge (kernel.0010 `UserAccount.email`
migration ordering/rollback fix), `main` @
`72c90f9ed97381ba55466fc680de90f38511b5e7` (PR #32's merge commit).

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
| Tenant-scoping manager inconsistency | 10 models across `kernel`/`accounts`/`reviews`/`wallet`/`finance`/`pricing` | Low today (every call site filters correctly by hand), structurally fragile | Additive `TenantScopedManager` retrofit — schema-safe, no migration required |
| Default roles ship with empty permissions | `apps/kernel/role_catalog.py`'s `DEV_BOOTSTRAP_ROLES` (most non-`organization_admin`/`platform-owner` entries) | Real gap for any fresh deployment wanting the API/RBAC-gated features usable | Product/security decision needed: which roles get which keys, seeded explicitly |
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
| No single test chains real affiliation-approval to financial-party resolution end-to-end | `apps.accounts.tests.test_supplier_bridge` (real flow, no financial assertion) vs. `apps.finance.tests.test_organization_provider_financial_isolation` (financial assertion, direct fixture) | Low — both halves independently, correctly tested | Add one test combining both, once convenient |
| Two role-seeding catalogs remain intentionally distinct role sets | `apps.kernel.role_catalog.DEV_BOOTSTRAP_ROLES` (hyphenated, `dev` tenant) vs. `DEFAULT_TENANT_ROLES` (underscored, real `salmandyar` tenant) — centralized into one shared module by Epic 05, but deliberately not merged/renamed (would mean renaming live `Role`/`RoleAssignment` database rows) | Low — `reconcile_role_permissions` keeps each catalog's own permissions in sync with its own roles; the one known slug alias (`platform-owner`/`platform_owner`) is recorded but not merged | A future, dedicated, database-safe rename/merge decision if the two are ever meant to become one taxonomy — see ADR-010 |
| Raw-literal `PermissionService` guardrail is regex-based, not AST-based | `apps.kernel.tests.test_permission_registry_guardrails.NoRawLiteralPermissionKeysTest` | Low — no current call site uses variable indirection or keyword-argument form to pass a key, but neither would be caught if one did | Harden to an AST-based check, or add a convention note, if a bypass is ever found |
| `PermissionService` does not validate a `permission_key` against the canonical registry at evaluation time | `apps.kernel.services.permission_service.PermissionService.check()`/`.require()` | Low — an unknown/unregistered key fails closed by construction (behaves exactly like a legitimate-but-ungranted key), but this is implicit and untested, not an explicit, tested policy | Add a test asserting the fail-closed behavior for an unregistered key; document it in `rbac-permissions.md` |
| No preflight check for pre-existing duplicate non-blank emails | `apps/kernel/migrations/0010_useraccount_email_unique.py` | Low — `email` was never unique before this migration, so a duplicate is plausible but unconfirmed on any given database; if one exists, the migration's `ADD CONSTRAINT UNIQUE` step fails safely (transactional abort, no corruption) but with no operator-facing guidance | A separate preflight/reporting tool if this is ever hit in practice — reconciling real duplicate user data is a product decision, not a mechanical migration fix (PR #32 Architecture Review Minor finding) |

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

## Future placeholders — resolved by Epic 04 (Enterprise Organization Isolation)

Two previously tracked gaps from Epic 02's own gap list are now closed,
plus one new capability Epic 04 delivered that was not itself a
previously documented gap:

**Previously tracked Epic 02 gaps, now closed:**

- **Organization Assignment Center tenant-wide visibility** — see the
  dedicated section immediately below.
- **Organization-scoped RBAC seeding** — a real production writer now
  exists (`OrganizationRoleSyncService`); the three keys it grants are
  now genuinely enforced at their intended call sites — see "Future
  placeholders — resolved by Epic 05" below.

**New capability delivered by Epic 04 (not a previously tracked gap):**

- **Affiliated-provider financial identity** — `SupplierType
  .ORGANIZATION_PROVIDER` (a Module 03 enum value, previously
  unreachable) is now created for organization-affiliated caregivers
  (`apps.accounts.services.supplier_bridge`), with a one-time
  reconciliation command (`reconcile_organization_provider_suppliers`)
  for caregivers affiliated before this change. Financial policy is
  unchanged and verified by regression test: `FinancialPartyService
  .resolve_party_for_supplier()` still keys strictly on `supplier_type
  == SupplierType.ORGANIZATION`, so an affiliated caregiver's earnings
  continue to settle to their own wallet, never the organization's.

### ~~Organization Assignment Center is tenant-wide, not organization-scoped~~ — closed by Epic 04

**Resolved** (Epic 04 — Enterprise Organization Isolation, PR #28,
merged). A new `OrderOrganizationEligibility` junction model
(`apps.orders.models`, sole writer `apps.orders.services
.eligibility_service.OrderEligibilityService`, guardrail-enforced —
`OrderOrganizationEligibilitySoleWriterTest`) makes eligibility explicit:
an order is claimable by an organization only if an `ACTIVE` eligibility
row exists for that `(order, organization)` pair, granted via the
`grant_order_eligibility` management command (no automatic/implicit
grant rule — verified no existing signal in `create_public_order()`/
`create_operator_order()` to build one from). `apps.orders.services
.queries.OrderQueryService.list_eligible_for_organization()` replaced
`list_unassigned_for_tenant()` as the Assignment Center's query
(`apps.organization_portal.views.assignment_center_view`);
`OrganizationAssignmentService.assign_manual()` re-checks eligibility
(or pre-existing assignment ownership, for reassignment) before
delegating to `AssignmentService.assign()`, denying and auditing
(`OrganizationAccessDenied` domain event) before any mutation otherwise.
Cross-organization and cross-tenant isolation are covered by regression
tests (`apps.organization_portal.tests.test_assignment_center
.EligibilityEnforcementTest`). `list_unassigned_for_tenant()` itself
still exists (retained for any genuinely tenant-wide/platform-admin
caller — none exist today) but is no longer reachable from
`apps.organization_portal`.

**Production readiness**: this feature is now safe for a tenant hosting
multiple independent organizations — an organization admin can no longer
see or claim another organization's orders. See `docs/adr
/ADR-009_ORGANIZATION_ELIGIBILITY_AND_SCOPED_RBAC.md` for the full design
record and the alternatives considered (a direct `Order.organization` FK,
a formal bidding/routing model) and why the explicit-grant junction model
was chosen over both.

## Future placeholders — resolved by Epic 05 (Permission-Key Registry & Authorization Hardening)

- **No permission-key registry** and **organization-scoped RBAC seeding
  exists but enforcement does not** — both closed; see "Architecture
  gaps" above for the full writeup.
- **Reviewer-ownership defect** — `ReviewSubmissionService.submit_review()`
  previously never verified the reviewer was the order's own customer;
  now fixed at the service level, with dedicated allow/deny tests. See
  `docs/adr/ADR-010_CANONICAL_PERMISSION_REGISTRY.md`'s defect writeup
  #4 for the full previous-behavior/risk/remediation account.
- **`AssignmentService.replace()` had zero authorization** — now enforces
  the same canonical key `assign()` does. No production caller exists yet
  (confirmed by inspection), closed before one is ever wired up.

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
2. **Identity, Roles, Profiles & Access** (Module 08) — the canonical
   permission-key registry now exists (Epic 05) and every organization
   permission key is now genuinely enforced. What remains: general
   default-role permission seeding for the broader `DEV_BOOTSTRAP_ROLES`
   catalog (most non-`organization_admin`/`platform-owner` roles still
   ship with empty `permissions`) and the two server-rendered
   portals-still-ownership-scoped-rather-than-RBAC-scoped choice
   (deliberate, see `DECISION_HISTORY.md`, not a defect).
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

- ~~No permission-key registry~~ — **closed by Epic 05** (Permission-Key
  Registry & Authorization Hardening, PR #29, merged). A canonical,
  in-memory Python registry (`apps.kernel.permissions`, 23 keys) is now
  the single source of truth for every real permission key, with
  duplicate/malformed-key rejection at Django startup and a guardrail
  test proving no production `PermissionService` call site uses a raw
  string literal. The pre-existing, migrated `kernel.Permission` model
  remains deliberately dormant — see `docs/adr
  /ADR-010_CANONICAL_PERMISSION_REGISTRY.md` for why. The three
  server-rendered portals (`apps.portal`, `apps.provider_portal`,
  `apps.organization_portal`) still use ownership as their primary
  security boundary — a deliberate, consistent choice (see
  `DECISION_HISTORY.md`), not drift.
- ~~Organization-scoped RBAC seeding exists but enforcement at the
  intended call sites does not~~ — **closed by Epic 05**.
  `RoleAssignment.scope_type="organization"`/`scope_id` evaluation and
  its production writer (`OrganizationRoleSyncService`, since Epic 04)
  now have their consumer side wired up too: `AssignmentService.assign()`
  /`.replace()` and `OrganizationStaffService.approve_membership()`/
  `suspend_membership()` all check their intended canonical permission
  key. Migrating every real `PermissionService` call site to a canonical
  constant surfaced three real, independent authorization defects (all
  fixed with dedicated tests) — the phantom
  `organization.assignment.assign` key Epic 04 granted but
  `AssignmentService.assign()` never checked (retired; `organization_admin`
  now carries the actual checked key), the two membership methods having
  granted keys with zero enforcement, and `AssignmentService.replace()`
  having no authorization at all. The pre-existing `ownership_authorized_by`
  fallback remains in place and is now the exception path (used only
  until an admin's `RoleAssignment` has synced), not the normal path —
  see `rbac-permissions.md`'s "The `ownership_authorized_by` security
  contract" section for the exact, explicit guarantee (and non-guarantee)
  this fallback provides. See `docs/adr
  /ADR-010_CANONICAL_PERMISSION_REGISTRY.md` for the full defect writeups
  and `DECISION_HISTORY.md` for the decision record.
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
