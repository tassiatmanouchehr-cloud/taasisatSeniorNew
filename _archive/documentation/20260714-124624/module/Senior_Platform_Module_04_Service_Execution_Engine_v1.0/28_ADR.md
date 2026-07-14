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

# 28 — Architecture Decision Records

## ADR-04-001 — Immutable Service Execution Records
Once a Provider records an Execution Record, the original record is immutable. No one — including Organization and Platform Team — may edit or delete it. They may only add Review, Internal Note, Correction, Administrative Comment, Dispute, Verification Result, or Audit Result, each with timestamp, actor, role, reason, and digital audit trail.

## ADR-04-002 — Event-Based Location Tracking
The system does not use continuous live tracking as the default. Instead it uses event-based location capture at meaningful points. Reasons: provider privacy, technical cost, battery consumption, implementation simplicity, applicability across different marketplaces, and sufficiency for operational audit. Continuous tracking may be enabled in the future for high-risk services, but is not part of the Core default.

## ADR-04-007 — Operational Communication First
The communication system is an Operational Communication Engine, not a general-purpose messenger. Its goals: reduce support calls, keep complete records, manage disputes, log operational decisions, create an audit trail — not build a social network or full messaging product.

## ADR-04-008 — Platform-Controlled Communication
All operational communication between parties happens inside the platform; the platform mediates. While a Session is active, direct communication is allowed, but only through the platform, and real phone numbers are never shown to each other. Benefits: reduced platform bypass, privacy protection, complete record-keeping, audit and dispute-resolution capability, and reusability across all future projects.

## ADR-04-009 — Universal Interaction Architecture
The base concept is no longer Communication — it is **Interaction**. During an active Session, actors are constantly interacting (declaring start, confirming completion, approving overtime, rejecting a dispute, rating a service), not just exchanging messages. The Communication Engine is generalized into the Interaction Engine, so every future module (invoice approval, payment confirmation, complaint, quality review, dispute resolution, refund approval) can reuse the same engine.

## ADR-04-010 — Independent Exception Lifecycle
An Exception is an independent entity: it has its own state machine, own timeline, own interactions, own evidence, and own audit trail, and only relates to a Session rather than being part of it. This lets the same engine later serve complaints, quality issues, and disputes.

## ADR-04-011 — Extension Requires Explicit Mutual Agreement
No Extension or Overtime is valid without explicit agreement between Customer and Provider. Without agreement, the system must enter Operational Review. Module 04 only records the fact of the extension and the agreement or dispute; financial calculation, invoicing, and settlement happen in later modules.

## ADR-04-012 — Session Completion Is Not Business Completion
Completion means execution is finished — not that the contract is finished, the case is closed, payment has happened, or the project has ended. Execution is only responsible for the end of that one Session's execution. This is the single most important ADR in the Completion & Handover Engine.

## ADR-04-013 — Generic Service Marketplace Framework (Project-Wide)
The project is upgraded from a single-purpose reference implementation platform to a reusable architectural framework for building independent service marketplace applications (Layer 1 — Core Platform, domain-independent) with Generic Service Marketplace Framework Reference Implementation as its first implementation (Layer 2 — reference implementation Domain Mapping). Each future implementation is its own independent product (own repository, database, server, domain) — "generic" means reusable patterns, not multi-tenancy.

## ADR-04-014 — Primary / Supporting Engine Classification
Module 04's ten sub-engines are classified as five Primary Engines (independent entity, own lifecycle: Session Lifecycle, Activity, Interaction, Exception & Resolution, Completion & Handover) and five Supporting Engines (serve the primary engines and are individually removable per implementation: Presence & Location, Start Checklist, Observation & Notes, Evidence, Extension & Overtime). This clarifies dependencies and lets future implementations omit unneeded Supporting engines without damaging the execution core.

## ADR-04-015 — Platform Architectural Principles as a Living Document
A project-wide "constitution" document (`02_PLATFORM_ARCHITECTURAL_PRINCIPLES.md`) is established above all modules, codifying twenty principles discovered across Modules 01–04 (Event-Driven Architecture, Interaction-Centric Design, Immutable Records, Timeline as Operational History, Configuration Over Hardcoding, Domain Pattern → Project Implementation, and others). It applies to Module 01+ and all future modules.

## ADR-04-016 — Documentation Package Standard for Module 04
Given the module's real complexity (ten sub-engines plus the new Platform Architectural Principles document), the documentation package standard is extended beyond Module 03's format with one dedicated file per sub-engine, a dedicated Event Catalog, and a dedicated Platform Architectural Principles file — while keeping the same per-file header (Depends On / Next Modules) and enriched section template introduced in Module 03.

## ADR-04-017 — Legal Crisis Scenarios Remain Deferred
Death, serious accidents, insurance, force majeure, legal liability, and complex legal exception scenarios remain explicitly outside this module's architecture, consistent with the same deferral decided in Module 03, pending legal review in a future module.
