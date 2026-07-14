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

# 08 — Flows

## Flow 01 — Main Order Payment

```text
Customer accepts offer
 → Reservation created
 → Payment deadline starts
 → Customer pays online
 → Wallet credited (optional internal path)
 → Wallet debited for order
 → Escrow funded
 → Contract active
 → Events published
```

## Flow 02 — Payment Expired

```text
Reservation active
 → Payment deadline expires
 → Policy resolved
 → Reservation released
 → Provider capacity released
 → Matching reopened or operator review required
 → Customer/provider/organization notified
```

## Flow 03 — Service Completed and Settlement Prepared

```text
Module 04 publishes operational completion
 → Module 05 resolves financial release policy
 → Escrow eligible for release
 → Commissions calculated
 → Payables allocated
 → Ledger posted
 → Statements updated
 → Settlement scheduled according to delay policy
```

## Flow 04 — Corporate Provider Settlement Example

```text
Gross paid: 10,000,000
Platform commission: 10% = 1,000,000
Net after platform: 9,000,000
Company commission from provider: configurable, e.g. 10%
Company may receive all 9,000,000 or direct provider payout may be used
Ledger and statement show all receivable/payable obligations
```

## Flow 05 — Independent Provider Settlement Example

```text
Gross paid: 10,000,000
Platform commission: 20% = 2,000,000
Provider receivable: 8,000,000
No organization party exists
Settlement item created for provider after netting
```

## Flow 06 — Supplemental Invoice at Closing

```text
Service work finished
 → Provider creates supplemental invoice
 → Optional AI/manual review
 → Payment link sent or cash recorded
 → Customer pays / provider collects
 → Escrow or cash receivable updated
 → Policies applied
 → Ledger and statements updated
 → Module 04 receives financial clearance/hold signal
```

## Flow 07 — Refund to Wallet

```text
Refund decision approved by platform
 → Refund document created
 → Ledger posted
 → Customer wallet credited
 → Customer sees wallet balance
 → Optional withdrawal request
 → Wallet debited after bank payout
```

## Flow 08 — Provider Collected Cash

```text
Provider collects cash from customer
 → Cash collection recorded
 → Provider statement credited for collected amount
 → Platform/organization commissions become receivable from provider or offset from future settlement
 → Netting engine calculates final position
```

## Flow 09 — Wallet Top-Up and Order Use

```text
Customer tops up wallet: +7,000,000
Later order amount: 10,000,000
Wallet debit: -7,000,000
New online payment: 3,000,000
Escrow/order funded: 10,000,000
Wallet balance: 0
```
