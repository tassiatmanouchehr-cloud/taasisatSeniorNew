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

# 28 — Admin Configuration

## Configuration Hierarchy

Framework → Implementation → Marketplace → Organization → Branch → Provider → Service Type → Financial Document → Contract

## Configuration Catalog

### Payment
- default payment window minutes
- payment extension allowed
- max extension count
- expiration action
- payment reminder schedule

### Commission
- platform commission percent/fixed/zero
- organization commission percent/fixed/zero
- commission base: gross or net after platform
- supplemental invoice commission preset
- independent provider commission default

### Financial Documents
- allowed document types
- issuer roles
- approver roles
- AI review required
- manual review required
- digital signature future flag
- invoice numbering policy

### Wallet
- wallet enabled
- top-up enabled
- refund-to-wallet default
- withdrawal enabled
- withdrawal approval required
- cashback enabled

### Refund / Adjustment
- refund approval role
- refund destination
- adjustment approval role
- reversal allowed roles

### Settlement
- settlement delay days
- financial period type
- batch creation schedule
- retry count
- retry interval
- netting enabled
- direct provider payout vs organization payout

### Visibility
- customer event visibility
- provider statement details
- organization statement details
- audit-only event list
