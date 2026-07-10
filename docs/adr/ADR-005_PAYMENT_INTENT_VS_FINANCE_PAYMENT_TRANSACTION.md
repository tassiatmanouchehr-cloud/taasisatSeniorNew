# ADR-005 — PaymentIntent (Payments) vs PaymentTransaction (Finance)

## Status

Accepted — Module 15, reaffirmed in Module 18. The bridge named as
deferred in this ADR's Consequences was built in Epic 03 Sprint 1 — see
the Update note at the end of this document.

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

## Update — Epic 03 Sprint 1 (Financial Settlement & Money Flow)

The "future orchestration module" named above is now
`apps.payments.services.SettlementOrchestrationService`, invoked from
`PaymentCallbackService.process_callback()` once its own atomic block has
committed and the intent has genuinely reached `SUCCEEDED` (never on an
idempotent replay). It lives inside `apps.payments` (not a new app),
consistent with `dependency-graph.md`'s existing `payments (→ finance,
wallet)` edge — this decision did not require inverting that graph. It
does call `PaymentService.record_payment()`, `LedgerService.
post_entries()`, and `apps.wallet.services.WalletTransactionService.
credit()` on a `SUCCEEDED` `PaymentIntent`, exactly as anticipated above.
`apps.payments` still never creates a `FinancialDocument` — settlement
resolves an already-created document (via
`FinancialDocumentService.create_invoice_from_execution()`, called
elsewhere), it does not fabricate one. See
`docs/architecture/DECISION_HISTORY.md` for the full set of decisions
made in this sprint, and `SettlementOrchestrationService`'s own docstring
for the exact money-flow sequence.
