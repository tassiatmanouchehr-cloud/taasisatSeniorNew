# Financial Core Implementation Plan

Status: PR-A delivered. PR-B through PR-F not yet started.

This document is the permanent record of the System Architect's frozen
Financial Core business model and the dependency-ordered PR sequence
required to implement it. Per the System Architect's explicit instruction,
it must remain recorded here so later phases cannot forget any requirement
— this is a checklist/reference document, not a status report; update the
checkboxes as each PR lands, do not delete completed items.

## PR sequence (dependency-ordered)

- [x] **PR-A — Financial policy, party roles, configuration, contracts,
  snapshots, arithmetic, and payment-expiry foundation.** Delivered on
  branch `claude/module-05-financial-ops-fmbfks`. See ADR-011 and the PR-A
  final report for full detail.
- [ ] **PR-B — Real escrow, releasable balances, objection period, and
  disputes.**
- [ ] **PR-C — Multi-party allocation, ledger postings, wallet/receivable
  integration, and online settlement.**
- [ ] **PR-D — Extra invoices, line discounts, coupons, goods/service
  policies, and cash payment clearing.**
- [ ] **PR-E — Refund engine, cancellation financial integration,
  reversals, and debt recovery.**
- [ ] **PR-F — Reconciliation, closing readiness, reporting, statements,
  administrative financial visibility, and test walkthrough.**

Each PR must be independently reviewable, must not be merged without
Architecture Review, and must not combine documentation-only
repository-state synchronization with implementation changes.

## Non-negotiable actors and terminology (binding for every PR)

Five financial actors: Manouchehr/Platform, Customer, Independent
Caregiver, Company, Company-Affiliated Caregiver. A single financial
transaction may have multiple beneficiaries. Never use a caregiver's
*current* affiliation when reproducing *historical* financial behavior —
always read the frozen `CommissionSnapshot` for that order.

## Final default commission policies (owner-decided, not assumptions)

| Cooperation type | Platform | Company | Caregiver |
|---|---:|---:|---:|
| Independent caregiver | 20% | 0% | 80% |
| Company-affiliated caregiver | 7% | 13% | 80% |
| Company as direct supplier | 7% | 93% | 0% |
| Goods (independent of the above) | 0% | 0% | 100% |

All four are seeded defaults (`seed_commission_defaults` management
command), reconfigurable via `CommissionPolicyService`, never permanent
hardcoded constants. Every set must sum to exactly 100 (enforced by
`validate_shares`/`validate_global_payload`).

## Policy priority (binding for every PR)

1. Active approved Company–Caregiver `CommissionContract`
2. Platform-specific override for the applicable caregiver/company
3. Cooperation-type default
4. Global default

Resolved once at proposal/offer acceptance and frozen into an immutable
`CommissionSnapshot` — later configuration changes must never affect an
already-snapshotted order. See ADR-011 for the full resolution
architecture and `apps.commission.services.resolver_service
.CommissionRuleResolver` for the implementation.

## Full business-model requirements checklist (for PR-B onward to consume)

The complete, verbatim business specification the System Architect
provided for this Financial Core (order payment deadline, escrow,
commission policy, configuration, priority, snapshot, extra invoice,
discount, goods, service extra, cash payment, online payment, refunds,
disputes, account statements, ledger, reports, audit, authorization,
tenant isolation, idempotency/concurrency, migration/legacy-data strategy)
is preserved verbatim in this repository's session history and in the
PR-A pull request description. Sections not yet implemented, with their
target PR:

- **Order payment deadline cascade** (accepted → deadline → expiry →
  reopen): **PR-A delivered** — `apps.commission.models.deadline
  .PaymentDeadline`, `PaymentDeadlineService`, the
  `commission.payment_deadline.expire` job,
  `AssignmentService.expire()`.
- **Order price immutability, staged/partial payment readiness**: not yet
  addressed — `apps.orders.Order` has no price field at all yet (pricing
  lives in `apps.pricing`/`apps.finance`, resolved later than assignment
  time). Target: PR-C, when the Quote-to-Order pricing bridge is designed.
- **Real escrow in the production payment path, objection period,
  auto-approval**: PR-B.
- **Partial dispute blocking, exact-invariant accounting**: PR-B.
- **Multi-party ledger/wallet allocation for real settlement**: PR-C.
  `SettlementAdjustmentPipeline` (`apps.payments.services
  .settlement_adjustments`) remains untouched by PR-A — it must be
  replaced, not extended in place, per the prior audit's finding that it
  is currently a hardcoded identity function; PR-C is where
  `CommissionRuleResolver`'s output actually reaches `LedgerService
  .post_entries()`.
- **Extra invoices with line discounts, goods/service mixed policy,
  coupons, gateway-fee/platform-loss accounting**: PR-D.
- **Cash payment declaration, caregiver central-clearing debt, netting**:
  PR-D.
- **Refund Rule Engine, cancellation-to-finance integration,
  post-settlement clawback groundwork**: PR-E.
- **Five-actor account statements, reconciliation, closing readiness,
  full financial reporting, operator/customer/caregiver/company UI
  surfaces**: PR-F.

## Canonical services PR-B onward must reuse (do not re-implement)

- `apps.commission.services.resolver_service.CommissionRuleResolver` —
  the only place that resolves an effective commission rate.
- `apps.commission.services.snapshot_service.CommissionSnapshotService` —
  the only place that creates a `CommissionSnapshot`.
- `apps.commission.services.allocation_calculator.AllocationCalculator` —
  the only place that turns a base amount + rates into conserved integer-
  IRR allocation lines (residual to caregiver).
- `apps.commission.services.contract_service.CommissionContractService` —
  the only place that transitions a `CommissionContract`.
- `apps.finance.services.ledger_service.LedgerService` /
  `apps.wallet.services.wallet_transaction_service.WalletTransactionService`
  — unchanged by PR-A, remain the canonical ledger/wallet write paths.

## Explicitly out of scope for PR-A (do not assume done)

Real escrow release, multi-party wallet crediting, cash clearing, refund,
full UI statements, reconciliation, closing readiness, and any change to
`SettlementOrchestrationService`'s real money-movement behavior. See the
PR-A final report's "known limitations reserved for PR-B onward" for the
complete, itemized list with file:line references.
