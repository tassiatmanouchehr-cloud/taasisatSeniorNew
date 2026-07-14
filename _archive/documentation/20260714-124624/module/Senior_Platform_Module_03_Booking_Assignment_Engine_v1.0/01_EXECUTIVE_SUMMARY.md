# Generic Service Marketplace Framework

**Module 03 — Booking, Assignment & Service Activation Engine**

| | |
|---|---|
| **Version** | 1.0 |
| **Status** | Frozen |
| **Document Owner** | Product Architecture |
| **Project** | Generic Service Marketplace Framework Reference Implementation |
| **Module Owner** | Platform Owner |
| **Depends On** | Module 01 — Request Engine, Module 02 — Matching Engine |
| **Next Modules** | Module 04 — Service Execution / Care Delivery Engine, Module 05/06 — Payment & Settlement |
| **Language** | Persian business domain, English technical structure |

> Module 01 and Module 02 are Frozen and Approved and are treated as baseline. Module 03 must not change their decisions unless a major architectural conflict is discovered.

# 01 — Executive Summary

## What Module 03 Is

Module 03 is the bridge between a customer's *choice* (produced by Module 02) and a real, trackable, executable commitment: a confirmed provider or company is going to a confirmed address at a confirmed time, and everyone involved knows it and has agreed to it.

Before Module 03, "selection" is just a preference. After Module 03, it is a **Confirmed Service Assignment** — a Service Case, ready for Module 04 to execute.

## Why It Matters

This is the module where a marketplace preference turns into an operational promise. Get it wrong and the platform either over-promises (customer thinks it's booked, provider never confirmed) or under-delivers (bookings silently fail with nobody informed). Three separate commitment paths — independent provider, company provider, company package — must each be handled correctly, because the party actually making the commitment differs in each case.

## Core Decisions at a Glance

- Module 03 begins at **Selection Lock** and ends at **Service Started** (Decision 03-051).
- Selection is not automatically a final booking — provider commitment is still required (Q03-001/002 resolved via the Provider Commitment scope item and the three-path design, Decision 03-006).
- Three distinct commitment paths are designed separately: independent provider, company provider (via company), company-as-package (company assigns providers itself).
- No separate "pre-service summary/confirmation" screen is required — both customer and provider see live status in their own panel (scenario 1 decision).
- Platform Owner's team can hold/block a Service Case before it starts if something looks wrong (scenario 2 decision).
- If a provider hasn't signalled "on the way" close to appointment time, the system immediately contacts the provider **and** involves the company (scenario 3 decision).
- Failure & Recovery, Audit & Traceability, and role Dashboards are first-class parts of this module, not afterthoughts.
- The legally sensitive crisis-scenario library is intentionally deferred pending legal review (see `00_README.md` → Open Issues).

## Relationship to Other Modules

```text
Module 01 (Request Engine)
        ↓
Module 02 (Matching Engine)  →  Customer Selected Candidate / Selection Lock
        ↓
Module 03 (this module)      →  Confirmed Service Assignment / Service Case
        ↓
Module 04 (Service Execution / Care Delivery Engine)
        ↓
Module 05/06 (Payment & Settlement)
```
