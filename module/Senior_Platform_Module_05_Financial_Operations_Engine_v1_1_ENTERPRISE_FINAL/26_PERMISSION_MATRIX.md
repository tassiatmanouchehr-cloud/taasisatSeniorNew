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

# 26 — Permission Matrix

| Action | Customer | Provider | Organization | Platform Operator | Platform Owner |
|---|---:|---:|---:|---:|---:|
| Pay initial contract | Yes | No | No | Assist | Assist |
| View own wallet | Yes | No | No | Support | Yes |
| Request wallet withdrawal | Yes | No | No | No | No |
| Approve wallet withdrawal | No | No | No | Permission | Yes |
| Issue supplemental invoice | No | Yes if policy | Yes if policy | Yes | Yes |
| Approve supplemental invoice | No | No | If policy | Permission | Yes |
| Record provider cash collection | No | Yes | Review | Permission | Yes |
| View own statement | Yes | Yes | Yes | Yes | Yes |
| View all statements | No | No | Own org only | Permission | Yes |
| Approve refund | No | No | No | Permission | Yes |
| Create adjustment | No | No | Request only | Permission | Yes |
| Post ledger entry manually | No | No | No | Restricted | Yes |
| Create settlement batch | No | No | Own org if allowed | Permission | Yes |
| Retry settlement item | No | No | No | Permission | Yes |
| Change financial policy | No | No | Own scope if allowed | Permission | Yes |

## Immutable Rule

No role can edit posted ledger entries. Even Platform Owner must use reversal/adjustment documents.
