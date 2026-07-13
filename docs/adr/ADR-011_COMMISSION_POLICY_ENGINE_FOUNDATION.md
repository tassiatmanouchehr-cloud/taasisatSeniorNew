# ADR-011 — Commission Policy Engine Foundation (Financial Core PR-A)

## Status

Accepted — Financial Core PR-A (System Architect's frozen business model,
delivered after two rounds of read-only Financial Engine audit in this same
engagement).

## Context

The System Architect froze the target Financial Core business model: five
financial actors (Platform/Manouchehr, Customer, Independent Caregiver,
Company, Company-Affiliated Caregiver), four default commission splits
(Independent 20/80, Company-Caregiver-Affiliated 7/13/80, Company-Direct
7/93, Goods 0/0/100), a four-tier commission-resolution priority (active
Company-Caregiver Contract > platform-specific override > cooperation-type
default > global default), an immutable per-order snapshot frozen at
proposal/offer acceptance, and a configurable payment-completion deadline
(default 30 minutes) enforced by a real scheduled job.

The prior two audit rounds (see the Financial Integrity Audit and Enterprise
Financial Audit reports delivered earlier in this engagement) established,
by direct code inspection and live execution, that none of this existed:
`SettlementAdjustmentPipeline` was a hardcoded identity function (net ==
gross, commission always zero) for every supplier type; no commission
configuration model existed; no company-caregiver contract concept existed;
no payment-deadline/offer-expiry mechanism existed (`PaymentIntent
.expires_at` was written once and never read).

The same audits also found `apps.kernel.models.policy.PolicyDefinition` /
`PolicyVersion` (Module 08, "Major business rules... are implemented as
versioned policies... immutable version snapshots... only one version
active at a time per policy") — a generic, already-built, already-tested
versioned-policy framework, with `scope_type`/`scope_id` and point-in-time
(`at_time`) resolution, sitting completely unused by any business rule in
the repository.

## Decision — reuse the existing generic policy engine; add a dedicated model only where its shape doesn't fit

**`apps.kernel.services.policy_service.PolicyService` is reused as the
storage/versioning/activation engine for three of the four priority tiers**
(global default, cooperation-type default, platform-specific override),
via a new `apps.commission` app that owns the commission-specific
`policy_type="commission"` payload shape and validation
(`CommissionPolicyService`). This directly satisfies the instruction to
"reuse approved existing services and architecture where they are
correct" — nothing about `PolicyDefinition`/`PolicyVersion`'s immutability,
activation/supersession, or point-in-time resolution needed to change.

**A dedicated `CommissionContract` model (in `apps.commission.models
.contract`) covers the fourth, highest-priority tier** — the bilateral
Company↔Caregiver negotiation — because its shape does not fit
`PolicyVersion`'s simpler `draft → pending_approval → active → superseded`
lifecycle: a contract needs a two-party proposer/approver negotiation (a
company proposes, a caregiver must approve — Business Model Section 10),
and terminal `REJECTED`/`TERMINATED` states `PolicyVersion` has no
equivalent for. Forcing this into `PolicyVersion` would have meant
overloading a generic governance model with two-party semantics it wasn't
designed for, so a purpose-built model was used instead — reuse where the
existing shape fits, a new model only where it genuinely doesn't.

**One canonical resolver (`CommissionRuleResolver`), not four scattered
lookups.** Every tier-2/3/4 lookup goes through `CommissionPolicyService`;
`CommissionRuleResolver` is the single place that implements the four-tier
priority order end to end, directly satisfying Business Model Section 8's
explicit requirement: "Do not scatter percentages across settings,
services, and templates. Implement one canonical policy-resolution
service."

**Global vs. cooperation-type default are stored as two distinct
`PolicyDefinition` scopes** (`scope_type="tenant"` holding all four splits
bulk-versioned together in one payload, vs. `scope_type="cooperation_type"`
per-key overrides), even though in practice they resolve to the same
percentages until a platform owner overrides one specific cooperation type.
This preserves the Business Model's explicit "change all global defaults
together" (one atomic bulk version) as functionally distinct from "override
just this one cooperation type" (a narrower, independently-versioned
change) — documented here explicitly as a deliberate architectural choice,
not a redundant no-op layer.

**Platform-override and cooperation-type-default `PolicyDefinition` rows
for the same key must use different `name` values** —
`override_policy_name(key, party_scope_type, party_id)` vs.
`cooperation_policy_name(key)` — because `PolicyDefinition`'s own
`unique_together = (tenant_id, policy_type, name)` does not include
`scope_type`/`scope_id`. Reusing the same name across scopes would have
silently collapsed a per-caregiver override into the same row as the
cooperation-type default (caught by this PR's own test suite, not a
theoretical risk — `PriorityChainTest
.test_platform_override_for_caregiver_overrides_cooperation_default`
failed under the first implementation and was fixed before merge-readiness).

## Decision — accepted-proposal representation: no new Offer model

Business Model Section 2 explicitly instructs: "Do not invent a new Offer
model automatically. First map the current accepted-proposal
representation." Inspection of `apps.orders`/`apps.booking` found no
`Offer` model at all — the closest, and correct, representation is
`apps.booking.services.assignment_service.AssignmentService.assign()`,
which is "the ONLY mutation of Order.assigned_supplier / Order.status"
(that service's own pre-existing docstring) and is exactly the point at
which a caregiver commits to an order. `CommissionSnapshotService
.create_snapshot_for_order()` and `PaymentDeadlineService
.create_for_order()` are both invoked from a single new
`AssignmentService._open_financial_core_for_assignment()` call at the end
of `assign()`, inside its existing `@transaction.atomic` boundary — the
smallest correct integration point, not a parallel Offer-acceptance
pathway.

`SupplierAssignmentStatus.EXPIRED` already existed in the schema
(`apps.booking.models`) as an unused enum value at the time of this PR — a
new `AssignmentService.expire()` method (mirroring the existing `.cancel()`
exactly, differing only in terminal status and event name) is the first
code to ever set it, rather than inventing a new status.

## Decision — payment-deadline expiry is a real scheduled `apps.jobs` job

`JobService.enqueue(..., scheduled_for=deadline_at)` schedules the
`commission.payment_deadline.expire` job for the exact due timestamp,
consumed by the existing `run_due_jobs` sweep — mirroring
`apps.payments.jobs`'s `payments.settlement.retry` pattern exactly, per
Business Model Section 2's explicit requirement: "The expiry must be
enforced by a real scheduled job, not only by a lazy page view check."
Extending a deadline reschedules the same `JobDefinition` row
(`next_run_at`/`scheduled_for` updated directly) rather than enqueuing a
second job, since `JobDefinition` carries no immutability constraint of its
own (unlike the finance ledger/document models) and rescheduling is the
correct operation, not a duplicate.

## Consequences

- A future engineer building PR-B (real escrow) or PR-C (multi-party
  settlement) must resolve commission rates via `CommissionRuleResolver`
  only — never re-implement tier resolution, and never read
  `PolicyDefinition`/`PolicyVersion` directly for a commission concern.
- `CommissionSnapshot` is a `ForeignKey` on `Order`, not `OneToOne` —
  a reassignment after a payment-deadline expiry (a genuinely new
  acceptance cycle) gets its own fresh snapshot; "the current snapshot for
  an order" is resolved by querying the latest snapshot for that
  `(order, supplier)` pair, never assumed to be singular per order.
- PR-A does not yet compute any real money: `CommissionSnapshot
  .accepted_gross_amount` is nullable (Order carries no price field at
  assignment time — pricing resolves later, at invoice time) and nothing
  in the real settlement path (`SettlementAdjustmentPipeline`,
  `SettlementOrchestrationService`) has been touched. See the PR-A final
  report for the complete "known limitations reserved for PR-B onward"
  list.

## Addendum — System Architect Review remediation (post-merge-readiness, pre-merge)

An independent Architecture/Domain/Security/Migration/Acceptance Review of
this PR surfaced one Critical and several Major/Minor findings, all
resolved in a single follow-up remediation commit on this same branch
(not a new PR — PR-A's scope is otherwise unchanged). Recorded here since
they are architecture-relevant decisions, not just bug fixes:

- **Payment-timing conflict (Critical, resolved by explicit System
  Architect decision, not a lifecycle redesign).** The final business rule
  is pay-before-service with Escrow: an accepted proposal is frozen, the
  customer must pay within the deadline, payment succeeds *before* service
  execution, and the money then sits in Escrow until completion/dispute
  handling/release. This repository's current order lifecycle is
  execution-first (assign → execute → invoice → pay) and does not match
  that rule yet — redesigning the lifecycle is out of scope for PR-A and
  its remediation; it belongs to whichever future PR introduces real
  pre-service `PaymentIntent` → successful callback → Escrow hold. Until
  then, `CommissionConfiguration.get_deadline_activation_enabled()`
  (default `False` for every tenant) gates whether `PaymentDeadlineService
  .create_for_order()` schedules a live `apps.jobs` expiry job at all —
  the `PaymentDeadline` row is still recorded (data foundation for
  reporting/statements), but nothing can reopen a real order through the
  expiry cascade until a tenant is explicitly, platform-authorized-only
  enabled for it. `PaymentDeadlineService.expire_due()` re-checks the same
  gate independently, so a stale already-scheduled job cannot mutate order
  state through a since-disabled path.
- **Authorization was tenant-wide only (Major).** `CommissionContractService`'s
  four write actions now additionally pass a `scope_type="organization"`
  scope (resolved from the contract's company party) into the permission
  check, and independently enforce that the organization is `ACTIVE` and
  the caregiver holds a currently-`ACTIVE` `OrganizationMembership` with
  that exact organization — a suspended/ended affiliation can no longer
  create or activate a contract even if the acting user still holds a
  valid RBAC grant. `approve()`/`reject()` additionally verify the acting
  caregiver is the one actually named on the contract (an
  ownership-style check RBAC scope alone cannot express, since
  `organization_caregiver` is not, and is not expected to become,
  scoped to one specific caregiver).
- **No DB-level protection against concurrent duplicate proposals
  (Major).** `CommissionContract` now carries `uq_commcontract_open_pair`
  (at most one `DRAFT`/`PENDING_CAREGIVER_APPROVAL` row per
  `(tenant, company_party, caregiver_party)`) and
  `uq_commcontract_active_pair` (at most one `ACTIVE` row per pair), both
  conditional `UniqueConstraint`s added in migration `commission.0002`
  (additive — `0001_initial` was not rewritten). `approve()` now locks and
  supersedes *every* currently-`ACTIVE` row for the pair inside its own
  transaction, not only its recorded `supersedes` predecessor.
- **No DB-level 100% invariant (Major).** `CommissionContract` now carries
  `chk_commcontract_share_range` (each share in [0, 100]) and
  `chk_commcontract_shares_sum100`
  (`platform_share_percent = 100 - company_share_percent -
  caregiver_share_percent`), also in `commission.0002` — a direct-ORM
  write bypassing `CommissionContractService.propose()` entirely is still
  rejected by the database. `clean_total()` on the model remains
  documented dead code (no caller); the CheckConstraint is the real
  enforcement.
- **No `AuditClassification.FINANCIAL` audit trail for policy writes
  (Major).** `CommissionPolicyService.set_global_defaults()`/
  `set_cooperation_default()`/`set_platform_override()` now each write one
  `AuditService.log()` entry (previously only a plain `logger.info()`
  call existed), recording both the superseded version (if any) and the
  newly-activated one.
- **`_reset_demo()` orphaned `JobDefinition` rows (Major, independently
  discovered during the review's own adversarial 3×`--reset-demo` check).**
  Fixed by narrowly deleting only the demo tenant's own
  `commission.payment_deadline.expire` jobs before rebuilding — verified
  stable across 3 consecutive resets.
- **Minor/documentation:** the caregiver-override-precedence-over-company-
  override in `CommissionRuleResolver._resolve_platform_override()` is
  intentional (more specific grant wins) and is now documented at that
  call site; the resolver's hard-fallback-to-`DEFAULT_SHARES` path (no
  seeded `PolicyVersion` for a tenant) now logs a warning; `AssignmentService
  .cancel()` now cancels any still-`PENDING` `PaymentDeadline` for the
  order via `PaymentDeadlineService.cancel_for_order()`;
  `CommissionContractStatus.EXPIRED` remains reserved/unimplemented (no
  code path sets it — documented at the enum definition); the generic
  `PolicyDefinition.scope_id` tenant-integrity guarantee remains
  service-enforced, not FK-enforced (unchanged, pre-existing, out of
  scope); this repository still has no periodic production scheduler
  (cron/celery-beat/systemd-timer) configured to invoke `run_due_jobs` —
  confirmed still accurate at remediation time — so job execution
  requires a real scheduler/worker to be wired up before any
  gate-enabled tenant's deadline jobs actually run in production. A
  latent, unrelated bug was also found and fixed while implementing the
  membership-active check above: `apps.accounts.services.supplier_bridge
  .resolve_organization_supplier_for_caregiver()` filtered
  `OrganizationMembership.status` against `AffiliationStatus.APPROVED`
  ("approved") instead of the field's real `OrgMembershipStatus.ACTIVE`
  ("active") — since "approved" is never a real `OrganizationMembership
  .status` value, this silently returned `None` for every real (non-test)
  affiliated caregiver's company party, outside test fixtures that
  happened to reuse the same wrong constant.
