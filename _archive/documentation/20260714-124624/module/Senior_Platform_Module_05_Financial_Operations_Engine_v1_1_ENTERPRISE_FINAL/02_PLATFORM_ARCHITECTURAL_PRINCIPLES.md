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

# 02 — Platform Architectural Principles

## P05-001 — Financial Architecture Is Generic

The core architecture must not contain reference implementation-only assumptions. Generic Service Marketplace Framework Reference Implementation is the reference implementation, not the framework boundary.

## P05-002 — Money Movement and Money Meaning Are Separate

A successful payment transaction only proves collection. It does not by itself define revenue, liability, receivable, payable, wallet balance or settlement eligibility.

## P05-003 — Append-Only Financial Truth

Posted financial facts are immutable. No record with financial consequence may be edited or deleted after posting. Corrections are represented by new records.

## P05-004 — Policy Outside Engine Logic

Pricing, commission, refund, settlement, payment window, review, wallet and collection behavior must be resolved by Financial Policy Resolution Engine. Individual engines ask for policy outcomes; they must not hard-code business rules.

## P05-005 — Financial Party Is Independent

A Financial Party can be a customer, provider, organization, platform, wallet, branch, internal account or external counterparty. It is not identical to user identity.

## P05-006 — Wallet Balance Is Derived

Wallet balance must be derived from wallet ledger entries. It must never be an editable numeric field.

## P05-007 — Statements Are User-Facing Interpretations

Ledgers are system truth. Running statements are readable views that combine ledger entries, operational status and pending financial documents.

## P05-008 — Escrow Is Liability Until Release

Customer money held by platform before completion is not platform revenue. It is held in escrow or wallet liability until release, refund, debit or settlement.

## P05-009 — Settlement Is Net-Position Based

The platform should calculate net payable/receivable positions per financial party before creating settlement items. This prevents unnecessary transfers and supports cash collection offsets.

## P05-010 — All Financial Outputs Are Evented

Every meaningful financial state transition must publish an event with visibility and audit metadata.
