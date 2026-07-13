# ADR-012 — Financial Core PR-B: Real Escrow, Objection Period, Disputes & Partial Release

## Status

Accepted — Financial Core PR-B, built on the merged Financial Core PR-A
foundation (ADR-011: commission policy resolution, `CommissionContract`,
`CommissionSnapshot`, `PaymentDeadline`). PR-B stops short of multi-party
wallet settlement — that is Financial Core PR-C's scope (see "PR-C
Consumption Contract" below).

## Context

PR-A froze commission percentages and payment deadlines but left the actual
money flow untouched: a successful online payment still credited the
caregiver/company wallet immediately via `SettlementOrchestrationService`'s
Direct Settlement path (execution-first: assign → execute → invoice → pay →
settle). PR-B's objective is the opposite order for any tenant that opts in:
accepted proposal → pre-service payment → **Escrow hold** → service
completion → **objection period** → **dispute handling** → partial/full
release *instructions* — with real multi-party wallet settlement explicitly
deferred to PR-C.

A pre-existing `apps.finance.models.escrow.EscrowRecord`/`EscrowService`
scaffold (single `beneficiary_party`, `HELD`/`RELEASED`/`REFUNDED`/
`CANCELLED`) had zero real callers anywhere in the repository before PR-B —
confirmed by inspection. It was extended in place rather than replaced by a
second, competing model.

## Decision — Escrow as a beneficiary-less pool; PR-C owns allocation

**Escrow holds money, it does not allocate it.** The extended
`EscrowRecord` has no single `beneficiary_party` for its PR-B fields —
multi-party allocation (platform/company/caregiver shares, computed from
the frozen `CommissionSnapshot` via PR-A's `AllocationCalculator`) and the
actual wallet credit are PR-C's job. PR-B only ever produces immutable
`ReleaseInstruction`/`RefundInstruction` rows; it never credits a wallet
itself. This is the central design decision the rest of this document
follows from.

**Every PR-B monetary field is an integer count of whole Rials**
(`PositiveBigIntegerField`, no fractional subunit) — a deliberate,
localized departure from the surrounding Decimal-based finance/payments/
pricing models, matching `AllocationCalculator`'s own "deterministic
integer-IRR" convention. The conversion boundary is
`PreServicePaymentService._to_irr()`, which truncates a Decimal
Quote/invoice total into an int at the point a `PaymentIntent` is created.

### Pre-service payment flow

`PreServicePaymentService.create_invoice_and_intent_for_order()` is called
from `AssignmentService._open_financial_core_for_assignment()` — the same
integration point PR-A already uses for `CommissionSnapshot`/
`PaymentDeadline` — immediately after `PaymentDeadlineService
.create_for_order()`, gated behind `CommissionConfiguration
.get_preservice_payment_enabled()` (default **disabled** for every tenant).
It resolves an amount (prefers an existing `Quote` already linked to the
order, else `QuoteService.generate_quote()` — no price is ever fabricated;
`PricingError` propagates as `PreServicePaymentError`), issues a
pre-service invoice via a new `FinancialDocumentService
.create_preservice_invoice_for_order()` (reuses the existing private
`_create_document()` helper with `execution_session=None`), and creates a
`PaymentIntent` whose `idempotency_key` is `f"preservice:{deadline.id}"` —
**tied to the exact `PaymentDeadline` for this assignment cycle, not the
order alone**. This is the load-bearing detail behind every "new
assignment cycle gets a new snapshot/deadline/invoice/intent" and "a late
callback must never revive an expired assignment" guarantee below.

The intent carries `metadata["financial_core_flow"] = "preservice"`, which
`SettlementOrchestrationService.settle_payment_intent()` checks (alongside
`CommissionConfiguration.get_escrow_production_enabled()`) to route to
`_settle_preservice_to_escrow()` instead of the legacy Direct Settlement
path — recording a `PaymentTransaction` with the platform party as
receiver (no wallet credit, no ledger entries, no `PaymentSettled`/
`ProviderEarningsCredited` events, since those would be factually wrong),
then calling `EscrowIntegrationService.handle_preservice_payment_succeeded()`.

**`EscrowIntegrationService` looks up the `PaymentDeadline` by its exact ID**
(carried in `intent.metadata["payment_deadline_id"]`), never "whichever
deadline is currently PENDING for this order." If that deadline is
`PENDING`, it is marked `COMPLETED` (cancelling its expiry sweep) and the
Escrow is held. If it is anything else (`EXPIRED`/`CANCELLED` — a newer
assignment cycle has superseded it), the hold is refused with a
`PreServicePaymentError` and a `commission.escrow.hold_rejected_stale_cycle`
FINANCIAL audit record — no Escrow is created, and the payment requires
manual review. This is what makes a late/stale callback unable to revive an
expired assignment. A duplicate callback (same `provider_event_id`) is a
pure idempotent replay at the `PaymentCallbackService` layer; a second call
to `handle_preservice_payment_succeeded()` for the same intent short-circuits
on `EscrowRecord`'s own `idempotency_key = f"preservice-hold:{intent.id}"`.

`ExecutionPaymentGuardService.assert_can_start_execution()` is a no-op for
any tenant with the gate disabled (preserving exact legacy behavior);
otherwise it requires a HELD/PARTIALLY_RELEASED/PARTIALLY_REFUNDED Escrow to
exist for the order before `ExecutionService.start_session()` proceeds —
enforced at the service layer, not a disabled UI button.

### Escrow state model and invariants

States: `HELD`, `PARTIALLY_RELEASED`, `FULLY_RELEASED`,
`PARTIALLY_REFUNDED`, `FULLY_REFUNDED`, `CLOSED` (plus the legacy scaffold's
unused `RELEASED`/`REFUNDED`/`CANCELLED`, kept dead for backward
compatibility). Fields: `original_amount_irr`, `held_amount_irr`,
`releasable_amount_irr`, `blocked_amount_irr`, `released_amount_irr`,
`refunded_amount_irr`, `remaining_amount_irr`.

Two DB-level `CheckConstraint`s (not just service-layer checks) hold at all
times:

```
original_amount_irr = released_amount_irr + refunded_amount_irr
                     + blocked_amount_irr + remaining_amount_irr   -- chk_escrow_conservation
held_amount_irr = blocked_amount_irr + remaining_amount_irr         -- chk_escrow_held_derived
releasable_amount_irr <= remaining_amount_irr                       -- chk_escrow_releasable_within_remaining
```

`held_amount_irr` and `releasable_amount_irr` are deliberately **not** part
of the four-term conservation identity: `held_amount_irr` is the total
still parked in Escrow (disputed or not — `blocked + remaining`);
`releasable_amount_irr` is an auxiliary subset-of-`remaining` tracker (the
portion cleared for release but not yet consumed by a `ReleaseInstruction`).
A remediation caught during PR-B's own implementation: `apply_release()`/
`apply_refund()` originally decremented `remaining_amount_irr` without also
decrementing `held_amount_irr`, violating `chk_escrow_held_derived` the
first time money actually left Escrow — fixed before this branch's tests
were accepted as passing.

Movements are append-only (`EscrowMovement.save()`/`delete()` raise on any
non-insert), one row per real balance change, each carrying a before/after
JSON state snapshot, actor, correlation ID, idempotency key, and reason —
created in the same transaction as the `EscrowRecord` field update. Types:
`HOLD`, `MARK_RELEASABLE`, `BLOCK_FOR_DISPUTE`, `UNBLOCK`, `RELEASE`,
`REFUND`, `ADJUSTMENT` (reserved, unused). Every mutating `EscrowService`
method (`hold_for_order`, `mark_releasable`, `block_for_dispute`, `unblock`,
`apply_release`, `apply_refund`) is idempotent per `(tenant,
idempotency_key)`, uses `select_for_update()`, and writes exactly one
movement plus one `AuditClassification.FINANCIAL` audit record.

### Objection period state machine

`ObjectionPeriod` states: `NOT_STARTED` (unused — rows are created already
`OPEN`), `OPEN`, `CUSTOMER_APPROVED`, `AUTO_APPROVED`, `DISPUTED`, `CLOSED`
(reserved, unused). Started by `ObjectionPeriodService
.start_for_completion()`, called from a new `ExecutionService
._start_objection_period_if_applicable()` hook wired into `close_session()`
— idempotent per Escrow (a retried `close_session()` returns the existing
period). No-op if the tenant's preservice-payment gate is disabled. If
enabled but no HELD/PARTIALLY_* Escrow exists (an inconsistency the
start-time execution guard should already have prevented), it fails safely:
logs a `commission.objection.start_skipped_no_escrow` FINANCIAL audit and
returns without blocking the already-committed session/order closure — it
never fabricates an ObjectionPeriod or an Escrow.

The deadline is `now + CommissionConfiguration.get_objection_period_seconds()`
(default 3 days, independently configurable per tenant, separate from the
automation on/off gate). If `get_objection_automation_enabled()` is on, an
`OBJECTION_PERIOD_AUTO_APPROVE` job (`apps.jobs`) is scheduled for that
deadline and its `JobDefinition.id` recorded on the row so `extend()` can
reschedule it later.

`approve_by_customer()` — ownership-checked (only the order's own customer;
no RBAC permission_key, matching the portal's documented
no-RBAC-for-customer-self-service convention) — and `auto_approve_if_due()`
— the scheduled job's body, restricted to pure `OPEN` status only (a
`DISPUTED` period requires human resolution, never auto-approval) — both
converge on the same `_release_undisputed_amount()` helper: it marks the
Escrow's entire current `remaining_amount_irr` releasable
(`EscrowService.mark_releasable()`) and immediately creates one
`ReleaseInstruction` for it (`ReleaseInstructionService.create()`), all in
the same transaction. This two-step sequence (MARK_RELEASABLE movement,
then a RELEASE movement via the instruction) satisfies the data model's
distinct-movement-type requirement while keeping the user-facing action a
single click.

`extend()` requires `COMMISSION_OBJECTION_EXTEND` (platform-only,
`platform_scope=True`) and a non-empty reason, reschedules the pending
auto-approve `JobDefinition` in place, and records an append-only
`ObjectionPeriodExtension` row — the same pattern as PR-A's
`PaymentDeadlineExtension`.

### Dispute model and partial-blocking invariant

`Dispute`: exact `disputed_amount_irr`, `reason_code`
(`DisputeReasonCode`), free-text `description`, `evidence_metadata`,
customer/supplier `FinancialParty` references, `status`
(`OPEN`/`UNDER_REVIEW`/`PARTIALLY_RESOLVED`/`RESOLVED`/`REJECTED`/
`CANCELLED`). `DisputeLine` optionally breaks the amount down against
specific `FinancialDocumentItem` rows.

`DisputeService.open()` — gated behind `get_dispute_release_enabled()`,
ownership-checked exactly like objection approval, idempotent — validates
`disputed_amount_irr > 0` and `<= escrow.remaining_amount_irr` (the
correct disputable ceiling, since already-blocked money is excluded from
`remaining` by construction), validates any given lines sum to the total
and belong to the same invoice/tenant, then calls `EscrowService
.block_for_dispute()` (one `BLOCK_FOR_DISPUTE` movement: `blocked_amount_irr
+= amount`, `remaining_amount_irr -= amount`, `releasable_amount_irr =
min(releasable, remaining)`) and — if an `OPEN` `ObjectionPeriod` exists for
the same Escrow — transitions it to `DISPUTED`.

**Worked example (the canonical PR-B partial-blocking proof, exercised
verbatim in `apps.commission.tests.test_dispute_flow
.test_exact_worked_example_partial_block`):** original 10,000,000 IRR,
disputed 1,543,000 IRR → `blocked_amount_irr = 1,543,000`,
`remaining_amount_irr = 8,457,000`, conservation identity holds
throughout. A duplicate dispute command with the same `idempotency_key`
never double-blocks (short-circuits on `EscrowMovement` idempotency);
concurrent creation is serialized by `select_for_update()` on the Escrow
row plus the DB-level conservation constraint as a last-resort guard.

`Dispute.resolve()` is not implemented as a per-line, incremental process
in PR-B — `DisputeResolutionService.resolve()` always allocates the
dispute's **entire** `disputed_amount_irr` in one call. `PARTIALLY_RESOLVED`
is defined on the enum but no code path ever sets it — a deliberate MVP
simplification, documented here as a known limitation (see the PR's final
report), not a bug to silently work around.

### Resolution, release instructions, and the PR-C consumption contract

`DisputeResolutionService.resolve()` requires `COMMISSION_DISPUTE_RESOLVE`
(platform-only), validates that
`customer_refund_amount_irr + platform_amount_irr + company_amount_irr +
caregiver_amount_irr` sums to exactly `dispute.disputed_amount_irr` (also a
DB-level `CheckConstraint`, `chk_disputeres_conservation`, on the immutable,
append-only `DisputeResolution` row), then: creates the `DisputeResolution`
first, `EscrowService.unblock()`s the full disputed amount back into
`remaining`, and conditionally creates one `RefundInstruction` (if
`customer_refund_amount_irr > 0`) and/or one `ReleaseInstruction` (if the
platform+company+caregiver total is > 0) against that now-unblocked amount.
The Dispute is marked `RESOLVED` with a derived label
(`FULL_REFUND`/`FULL_RELEASE`/`MIXED`).

`ReleaseInstruction` (`PENDING_ALLOCATION`/`READY`/`CONSUMED`/`CANCELLED`) is
the canonical, immutable record PR-C is required to consume: tenant,
escrow, order, invoice, `commission_snapshot` (the frozen PR-A snapshot —
**PR-B never recomputes current commission configuration**),
`gross_releasable_amount_irr`, source
(`CUSTOMER_APPROVAL`/`AUTO_APPROVAL`/`UNDISPUTED_PARTIAL`/
`DISPUTE_RESOLUTION`), `idempotency_key`, `correlation_id`. It is created
`READY` (not `PENDING_ALLOCATION` — allocation math is PR-C's job, not a
state PR-B ever occupies) and is expected to transition to `CONSUMED` only
by PR-C, which is also the only code allowed to perform the actual
multi-party wallet credit (via PR-A's `AllocationCalculator` against the
referenced `commission_snapshot`). One `ReleaseInstruction` per exact
release event — never a running total, never mutated after creation.

### Held-Escrow refund boundary

`RefundInstruction` (`PENDING`/`INITIATED`/`COMPLETED`/`FAILED`) represents
money that never left Escrow being returned to the customer — distinct from
a post-settlement clawback (no wallet has ever been credited for PR-B
money, so there is nothing to claw back; that mechanism is reserved for
PR-E). `RefundInstructionService.create()` calls `EscrowService
.apply_refund()` in the same transaction as the instruction row.
`.initiate()` is the only place PR-B calls out to a PSP adapter — the Fake
provider's new `refund_payment()` classmethod (a pure, deterministic,
in-memory simulation, mirroring `request_payment()`'s shape) — and is
**synchronous and Fake-only**: there is no real async PSP refund-callback
path in PR-B, documented as a limitation.

### Cancellation-before-release boundary

`CancellationEscrowService.handle_cancellation()` implements only the
minimum safe behavior Section 17 requires: a no-op for an unpaid
cancellation (no Escrow exists) or when nothing remains un-blocked/
un-released (`remaining_amount_irr <= 0`); a full refund of the remaining
amount when the dispute/release gate is enabled; and, when that gate is
disabled, a `commission.cancellation.requires_manual_review` FINANCIAL
audit with **no** `RefundInstruction` created (never silent, never a
fabricated shortcut). The full cancellation rule engine (time-window
penalties, partial-compensation policies) is explicitly reserved for PR-E —
PR-B never invents one.

### Feature gates and legacy safety

Five independently-configurable, tenant-scoped gates, all defaulting
**disabled** (`CommissionConfiguration`, `apps.commission.services
.configuration`): `PRESERVICE_PAYMENT_ENABLED_KEY`,
`ESCROW_PRODUCTION_ENABLED_KEY`, `OBJECTION_AUTOMATION_ENABLED_KEY`,
`DISPUTE_RELEASE_ENABLED_KEY` (booleans), and
`OBJECTION_PERIOD_SECONDS_KEY` (a duration, independent of the automation
on/off switch). The pre-existing `FinanceConfiguration.ESCROW_ENABLED_KEY`
(`financial.escrow.enabled`, default `True`, historically inert — the
legacy `SettlementOrchestrationService` only ever warned and bypassed it)
is deliberately left untouched and unused by PR-B, to avoid silently
changing behavior for any tenant that might already have it explicitly
set.

A tenant that never opts in sees **exactly** pre-PR-B behavior: no
pre-service invoice/intent, no Escrow, no objection period, no execution
guard, no false claim that money is held when it never was — direct
verification in `apps.commission.tests.test_pr_b_feature_gates`.

**A real, confirmed cross-cutting constraint discovered while extending
`seed_product_walkthrough`:** these gates are tenant-wide, not per-order.
A tenant that enables `preservice_payment` blocks *every* order in that
tenant from starting execution without a HELD Escrow — including
pre-existing legacy execution-first orders that never went through the
pre-service flow. The walkthrough seed command works around this by
driving the legacy-flow demo orders' execution to completion *before*
enabling the PR-B gates for its dedicated demo tenant, and by resetting
those gates (deleting the tenant's `ConfigurationValue` rows) as part of
`--reset-demo` so repeated resets stay ordering-safe. Any tenant migrating
from the legacy flow to PR-B in production must account for this: enabling
`preservice_payment` is an all-or-nothing switch for that tenant's *new*
assignment cycles going forward, not a per-order opt-in.

### Reconciliation (read-only)

`EscrowReconciliationService.check_escrow()`/`check_tenant()` verify, per
Escrow: captured payment amount equals `original_amount_irr`; the four-term
conservation identity; open-dispute total equals `blocked_amount_irr`;
sum of `ReleaseInstruction` amounts does not exceed `released_amount_irr`;
sum of `RefundInstruction` amounts does not exceed `refunded_amount_irr`.
It returns a frozen `ReconciliationResult(ok, discrepancies: list[str])` and
**never auto-corrects** — a discrepancy is a bug to investigate, not data to
silently normalize.

## Consequences

- PR-B is additive at the schema level: two new migrations
  (`commission.0003`, `finance.0003`), no rewrite of any PR-A migration.
- Legacy direct-settlement records are never retroactively reclassified
  into Escrow — old `PaymentTransaction`/settlement rows remain exactly as
  they were, implicitly "legacy direct-settlement" by the simple fact that
  no Escrow references them.
- PR-C's contract is now concrete: consume `ReleaseInstruction` rows
  (`READY` → `CONSUMED`), perform the actual multi-party wallet credit
  against the referenced `commission_snapshot`, and nothing else — PR-B's
  own `EscrowService.apply_release()` has already moved the money out of
  `remaining_amount_irr` by the time a `ReleaseInstruction` exists.
- Known, deliberately out-of-scope for PR-B (reserved for PR-C–PR-F, per
  the originating instructions): final multi-party wallet settlement,
  platform/company/caregiver wallet credits, complete cash clearing, the
  full extra-invoice engine, the full cancellation rule engine,
  post-settlement clawback, real bank payouts, complete financial
  reporting.
- Known implementation gaps, not yet built: provider/company notification
  fan-out for PR-B domain events (every event currently notifies only the
  order's customer — see `apps.kernel.events.base`'s PR-B section);
  `DisputeStatus.PARTIALLY_RESOLVED` is unreachable; multiple *overlapping*
  disputes against the same Escrow amount are prevented by the disputable-
  ceiling check but a dedicated multi-dispute non-overlap test matrix was
  not exhaustively built.
