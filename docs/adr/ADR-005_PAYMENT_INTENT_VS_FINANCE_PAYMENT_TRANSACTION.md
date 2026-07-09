# ADR-005 — PaymentIntent (Payments) vs PaymentTransaction (Finance)

## Status

Accepted — Module 15, reaffirmed in Module 18.

## Context

`apps.finance.models.payment.PaymentTransaction` (Module 05) already
existed when Module 15 (Payment Gateway Integration) began: an internal,
append-only record of money movement, created only via
`PaymentService.record_payment(...)`, always constructed in a single
terminal status (default `SUCCEEDED`), immediately resolving a
`FinancialObligation`/`FinancialDocument`. It even has a
`provider_reference` field and `PaymentMethod.ONLINE` — evidence a
PSP-facing flow was anticipated but never built around it.

Module 15 needed something structurally different: a multi-step
orchestration state machine (create an intent → start a provider attempt
→ receive and validate a callback → transition through CREATED → PENDING
→ AUTHORIZED/SUCCEEDED/FAILED/CANCELLED/EXPIRED) with idempotent
creation, idempotent callback handling, and a durable audit trail of
every callback payload (accepted or rejected) — none of which
`finance.PaymentTransaction`'s single-shot, already-succeeded shape could
represent.

## Decision

Build `apps.payments.PaymentIntent`/`PaymentAttempt`/`PaymentCallback` as
a **new, separate, upstream** bounded context — not a duplicate of
`finance.PaymentTransaction`, but its logical predecessor in the payment
lifecycle:

```
PaymentIntent/PaymentAttempt   (apps.payments — pre-settlement, gateway-facing)
        │  [deferred — no code exists yet]
        ▼
finance.PaymentTransaction      (apps.finance — post-hoc, settlement ledger)
```

`apps.payments` never creates a `finance.PaymentTransaction`, a
`Wallet`/`WalletTransaction`, or a `FinancialDocument` row. It has no
runtime dependency on `apps.finance` beyond reading `FinancialParty` (the
existing generic financial-counterparty abstraction, reused rather than
duplicated — the same pattern `apps.wallet` already established).

## Consequences

- Two payment-shaped entities exist without overlapping: `PaymentIntent`
  answers "are we trying to collect this payment, and what state is that
  attempt in," `finance.PaymentTransaction` answers "did money definitely
  move, and what obligation does it resolve." A future orchestration
  module would call `PaymentService.record_payment()` once a
  `PaymentIntent` reaches `SUCCEEDED` — deliberately not built now.
- `apps.api`'s payments endpoints (Module 17B) confirm the boundary held:
  `POST /api/v1/payments/intents/` and its attempt/callback siblings only
  ever touch `apps.payments`, never `apps.finance`.
- See `docs/architecture/wallet-finance-boundary.md` for the full picture
  including the wallet side of this triangle.
