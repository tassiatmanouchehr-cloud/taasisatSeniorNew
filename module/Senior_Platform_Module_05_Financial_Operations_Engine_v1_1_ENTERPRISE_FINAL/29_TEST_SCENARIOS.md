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

# 29 — Test Scenarios

## Reservation and Payment
1. Accepted offer creates reservation and payment deadline.
2. Payment before deadline funds escrow.
3. Payment after deadline is rejected or routed to operator review.
4. Operator extension creates immutable extension history.
5. Expired reservation releases provider capacity.

## Contract Lock
6. Contract amount cannot be edited after finalization.
7. Incorrect price resolution creates cancellation/refund/adjustment document.
8. Archived offers remain visible for audit but cannot mutate contract.

## Supplemental Invoice
9. Provider creates supplemental invoice near closing.
10. Supplemental invoice can require review before link.
11. Supplemental invoice paid online increases escrow.
12. Provider cash collection creates provider cash collected record and platform receivable.

## Commission
13. Corporate provider: platform commission, organization commission, provider payable calculated.
14. Organization commission base can be gross or net.
15. Independent provider has no organization commission.
16. Supplemental invoice uses separate commission preset.

## Wallet
17. Direct order payment credits wallet then debits wallet.
18. Wallet top-up remains available for future order.
19. Partial wallet + online payment funds order.
20. Refund credits wallet.
21. Wallet withdrawal debits wallet after payout.
22. Cashback credit is separate from refund.

## Ledger and Statement
23. Posted ledger entry cannot be edited.
24. Adjustment creates new document and new ledger entries.
25. Statement shows pending unfinished order as stable row with zero recognized provider amount.
26. Settlement document appears in stakeholder statement.

## Settlement
27. Positive provider net balance creates payable settlement item.
28. Negative provider balance creates receivable or offset.
29. Settlement batch can have one item completed and another failed.
30. Retryable failure schedules retry.
31. Permanent failure requires operator review.

## Cross-Module
32. Module 05 does not complete service sessions.
33. Module 05 publishes financial hold when supplemental invoice blocks handover.
34. Module 05 publishes financial clearance when payment/override is resolved.
