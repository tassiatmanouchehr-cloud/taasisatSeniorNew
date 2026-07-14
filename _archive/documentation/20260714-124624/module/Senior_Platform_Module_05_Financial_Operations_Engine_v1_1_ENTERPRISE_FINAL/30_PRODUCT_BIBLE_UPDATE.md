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

# 30 — Product Bible Update

## Module 05 Frozen Summary

The platform now has a complete Financial Operations architecture. Payment is not treated as revenue. Customer money may be held in wallet or escrow, and money ownership is explicit throughout the lifecycle.

## Product Rules Added

- The order's accepted price becomes a locked commercial contract.
- Customer payment can move through wallet ledger even when it is immediately consumed by an order.
- Refunds go first to customer wallet.
- Cashback is a separate financial source.
- Provider can issue supplemental invoice when policy allows.
- Provider cash collection is recorded and affects net settlement.
- Platform and organization commissions are configurable and policy-driven.
- Statements must show all relevant accrual, settlement, refund and adjustment activity.
- Settlement is net-position based.
- Ledger entries are immutable.

## Vocabulary

- Financial Party
- Financial Document
- Commercial Contract
- Customer Wallet
- Escrow
- Money Ownership State
- Financial Policy Resolution
- Ledger Entry
- Running Statement
- Settlement Batch
- Settlement Item
- Net Position
- Financial Outcome

## Future Expansion

- Tax engine
- ERP adapter
- PSP adapter
- Bank payout adapter
- AI invoice review
- Multi-currency
- Regulated wallet compliance by jurisdiction
