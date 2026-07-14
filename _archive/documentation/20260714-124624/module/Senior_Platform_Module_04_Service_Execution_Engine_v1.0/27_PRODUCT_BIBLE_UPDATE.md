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

# 27 — Product Bible Update

## Executive Summary

Module 04 — Service Execution & Session Lifecycle Engine owns everything from the moment a provider starts a session to the moment it's closed and handed back to the Service Case. It is the largest module so far, decomposed into ten sub-engines, and it is the first module built under the project's new identity as a **Generic Service Marketplace Framework** rather than a Generic Service Marketplace-Care-only product.

## Key Frozen Decisions (Module 04)

1. The project is now a two-layer architecture: domain-neutral Core Platform + reference implementation Domain Mapping as its first implementation.
2. Module 04 begins at "Service Started" (handoff from Module 03) and ends at Session Closed & Handed Over, producing events only.
3. Ten sub-engines: five Primary (Session Lifecycle, Activity, Interaction, Exception & Resolution, Completion & Handover) and five Supporting (Presence & Location, Start Checklist, Observation & Notes, Evidence, Extension & Overtime).
4. All execution records are immutable once created (ADR-04-001); corrections are always additive.
5. Session start requires presence + GPS (mandatory reference implementation / configurable Core) + customer confirmation + checklist + configured evidence.
6. Location capture is event-based, not continuous, by default (ADR-04-002).
7. All operational communication is platform-mediated; real phone numbers are never exposed (ADR-04-008).
8. The base interaction concept is Interaction, not Message — a universal, reusable exchange model (ADR-04-009).
9. Exceptions are independent entities with their own lifecycle, decoupled from Session state (ADR-04-010) — reusable for future complaints/quality/disputes.
10. Extensions require explicit mutual agreement; unresolved disagreement routes to Operational Review (ADR-04-011).
11. Session completion is not business completion — a completed session never implies the Service Case, contract, or payment is finished (ADR-04-012).
12. Module 04 produces zero financial output; only events for future financial modules.
13. Legal/crisis scenarios (death, serious accidents, insurance, force majeure) remain explicitly deferred pending legal review.
14. A project-wide "constitution" — Platform Architectural Principles v1.0 — was written during this module and applies to all modules going forward.

## Final Architecture (Module 04)

```text
Module 03 → Service Started
        ↓
Session Lifecycle Engine (Primary) ← served by Presence & Location, Start Checklist, Extension & Overtime
        ↓
Execution Activity Engine (Primary) ← served by Observation & Notes, Evidence
        ↓
Interaction Engine (Primary) — spans the whole session
        ↓
Exception & Resolution Engine (Primary) — runs in parallel, independent state
        ↓
Completion & Handover Engine (Primary)
        ↓
Module 05/06 — Payment & Settlement (future, event-triggered only)
```

## MVP Implementation Priorities

### Phase 1
- Session Lifecycle Engine core state machine
- Presence & Location Engine (event-based capture)
- Start Checklist Engine (generic template)
- Execution Activity Engine

### Phase 2
- Observation & Notes Engine
- Evidence Engine
- Interaction Engine (core message/approval/confirmation types)
- Completion & Handover Engine

### Phase 3
- Exception & Resolution Engine (full category/severity taxonomy)
- Extension & Overtime Engine

### Future / Deferred
- Legal-reviewed crisis-scenario library
- Continuous live tracking for high-risk services
- Automated case-completion detection
- Interaction Engine reuse in Modules 05+ (invoice approval, disputes, quality review, refunds)

## Quality Bar

A feature is not complete unless it respects the Module 04 boundary (Service Started → Session Closed & Handed Over), keeps execution records immutable, is testable, handles the decided structural exception/extension/completion cases, is permission-controlled if admin-facing, and creates an audit log when manually changed.

## Freeze Statement

Module 04 is architecturally complete across all ten sub-engines, the Platform Architectural Principles, and the Primary/Supporting classification. The legal crisis-scenario catalogue and continuous tracking are intentionally carried forward as open issues rather than blocking the freeze. Module 04 is considered architecturally frozen for its decided scope. Next: Module 05/06 — Payment & Settlement.
