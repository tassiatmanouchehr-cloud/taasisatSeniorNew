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

# 01 — Executive Summary

## What Module 05 Is

Module 05 owns the financial lifecycle of the marketplace. It starts when a selected offer or financial document needs financial processing and continues through payment, escrow, wallet movement, commission calculation, ledger posting, stakeholder statements, refund/adjustment handling, netting and settlement outcomes.

The module is deliberately broader than payment. A marketplace financial system must answer five separate questions:

1. What commercial amount was agreed?
2. Who paid, by what method, and who collected the money?
3. Who economically owns the money at each moment?
4. Who is entitled to what amount after policy application?
5. What has actually been settled, refunded, adjusted or left outstanding?

## Core Marketplace Decision

Every customer payment creates at least two distinct effects:

- a **Payment Transaction** proving money movement or collection;
- a **Financial Account / Escrow / Wallet / Ledger Entry** explaining who is credited, debited, liable or entitled.

These concepts must never be collapsed into one field.

## Major Decisions

- Customer money paid for the main order is held by Platform Owner as escrow until operational completion and financial release.
- Direct order payment can still pass through the customer wallet ledger: wallet credit, then order debit.
- Refunds first return to the customer wallet; withdrawal to bank is a separate financial flow.
- Supplemental invoices can be created by the provider near service closing and can be paid online, by wallet, by cash, or through configurable collection policies.
- Issuer, collector, payer, beneficiary, approver and settlement payer are separate roles.
- Commission policy can differ for main contract, overtime, supplemental invoice, discount, organization/provider relation and document type.
- All financial records are immutable. Corrections use adjustments, reversals, credit notes or debit notes.
- Stakeholders see running statements, not raw accounting tables.
- Settlement is based on net position, not blindly paying every order separately.

## Relationship to Module 04

Module 05 does not decide whether service execution is complete. It listens to Module 04 outcomes such as `service_session_closed`, `completion_confirmed`, `financial_clearance_requested` and `handover_completed`.

Module 05 can publish financial holds or clearances back to operational workflows, such as `supplemental_invoice_pending_payment`, `financial_hold_required` and `financial_clearance_granted`.

## reference implementation Mapping

- Customer = Customer or Customer Delegate
- Independent Provider = Independent Provider
- Organization Provider = Organization Provider
- Organization = Organization
- Platform Owner = Platform Owner
- Customer Wallet = حساب / کیف پول Customer
- Platform Escrow = پول امانی نزد Platform Owner
