# Wallet / Finance / Payments Boundary

Status: current as of Module 18. Three things in this codebase are easy to
conflate because they're all "about money." This document is the
disambiguation reference. See ADR-004 and ADR-005 for the decisions
behind this, and `wallet-finance-boundary.md`'s cousin, `api-guidelines
.md`, for how the API layer respects it.

## The three things

| | Owns | Nature | Status |
|---|---|---|---|
| `apps.wallet.Wallet`/`WalletTransaction` | Internal stored value (customer credits, refunds-to-wallet, promotions) | A cached balance + append-only transaction ledger | **Canonical**, active |
| `apps.finance.models.wallet.WalletAccount`/`WalletTransaction` | The same *shape* of thing, built first (Module 05) | Identical pattern, but coupled to `FinancialDocument`/`PaymentTransaction` and publishes a DomainEvent on every mutation | **Legacy/frozen** — see below |
| `apps.payments.PaymentIntent`/`PaymentAttempt`/`PaymentCallback` | A gateway-facing request/callback state machine (CREATED→PENDING→AUTHORIZED/SUCCEEDED/FAILED/CANCELLED/EXPIRED) | Pre-settlement orchestration — "we're trying to collect a payment" | Active, but not wired to anything downstream yet |
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
        │  [NOT YET WIRED — see technical-debt-register.md]
        ▼
  finance.PaymentTransaction        ◄── apps.finance — post-hoc settlement
        │  (resolves FinancialObligation, marks FinancialDocument PAID)
        ▼
  ledger entries, settlement batches
```

A future orchestration module would call `PaymentService.record_payment()`
once a `PaymentIntent` reaches `SUCCEEDED` — deliberately not built yet
(Module 15 explicitly forbade wiring into Finance settlement; Module 17B
explicitly forbade it for the API layer too).

## No wallet mutation from the payment intent flow (yet)

`apps.payments` does not create `Wallet`/`WalletTransaction` rows on a
successful callback, and never has — tested explicitly
(`apps/payments/tests/test_no_side_effects.py`). Crediting a customer's
wallet from a successful payment is a real, expected future capability,
deliberately deferred to a dedicated orchestration module rather than
smuggled into either `PaymentCallbackService` or an API view.

## Guardrail

`apps/kernel/tests/test_architecture_guardrails.py`
(`NoDuplicateWalletModelTest`) asserts that the only two locations in the
codebase defining a model literally named `Wallet` or `WalletTransaction`
are `apps.wallet.models` (canonical) and `apps.finance.models.wallet`
(legacy, already known) — catching, at test time, any future accidental
reintroduction of a third wallet concept.
