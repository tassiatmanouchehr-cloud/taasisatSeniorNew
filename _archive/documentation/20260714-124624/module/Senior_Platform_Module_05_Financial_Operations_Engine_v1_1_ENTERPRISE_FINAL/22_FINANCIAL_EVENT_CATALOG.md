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

# 22 — Financial Event Catalog

## Event Visibility Levels

- Platform Only
- Platform + Organization
- Organization Only
- Provider
- Customer
- Audit Only
- Platform + Customer
- Platform + Provider
- Platform + Organization + Provider

## Core Events

### Reservation
- `financial_reservation_created`
- `payment_window_started`
- `payment_window_extended`
- `payment_window_expired`
- `reservation_released`

### Contract & Pricing
- `offer_price_accepted`
- `contract_amount_locked`
- `contract_price_correction_requested`
- `contract_cancelled_for_price_error`

### Financial Document
- `financial_document_drafted`
- `financial_document_issued`
- `financial_document_review_requested`
- `financial_document_approved`
- `financial_document_rejected`
- `payment_link_sent`
- `financial_document_paid`
- `financial_document_posted`
- `financial_document_closed`

### Payment
- `payment_received`
- `payment_failed`
- `cash_collection_recorded`
- `wallet_debit_recorded`
- `payment_transaction_reconciled`

### Wallet
- `wallet_topup_received`
- `wallet_order_debit_posted`
- `wallet_refund_credit_posted`
- `wallet_cashback_credit_posted`
- `wallet_withdrawal_requested`
- `wallet_withdrawal_approved`
- `wallet_withdrawal_completed`

### Escrow
- `escrow_created`
- `escrow_funded`
- `escrow_release_eligible`
- `escrow_allocated`
- `escrow_released`
- `escrow_refunded`
- `escrow_closed`

### Ledger & Statement
- `ledger_entry_posted`
- `ledger_journal_posted`
- `statement_row_created`
- `statement_balance_updated`

### Commission & Allocation
- `platform_commission_calculated`
- `organization_commission_calculated`
- `provider_payable_allocated`
- `financial_obligation_created`

### Refund & Adjustment
- `refund_requested`
- `refund_approved`
- `refund_rejected`
- `refund_wallet_credit_posted`
- `adjustment_document_created`
- `reversal_posted`
- `credit_note_posted`
- `debit_note_posted`

### Settlement
- `net_position_calculated`
- `settlement_batch_created`
- `settlement_item_scheduled`
- `settlement_item_processing`
- `settlement_item_completed`
- `settlement_item_failed`
- `settlement_retry_scheduled`
- `settlement_batch_closed`

### Cross-Module Outcomes
- `financial_hold_required`
- `supplemental_invoice_pending_payment`
- `financial_clearance_granted`
- `financial_outcome_published`
