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

# 04 — Business Rules

## BR-05-001 — Accepted Offer Creates Financial Reservation
When a customer accepts an offer, Module 05 must create a reservation and payment deadline according to configuration.

## BR-05-002 — Payment Window Is Configurable
Payment window may be configured by marketplace, service type, organization, customer type or contract. Default for Generic Service Marketplace Framework Reference Implementation may be 30 minutes.

## BR-05-003 — Expired Payment Releases Reservation
If the payment deadline expires and no extension exists, the selected offer/reservation may be cancelled, provider capacity released, and matching reopened according to policy.

## BR-05-004 — Customer Payment Creates Wallet/Escrow Entries
Online payment for an order may credit customer wallet and immediately debit it for the order, creating visible wallet trace even when final wallet balance is zero.

## BR-05-005 — Main Contract Amount Is Locked
After order finalization, the accepted contract amount is locked. If wrong, it must be corrected using cancellation, refund, adjustment, credit/debit note or reversal; not by editing the original amount.

## BR-05-006 — Contract Amount Can Be Summary-Level Initially
The initial implementation may store the contract amount as one total. The architecture must allow future line items without redesign.

## BR-05-007 — Supplemental Invoice Is Separate From Contract Price
Overtime, extension, travel, medicine, equipment or other post-contract charges must be represented as supplemental financial documents.

## BR-05-008 — Provider May Issue Supplemental Invoice
In Generic Service Marketplace Framework Reference Implementation, the provider may issue an extra invoice near session closing after discussing it with the customer.

## BR-05-009 — AI Review Is Future-Ready
Version 1 may send payment link directly. Future versions may require AI or manual review before sending payment link.

## BR-05-010 — Issuer, Collector and Beneficiary Are Separate
Every financial document must explicitly identify payer, issuer, collector, approver, beneficiary and settlement payer where applicable.

## BR-05-011 — Provider Cash Collection Creates Receivables
If a provider collects cash, the platform and organization shares must still be recognized as receivables or offsets in netting.

## BR-05-012 — Platform Commission Is Configurable
Platform Owner may configure commission per organization, service type, provider type, financial document type, contract, or supplemental invoice.

## BR-05-013 — Organization Commission Is Configurable
A company may define commission from its affiliated provider. The base may be gross contract amount or net amount after platform commission.

## BR-05-014 — Independent Provider Has No Organization Share
For Independent Provider, company commission is not applicable unless a future intermediary is introduced.

## BR-05-015 — Monthly Services Use Financial Periods
Long-running/monthly services may be financially processed in configurable periods, e.g., weekly cycles.

## BR-05-016 — Settlement Timing Is Configurable
Platform Owner can define whether settlement is scheduled immediately after financial clearance or after 1 to 5 days or another configured delay.

## BR-05-017 — Financial Records Are Immutable
No posted financial ledger entry, wallet entry, escrow entry, statement source event or settlement item may be directly edited or deleted.

## BR-05-018 — Corrections Are Additive
Mistakes are corrected through adjustment, reversal, debit note, credit note or refund documents.

## BR-05-019 — Refund Requires Platform Authorization
Refund is authorized by Platform Owner or authorized platform operator.

## BR-05-020 — Refund Destination Defaults to Wallet
Refunds first credit the customer wallet; bank withdrawal is a separate flow.

## BR-05-021 — Cashback Is Not Refund
Cashback must be a separate wallet credit type with its own financial document/policy.

## BR-05-022 — Wallet Withdrawal Requires Approval
Customer wallet withdrawal to bank requires request, approval, payment execution and wallet debit.

## BR-05-023 — Settlement Is Balance-Based
If a provider owes platform because of cash collection and commissions, the settlement engine may offset the debt from future payables or produce a receivable.

## BR-05-024 — Settlement Batch Contains Independent Items
A batch groups settlement items but each item has independent state, failure reason and retry history.

## BR-05-025 — Settlement Retry Is Automatic Where Allowed
Failed settlement items may retry automatically according to policy; permanent failure requires operator review.

## BR-05-026 — Running Statement Shows Pending Operational Rows
A statement may show unfinished orders as zero recognized amount until financial recognition occurs, while preserving stable display rows.

## BR-05-027 — Ledger and Statement Are Separate
Ledger is formal immutable financial record. Statement is user-facing representation and can include pending/predictive/operational rows.

## BR-05-028 — Money Ownership State Must Be Explicit
Money states include owned by customer, held in wallet, held in escrow, eligible for release, allocated to beneficiaries, settled and closed.

## BR-05-029 — Financial Events Require Visibility
Each event must define visibility: platform only, organization, provider, customer, audit only, or combinations.

## BR-05-030 — Module 05 Emits Outcomes Not Raw Internals
Outbound modules should consume Financial Outcomes, not internal invoice/ledger table structures.
