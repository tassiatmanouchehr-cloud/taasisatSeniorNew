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

# 23 — Notification Engine

## Principle

Financial events may create notifications. Notifications are configurable and must not be hard-coded.

## Recipients

- Customer / Customer or Customer Delegate
- Provider / Independent Provider یا Organization Provider
- Organization / Organization
- Platform Team / Platform Owner و تیم
- Finance Operator

## Channels

- In-App
- Push
- SMS
- Email
- Panel Notification
- Phone Call Task

## Notification Examples

- Payment deadline started
- Payment deadline expiring soon
- Payment expired
- Payment received
- Supplemental invoice issued
- Refund credited to wallet
- Wallet withdrawal completed
- Settlement completed
- Settlement failed
- Provider owes platform because of cash collection
- Financial hold required before handover

## Rules

- Sensitive internal financial events may be Platform Only.
- Customer must not see internal commission calculations unless product policy explicitly allows it.
- Provider and organization statements should expose their own balances and related deductions, not unrelated counterparties' private data.
