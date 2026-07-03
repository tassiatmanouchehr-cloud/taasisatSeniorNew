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

# 27 — UI Screen Catalog

## Customer Screens

- Payment Deadline / Pay Now
- Wallet Balance
- Wallet Ledger
- Refund Credit Details
- Wallet Withdrawal Request
- Supplemental Invoice Review and Payment
- Payment History

## Provider Screens

- My Financial Statement
- Supplemental Invoice Create
- Cash Collection Record
- Settlement Status
- Amount Owed to Platform / Organization
- Failed Settlement Item Details

## Organization Screens

- Organization Statement
- Provider Payables
- Organization Commission Rules
- Settlement Batch Overview
- Provider Cash Collection Review

## Platform Screens

- Financial Dashboard
- Escrow Monitor
- Wallet Liability Monitor
- Payment Window Monitor
- Refund Approval Queue
- Adjustment/Reversal Console
- Settlement Batch Manager
- Financial Party Profile
- Ledger Journal Viewer
- Policy Configuration
- Event Audit Timeline

## Admin Safety

UI must clearly distinguish:

- paid amount
- escrow balance
- wallet balance
- recognized revenue
- payable amount
- settled amount
- outstanding receivable/payable
