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

# 25 — API Contract

## Commands

### Create Reservation
`POST /financial/reservations`

Input: accepted_offer_id, customer_id, contract_amount, payment_window_policy_context.

Output: reservation_id, payment_deadline, state.

### Create Payment Link
`POST /financial/documents/{id}/payment-link`

Output: payment_link_id, expires_at, channel.

### Record Payment
`POST /financial/payments`

Input: document_id or contract_id, payer, amount, method, provider_reference.

### Record Cash Collection
`POST /financial/cash-collections`

Input: document_id, collector_party_id, payer_party_id, amount, evidence optional.

### Create Supplemental Invoice
`POST /financial/supplemental-invoices`

Input: service_case_id, session_id, issuer, payer, amount, description, collection_model.

### Approve Refund
`POST /financial/refunds/{id}/approve`

Output: wallet_credit_entry_id, financial_event_id.

### Request Wallet Withdrawal
`POST /wallets/{id}/withdrawals`

Input: amount, bank_account_reference.

### Create Settlement Batch
`POST /financial/settlement-batches`

Input: financial_period_id, party_scope, policy_context.

### Retry Settlement Item
`POST /financial/settlement-items/{id}/retry`

## Queries

- `GET /financial/parties/{id}/statement`
- `GET /financial/contracts/{id}`
- `GET /financial/documents/{id}`
- `GET /wallets/{id}/ledger`
- `GET /financial/settlement-batches/{id}`
- `GET /financial/events?aggregate_type=&aggregate_id=`

## Events Published

All commands that change financial state must publish a Financial Event with visibility and audit metadata.
