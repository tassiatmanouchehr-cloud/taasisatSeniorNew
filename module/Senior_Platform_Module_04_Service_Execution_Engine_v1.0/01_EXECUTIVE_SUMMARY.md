# Generic Service Marketplace Framework

**Module 04 — Service Execution & Session Lifecycle Engine**

| | |
|---|---|
| **Version** | 1.0 |
| **Status** | Frozen |
| **Document Owner** | Product Architecture |
| **Project** | Generic Service Marketplace Framework Reference Implementation (reference implementation of the Generic Service Marketplace Framework) |
| **Module Owner** | Platform Owner |
| **Depends On** | Module 01 — Request Engine, Module 02 — Matching Engine, Module 03 — Booking, Assignment & Service Activation Engine |
| **Next Modules** | Module 05/06 — Payment & Settlement, future Quality / Dispute / Reporting modules |
| **Language** | Persian business domain, English technical structure |

> Modules 01–03 are Frozen and Approved and are treated as baseline. Module 04 must not change their decisions unless a major architectural conflict is discovered.

> **Architecture Upgrade Notice:** starting with this module, the project is no longer designed as a single-purpose reference implementation platform. It is designed as a **Generic Service Marketplace Framework** (Layer 1 — Core Platform, domain-independent) with **Generic Service Marketplace Framework Reference Implementation as its first reference implementation** (Layer 2 — reference implementation Domain Mapping). Every section below states the Core Platform pattern first, then its reference implementation mapping.

# 01 — Executive Summary

## What Module 04 Is

Module 04 is the largest and most consequential module designed so far. It owns everything that happens from the moment a provider actually starts a service session to the moment that session is formally closed and handed back to the Service Case. Where Module 03 answered "is someone really coming," Module 04 answers "what actually happened, is it proven, and did both sides agree it's done."

## Why It's Different From Modules 01–03

Two architecture-level upgrades happened during this module's Discovery, both significant enough to apply retroactively as project-wide principles, not just Module 04 decisions:

1. **Generic Service Marketplace Framework.** The project stopped being "a reference implementation platform" and became a reusable architecture framework whose first product is Generic Service Marketplace Framework Reference Implementation. Every pattern designed from Module 04 onward is written in two layers: a domain-neutral Core Platform pattern, and a reference implementation mapping. Each future implementation (beauty, cleaning, tutoring, etc.) would be its own independent product — separate repository, database, and deployment — sharing only the architectural patterns, not a multi-tenant runtime.
2. **Universal Interaction Architecture.** What started as an "Operational Communication Engine" was generalized into an **Interaction Engine** — because almost everything actors do to each other during execution (confirm, approve, reject, rate, escalate, message) is structurally the same kind of object. This one decision means every future module (payment approval, dispute resolution, quality review, refund approval) can reuse the same engine.

## The Ten Sub-Engines

Module 04 is decomposed into five **Primary Engines** (Session Lifecycle, Activity, Interaction, Exception & Resolution, Completion & Handover) and five **Supporting Engines** (Presence & Location, Start Checklist, Observation & Notes, Evidence, Extension & Overtime). Primary engines have independent identity and lifecycle; supporting engines serve them and can be individually omitted by future implementations without damaging the execution core.

## Core Decisions at a Glance

- Session start requires presence, GPS (mandatory for reference implementation, configurable in Core), customer confirmation, a start checklist, and — where configured — photo/signature.
- All execution records (activities, observations, evidence, locations, interactions) are **immutable** once created; corrections are always additive (review / correction / note / dispute), never edits.
- The provider can complete a session, but cannot close it alone — closing requires customer confirmation or Operational Review resolution (BR-04-006, BR-04-077).
- Session completion is explicitly **not** business completion, contract completion, or payment completion (ADR-04-012) — it only means execution of that one session is done.
- Module 04 produces zero financial output; it only emits events for future financial modules (BR-04-010, BR-04-081).
- Location tracking is **event-based**, not continuous live tracking, by default — for privacy, battery, cost, and simplicity reasons (ADR-04-002).
- All operational communication happens **inside the platform**; real phone numbers are never exposed between customer and provider (ADR-04-008).
- Exceptions are independent entities with their own state machine, decoupled from Session state (ADR-04-010, BR-04-068) — reusable later for complaints, quality, and disputes.
- Legally sensitive crisis scenarios (death, serious accidents, insurance, force majeure) remain explicitly deferred pending legal review.

## Relationship to Other Modules

```text
Module 03 → Service Started
        ↓
Module 04 (this module) → Session Closed & Handed Over
        ↓
Module 05/06 — Payment & Settlement (future)
```
