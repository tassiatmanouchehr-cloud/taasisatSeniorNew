# Generic Service Marketplace Framework

**Module 05 — Financial Operations, Ledger, Wallet & Settlement Engine**

| | |
|---|---|
| **Version** | 1.0 |
| **Status** | Frozen |
| **Document Owner** | Product Architecture |
| **Project** | Generic Service Marketplace Framework Reference Implementation (reference implementation of the Generic Service Marketplace Framework) |
| **Module Owner** | Platform Owner |
| **Depends On** | Module 01 — Request Engine, Module 02 — Matching Engine, Module 03 — Booking, Assignment & Service Activation Engine, Module 04 — Service Execution & Session Lifecycle Engine |
| **Next Modules** | Quality, Dispute, Reporting, Accounting/ERP Integration, Banking/PSP Adapters |
| **Language** | Persian business domain, English technical structure |

> Modules 01–04 are Frozen and Approved and are treated as baseline. Module 05 must not change their operational decisions unless a major architectural conflict is discovered.

> **Architecture Notice:** the project is a **Generic Service Marketplace Framework** with **Generic Service Marketplace Framework Reference Implementation** as the first reference implementation. Every section states the Core Platform pattern first, then its reference implementation mapping where useful.

# 07 — State Machines

## Commercial Contract State

```text
OFFER_ACCEPTED
 → RESERVATION_CREATED
 → PAYMENT_PENDING
 → PAID
 → CONTRACT_ACTIVE
 → OPERATIONALLY_COMPLETED
 → FINANCIALLY_CLEARED
 → CLOSED
```

Exception states: PAYMENT_EXPIRED, CANCELLED_BEFORE_SERVICE, CANCELLED_DURING_SERVICE, REFUND_PENDING, FINANCIAL_REVIEW_REQUIRED.

## Financial Document State

```text
DRAFT
 → ISSUED
 → REVIEW_PENDING (optional)
 → APPROVED
 → PAYMENT_PENDING
 → PAID / CASH_COLLECTED / WALLET_DEBITED
 → POSTED_TO_LEDGER
 → CLOSED
```

Exception states: REJECTED, CANCELLED, VOIDED_BY_REVERSAL, DISPUTED, PARTIALLY_PAID.

## Payment Window State

```text
NOT_STARTED
 → ACTIVE
 → PAID
```

Alternative branches:

```text
ACTIVE → EXPIRED → RESERVATION_RELEASED
ACTIVE → EXTENDED → ACTIVE
ACTIVE → OPERATOR_REVIEW_REQUIRED
```

## Wallet Entry State

```text
CREATED
 → POSTED
 → AVAILABLE
 → HELD (optional)
 → DEBITED / WITHDRAWN / EXPIRED / REVERSED
```

## Escrow State

```text
CREATED
 → FUNDED
 → HELD
 → ELIGIBLE_FOR_RELEASE
 → ALLOCATED
 → RELEASED
 → CLOSED
```

Alternative states: REFUND_HELD, PARTIALLY_RELEASED, DISPUTED, REVERSED.

## Settlement Item State

```text
CREATED
 → SCHEDULED
 → PROCESSING
 → COMPLETED
```

Exception states: FAILED_RETRYABLE, FAILED_PERMANENT, CANCELLED, OFFSET_BY_NETTING, MANUAL_REVIEW_REQUIRED.

## Refund State

```text
REQUESTED
 → PLATFORM_APPROVAL_PENDING
 → APPROVED
 → WALLET_CREDITED
 → CLOSED
```

Optional path:

```text
WALLET_CREDITED → WITHDRAWAL_REQUESTED → WITHDRAWAL_APPROVED → PAID_TO_BANK → WALLET_DEBITED
```

## Money Ownership State

```text
OWNED_BY_CUSTOMER
 → HELD_IN_WALLET
 → HELD_IN_ESCROW
 → ELIGIBLE_FOR_RELEASE
 → ALLOCATED_TO_BENEFICIARIES
 → SETTLED
 → CLOSED
```
