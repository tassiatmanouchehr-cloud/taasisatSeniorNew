# Wallet / Finance / Payments Boundary

Status: current as of PR #26's merge (Epic 03 Sprint 1). Three things in
this codebase are easy to conflate because they're all "about money."
This document is the disambiguation reference. See ADR-004 and ADR-005
for the decisions behind this, and `wallet-finance-boundary.md`'s cousin,
`api-guidelines.md`, for how the API layer respects it.

## The three things

| | Owns | Nature | Status |
|---|---|---|---|
| `apps.wallet.Wallet`/`WalletTransaction` | Internal stored value (customer credits, refunds-to-wallet, promotions) | A cached balance + append-only transaction ledger | **Canonical**, active |
| `apps.finance.models.wallet.WalletAccount`/`WalletTransaction` | The same *shape* of thing, built first (Module 05) | Identical pattern, but coupled to `FinancialDocument`/`PaymentTransaction` and publishes a DomainEvent on every mutation | **Legacy/frozen** — see below |
| `apps.payments.PaymentIntent`/`PaymentAttempt`/`PaymentCallback` | A gateway-facing request/callback state machine (CREATED→PENDING→AUTHORIZED/SUCCEEDED/FAILED/CANCELLED/EXPIRED) | Pre-settlement orchestration — "we're trying to collect a payment" | Active; wired to settlement as of Epic 03 Sprint 1 — see below |
| `apps.finance.PaymentTransaction` | A settlement ledger row | Post-hoc — "a payment already happened, resolve the obligation/document" | Active, created only via `PaymentService.record_payment()` |

## Why the legacy Finance wallet still exists

Module 05 built `WalletAccount`/`WalletTransaction` as part of the initial
Finance foundation. By Module 14, nothing outside Finance's own tests had
ever created a `WalletAccount` row. When Module 14 built the real
customer-wallet requirements (overdraft config, idempotency, PROMOTION/
MANUAL transaction types, no coupling to Finance documents), the
architecturally correct choice was Option 1 from the Module 14 correction
report: standardize on `apps.wallet` as the one active implementation and
mark the Finance version legacy via docstring — not delete it (it still
has its own passing tests) and not refactor Finance (out of scope then and
now). See the docstrings on `apps/finance/models/wallet.py` and
`apps/finance/services/wallet_service.py` for the in-code marker.

**Rule for new code**: never call `apps.finance.services.WalletService`
(the legacy one). Always use `apps.wallet.services.WalletService`/
`WalletTransactionService`.

## Why PaymentIntent and finance.PaymentTransaction are both real and don't overlap

They sit at different points in the same conceptual timeline:

```
customer initiates payment
        │
        ▼
  PaymentIntent (CREATED)          ◄── apps.payments — pre-settlement
        │  start_attempt()
        ▼
  PaymentAttempt (PENDING)
        │  provider callback
        ▼
  PaymentIntent (SUCCEEDED/FAILED/...)
        │
        │  SettlementOrchestrationService.settle_payment_intent()
        │  (Epic 03 Sprint 1 — triggered from PaymentCallbackService
        │   after its own commit, SUCCEEDED + first-time only; a
        │   PaymentIntent row lock serializes concurrent attempts)
        ▼
  finance.PaymentTransaction        ◄── apps.finance — post-hoc settlement
        │  (resolves FinancialObligation, marks FinancialDocument PAID)
        ▼
  ledger entries (LedgerService.post_entries)
        ▼
  beneficiary Wallet credit (apps.wallet.WalletTransactionService)
```

`SettlementOrchestrationService` (`apps.payments.services`) is that
orchestration module — built in Epic 03 Sprint 1 (PR #26). It calls
`PaymentService.record_payment()` once a `PaymentIntent` reaches
`SUCCEEDED` and references an `Order`, exactly as anticipated. Sprint 1
is Direct Settlement only (escrow is read via `FinanceConfiguration.
get_escrow_enabled()` but always warns and falls back); every
commission/tax/discount adjustment is zero through the
`SettlementAdjustmentPipeline` extension point. Settlement never
fabricates a `FinancialDocument` — it resolves one already created via
`FinancialDocumentService.create_invoice_from_execution()`, and raises a
clear `SettlementError` if none exists yet for the order. If a
synchronous settlement attempt fails, a durable `payments.settlement.retry`
job is enqueued via `apps.jobs` rather than the failure only being logged.

## Wallet mutation from the payment intent flow

`apps.payments` now creates `finance.PaymentTransaction` rows and credits
the beneficiary's canonical `apps.wallet.Wallet` — but only through
`SettlementOrchestrationService`, and only for a `PaymentIntent` that
references an `Order` (`reference_type="Order"`) and has a resolvable
`FinancialDocument`. `apps/payments/tests/test_no_side_effects.py` guards
the narrower, still-true invariant: a callback for a *non-Order* intent
produces no wallet/`PaymentTransaction` side effects (settlement is
skipped, not silently faked), and the legacy `apps.finance.models.wallet`
is never touched by any payments flow. The full settle-and-credit path,
including concurrency and rollback-on-failure behavior, is covered by
`apps/payments/tests/test_settlement_orchestration.py`; the reporting
side (a settlement's effect actually reaching `apps.provider_portal`'s
earnings view) is covered by
`apps/provider_portal/tests/test_settlement_earnings_integration.py`.

## Guardrail

`apps/kernel/tests/test_architecture_guardrails.py`
(`NoDuplicateWalletModelTest`) asserts that the only two locations in the
codebase defining a model literally named `Wallet` or `WalletTransaction`
are `apps.wallet.models` (canonical) and `apps.finance.models.wallet`
(legacy, already known) — catching, at test time, any future accidental
reintroduction of a third wallet concept.
