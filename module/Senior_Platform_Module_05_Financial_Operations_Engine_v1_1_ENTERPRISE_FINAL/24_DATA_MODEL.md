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

# 24 — Data Model

## Tables / Collections

### financial_parties
- id
- party_type
- reference_type
- reference_id
- display_name
- status
- created_at

### financial_accounts
- id
- party_id
- account_type: wallet, escrow, revenue, payable, receivable, clearing, settlement
- currency
- status

### commercial_contracts
- id
- service_case_id
- accepted_offer_id
- customer_party_id
- provider_party_id
- organization_party_id nullable
- platform_party_id
- contract_amount
- currency
- locked_at
- status

### financial_documents
- id
- document_type
- document_number
- contract_id nullable
- issuer_party_id
- payer_party_id
- collector_party_id nullable
- beneficiary_party_id nullable
- approver_party_id nullable
- gross_amount
- currency
- state
- version
- issued_at
- locked_at

### payment_transactions
- id
- financial_document_id nullable
- contract_id nullable
- payer_party_id
- collector_party_id
- method
- amount
- status
- provider_reference
- paid_at

### wallet_ledger_entries
- id
- wallet_account_id
- entry_type
- debit_amount
- credit_amount
- source_document_id nullable
- source_payment_id nullable
- posted_at

### escrow_records
- id
- escrow_account_id
- contract_id
- amount
- state
- ownership_state
- funded_at
- released_at nullable

### ledger_entries
- id
- journal_id
- account_id
- party_id
- debit_amount
- credit_amount
- currency
- source_type
- source_id
- description
- posted_at
- immutable_hash

### statement_rows
- id
- party_id
- source_type
- source_id
- display_date
- title
- debit_amount
- credit_amount
- balance_after nullable
- row_state

### settlement_batches
- id
- period_id nullable
- status
- scheduled_at
- created_by

### settlement_items
- id
- batch_id
- party_id
- net_amount
- direction: payable_to_party, receivable_from_party, offset_only
- status
- retry_count
- failure_reason nullable

### financial_events
- id
- event_type
- aggregate_type
- aggregate_id
- actor_id
- visibility
- payload
- occurred_at

## Integrity Rules

- Ledger entries are append-only.
- Wallet balance is sum(credits - debits).
- Settlement item status is independent from settlement batch status.
- Financial documents cannot be edited after lock; versioning or adjustment is required.
