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

# 03 — Product Specification

## Product Objective

Build a reusable financial operations layer for any service marketplace where a customer can select an offer, pay, use wallet balance, receive refunds/cashback, be invoiced for extras, and where platform, organization and provider shares must be calculated, stated and settled.

## Core User Outcomes

### Customer / Customer Family
- Pay for accepted offer within a time window.
- Use wallet balance for payment.
- Receive refund into wallet.
- Request wallet withdrawal.
- Review/pay supplemental invoices.
- See payment and wallet history.

### Provider / Provider
- See expected receivables from orders.
- Issue supplemental invoice when allowed.
- Record cash collection when allowed.
- See running statement and net payable/receivable balance.
- See settlement items and failed payment reasons.

### Organization / Company
- Configure provider commission rules.
- See organization statement, receivables, provider allocations and settlement status.
- Review provider invoices where policy requires.

### Platform / Platform Owner
- Configure payment windows, commission, refund, settlement delay and financial policies.
- Approve refunds and sensitive adjustments.
- Monitor escrow, wallet liabilities, receivables, payables and settlement batches.
- Export financial outcomes for future accounting.

## Financial Documents

Supported document types:

- Initial Contract
- Initial Invoice / Contract Invoice
- Supplemental Invoice
- Overtime Invoice
- Extension Invoice
- Extra Charge Invoice
- Credit Note
- Debit Note
- Refund Document
- Adjustment Document
- Reversal Document
- Settlement Document
- Wallet Top-Up Document
- Cashback Document

## Collection Models

- Platform Escrow Collection
- Customer Wallet Debit
- Provider Cash Collection
- Provider Online Collection via platform link
- Organization Collection
- Manual / Operator Recorded Collection

## Non-Goals

- Direct bank transfer execution.
- Statutory tax compliance engine.
- ERP double-entry posting adapter.
- PSP implementation details.
