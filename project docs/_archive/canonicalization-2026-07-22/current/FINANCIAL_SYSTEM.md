# FINANCIAL SYSTEM AS-IS

**Last verified HEAD:** a5dbaf28703142edaa1d770ea8f3c2a45a12640f (full audit) / partial
update 2026-07-15 (phase2-caregiver-professional-dashboard, PR #9 merged) — only the new
"Caregiver-Facing Read Paths" section added; no change to any existing section above /
re-confirmed unchanged 2026-07-15 (phase2-caregiver-public-profile-finalization, Sprint 2.6
— no financial logic touched; bonus/penalty gap re-confirmed still unresolved, KL-020)
**Last verified date:** 2026-07-14 / 2026-07-15 (partial, Sprint 2.5) / 2026-07-15
(re-confirmed, Sprint 2.6)

---

## Financial Architecture

### Money Representation

Canonical: `DecimalField(max_digits=14, decimal_places=2)` with `DEFAULT_CURRENCY="IRR"` throughout. Used in: Quote, FinancialDocument, PaymentIntent, Wallet, WalletTransaction, EscrowRecord (PR-B fields use PositiveBigIntegerField for IRR amounts).

### Financial Party Abstraction

`finance.FinancialParty` is the universal financial counterparty. Type enum: CUSTOMER, SUPPLIER, ORGANIZATION, PLATFORM. Linked to domain entities via `linked_entity_type` + `linked_entity_id` (generic FK pattern).

### Financial Document Chain

```
FinancialDocument (invoice/credit note)
├── FinancialDocumentItem (line items)
├── FinancialObligation (payment obligations)
├── PaymentTransaction (settlement ledger)
├── LedgerEntry (double-entry accounting)
└── EscrowRecord (held funds)
```

## Payment Flow

### Current State: MOCKED PSP

`PaymentProviderRegistry` registers only `FakePaymentProviderAdapter`. No real PSP (Zarinpal, Mellat, Stripe) is implemented.

### PaymentIntent Lifecycle

```
CREATED → PENDING → SUCCEEDED / FAILED / EXPIRED / CANCELLED
```

`PaymentIntentService.create_intent()` creates idempotent intents. `start_attempt()` calls the adapter. `process_callback()` handles provider responses and triggers settlement.

### Settlement

`SettlementOrchestrationService.settle_payment_intent()` on SUCCEEDED:
1. Creates `Wallet` (get_or_create)
2. Credits wallet via `WalletTransactionService.credit()`
3. Idempotent via `idempotency_key=f"settlement:{intent.id}"`
4. On failure: enqueues `payments.settlement.retry` job

## Escrow System (PR-B)

### Production Path (7 methods)

| Method | Purpose | State Change |
|--------|---------|-------------|
| `hold_for_order()` | Create HELD escrow after preservice payment | → HELD |
| `mark_releasable()` | Move remaining → releasable after service completion | remaining ↓, releasable ↑ |
| `block_for_dispute()` | Move remaining → blocked for open dispute | remaining ↓, blocked ↑ |
| `unblock()` | Return blocked → remaining after dispute resolution | blocked ↓, remaining ↑ |
| `apply_release()` | Consume remaining → released | remaining ↓, released ↑ |
| `apply_refund()` | Consume remaining → refunded | remaining ↓, refunded ↑ |

### Conservation Equation

```
original_amount = held + remaining + releasable + blocked + released + refunded
```

Enforced by 3 CheckConstraints on EscrowRecord.

## Commission System

### CommissionContract

Bilateral versioned agreement between company_party and caregiver_party. Statuses: DRAFT, PROPOSED, ACTIVE, SUPERSEDED, REJECTED, CANCELLED. UniqueConstraints enforce one OPEN and one ACTIVE contract per pair.

### CommissionSnapshot

Created at assignment time. Freezes the resolved commission policy for the order. Referenced by DisputeResolution, ReleaseInstruction, RefundInstruction.

### ObjectionPeriod

Created after service completion when preservice payment is enabled. Window for customer to raise disputes. Auto-approves after configurable period.

## Wallet System

### Wallet

`Wallet` model: per (tenant, party, currency). Balance cached, recalculated from transactions.

### WalletTransaction

6 types: CREDIT, DEBIT, REFUND, PROMOTION_CREDIT, ADJUSTMENT, MANUAL_ADJUSTMENT. All mutations go through `_apply()` with row lock, idempotent dedup, and insufficient funds check.

## Legacy Wallet (finance.WalletAccount)

`finance.WalletAccount` and `finance.WalletTransaction` exist in `apps/finance` but are documented as legacy/frozen. The canonical wallet is `apps.wallet`. See `11_DUPLICATION_AND_SOURCE_OF_TRUTH_REGISTER.md`.

## Caregiver-Facing Read Paths (Sprint 2.5, 2026-07-15)

The Caregiver Professional Dashboard (`apps.provider_portal`) reads, but does not
calculate, financial state — no new money representation, no new financial document type,
no new wallet transaction type. It reuses:

- `WalletService.get_wallet_or_none()` + `WalletTransactionService.list_transactions()`
  (both pre-existing) for the available balance and recent movements.
- A new `FinancialDocumentService.list_for_beneficiary_party()`/
  `count_by_status_for_beneficiary_party()` pair — the `beneficiary_party` side of the same
  `FinancialDocument` model `list_for_payer_party()` already reads for customers; not a new
  document type or status.

**Bonus/penalty is not modeled anywhere in this repository** — confirmed by inspection
(no dedicated model/field, and `WalletTransactionType`'s 6 values carry no bonus/penalty
semantic). The dashboard documents this gap explicitly (`FinancialOverviewViewModel
.bonus_penalty_note`) rather than inventing a classification. See
`traceability/ARCHITECTURE_DECISION_LOG.md` ADM-021.
