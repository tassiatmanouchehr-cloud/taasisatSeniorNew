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

# 05 — Architecture

## Architectural Style

Module 04 is an event-driven execution subsystem composed of ten sub-engines, following the project-wide pattern established in `02_PLATFORM_ARCHITECTURAL_PRINCIPLES.md`:

```text
Action → Event → Interaction → Decision → State Change → Timeline → Audit
```

## Primary vs Supporting Engines

**Primary Engines** — independent entity, own lifecycle, own state machine:

```text
Session Lifecycle Engine
Execution Activity Engine
Interaction Engine
Exception & Resolution Engine
Completion & Handover Engine
```

**Supporting Engines** — serve the primary engines, individually removable per future implementation without damaging the execution core:

```text
Presence & Location Engine
Start Checklist Engine
Observation & Notes Engine
Evidence Engine
Extension & Overtime Engine
```

This classification, decided late in Discovery, exists so that a future marketplace that doesn't need GPS or overtime can drop just that Supporting engine without touching the Primary core.

## Common Engine Pattern

Nearly every engine follows the same internal shape:

```text
Entity → Lifecycle → Events → Interactions → Timeline → Audit
```

E.g. Session → Session State → Session Events → Interactions → Timeline → Audit; Activity → Lifecycle → Events → Timeline → Audit; Evidence → Lifecycle → Review → Timeline → Audit.

## Main Pipeline

```text
Module 03 → Service Started
        ↓
Session Lifecycle Engine (Primary)
        ↓  ↑ (served by)
Presence & Location  |  Start Checklist  |  Extension & Overtime
        ↓
Execution Activity Engine (Primary)
        ↓  ↑ (served by)
Observation & Notes  |  Evidence
        ↓
Interaction Engine (Primary) — carries all actor-to-actor exchanges throughout
        ↓
Exception & Resolution Engine (Primary) — runs in parallel, independent state
        ↓
Completion & Handover Engine (Primary)
        ↓
Module 05/06 — Payment & Settlement (future, event-triggered only)
```

## Universal Interaction Architecture

Rather than a bespoke messaging system, all actor-to-actor exchanges (message, phone call, approval, rejection, confirmation, request, response, rating, feedback, signature, escalation, operational decision, internal comment, system prompt) are modeled as one `Interaction` type with a shared lifecycle:

```text
CREATED → DELIVERED → VIEWED → RESPONDED → RESOLVED → CLOSED
CREATED → EXPIRED
CREATED → ESCALATED
```

This is intentionally designed so that future modules (invoice approval, payment confirmation, complaint, quality review, dispute resolution, refund approval) reuse the same Interaction Engine rather than building a new communication mechanism each time.

## Exception Independence

Exceptions are modeled as independent entities related to, but not owned by, a Session — each with its own state machine, timeline, interactions, evidence, and audit trail (ADR-04-010). This is deliberate: the same engine is intended to later serve complaints, quality issues, and disputes, not just execution-time exceptions.

## Event-Based Location, Not Continuous Tracking

Location is captured only at meaningful points (en route, arrived, start, pause, resume, temporary leave, completion, checkout) rather than continuously streamed — a deliberate privacy, battery, cost, and simplicity trade-off (ADR-04-002), with continuous tracking reserved as a future option for high-risk services only.

## Module Boundary

Module 04 begins at "Service Started" (handoff from Module 03) and ends when a Session is Closed and Handed Over to the Service Case, producing events only — no financial output (ADR-04-012, BR-04-081). Module 05/06 owns everything financial from that point.
