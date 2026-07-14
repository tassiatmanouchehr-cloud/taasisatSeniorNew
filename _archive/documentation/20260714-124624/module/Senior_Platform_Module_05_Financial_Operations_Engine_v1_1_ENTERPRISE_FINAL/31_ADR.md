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

# 31 — Architectural Decision Records

## ADR-05-001 — Payment Transaction and Escrow Are Separate
Accepted. Customer payment creates transaction proof and escrow/wallet/liability entries separately.

## ADR-05-002 — Reservation & Payment Expiration Engine
Accepted. Accepted offer starts payment window; expiry releases reservation according to policy.

## ADR-05-003 — Configurable Cancellation Financial Policy
Accepted. Pre-service and in-service cancellation financial effects are policy-driven.

## ADR-05-004 — Partial Completion Finance
Accepted. Partial completion can create partial payable, refund, penalty or manual decision based on evidence and events.

## ADR-05-005 — Supplemental Financial Documents
Accepted. Supplemental invoices and related notes are separate from initial contract.

## ADR-05-006 — Policy Applies to All Financial Documents
Accepted. Every payable/refundable/adjustable document passes through policy engine.

## ADR-05-007 — Supplemental Invoice Closing Stage
Accepted. Supplemental invoice usually happens near service closing but policy supports other timings.

## ADR-05-008 — Multiple Payment Collection Models
Accepted. Platform escrow, provider collection, organization collection and wallet debit are all supported.

## ADR-05-009 — Issuer / Collector / Beneficiary Separation
Accepted. Financial document roles are independent.

## ADR-05-010 — Immutable Multi-Ledger Architecture
Accepted. Order ledger, stakeholder ledger, wallet ledger, escrow ledger and internal accounts are linked but distinct.

## ADR-05-011 — Running Statement Separate From Ledger
Accepted. Statements are user-facing read models over immutable facts plus operational context.

## ADR-05-012 — Financial Recognition Policy
Accepted. Not all displayed rows are recognized financial entitlement. Recognition is policy/state driven.

## ADR-05-013 — Stable Display Row
Accepted. Statements may show unfinished orders as stable rows before final financial recognition.

## ADR-05-014 — Balance-Based Settlement
Accepted. Settlement depends on net position, including cash collections and offsets.

## ADR-05-015 — Configurable Financial Period Engine
Accepted. Long-running services can settle by configurable financial period.

## ADR-05-016 — Settlement Batch with Independent Items
Accepted. Batch groups items; each item has independent status and retry.

## ADR-05-017 — Automatic Retry Settlement Policy
Accepted. Retryable settlement failures can be retried automatically.

## ADR-05-018 — Financial Policy Resolution Core
Accepted. Engines must ask policy engine instead of embedding business rules.

## ADR-05-019 — Contract Price Lock
Accepted. Accepted contract price is locked; corrections are additive.

## ADR-05-020 — Commercial Pricing Decisions
Accepted. Offer pricing is captured and archived; later restrictions may block invalid prices before submission.

## ADR-05-021 — Commission Base
Accepted. Commission base is configurable: gross, net, document type, provider type and organization-specific.

## ADR-05-022 — Archived Offers
Accepted. Non-selected offers remain audit history.

## ADR-05-023 — Discount Ownership Model
Accepted. Discount must specify owner/funder because it affects commission and payable amounts.

## ADR-05-024 — Incorrect Contract Resolution
Accepted. Incorrect contract is not edited; use cancellation, refund, reversal or adjustment.

## ADR-05-025 — Refund Destination
Accepted. Refund defaults to customer wallet.

## ADR-05-026 — Invoice Snapshot, Lock, Versioning and Notes
Accepted. Invoice preserves snapshot, supports versions before final lock, and has unlimited notes.

## ADR-05-027 — Future Digital Signature
Accepted. Signature is future-ready but not mandatory in v1.

## ADR-05-028 — Financial Event and Configuration Catalogs
Accepted. Events and configurations are first-class architecture artifacts.

## ADR-05-029 — Cross-Module Financial Outcomes
Accepted. Module 05 publishes outcomes, not raw internal structures.

## ADR-05-030 — Money Ownership Lifecycle
Accepted. Customer money is held by Platform Owner in escrow until services are completed and funds are split.

## ADR-05-031 — Multi-Party Netting
Accepted. Marketplace settlement must calculate all party net positions before settlement.

## ADR-05-032 — Financial Party Architecture
Accepted. Financial Party is independent from User, Provider, Organization, Collector or Issuer.

## ADR-05-033 — Customer Wallet Ledger
Accepted. Customer wallet is a real financial account; balance is derived from ledger entries.
