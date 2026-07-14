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

# 09 — Session Lifecycle Engine (Primary)

## Purpose
Manage the core execution state of a Service Session: when it can start, when the provider is en route, when they've arrived, when execution truly begins, and how it pauses, interrupts, completes, and closes.

## Business Goal
Make the meaning of "the session happened" unambiguous and provable, with a single authoritative state machine that every other engine reads and writes against.

## Functional Specification
See the full state definitions in `07_STATE_MACHINES.md` §1. In summary, the engine governs: SCHEDULED → PROVIDER_EN_ROUTE → PROVIDER_ARRIVED → START_CHECK_PENDING → IN_PROGRESS → PROVIDER_COMPLETED → CUSTOMER_CONFIRMATION_PENDING → CUSTOMER_CONFIRMED → CLOSED, with exception states START_BLOCKED, PAUSED, INTERRUPTED, CUSTOMER_UNAVAILABLE, OPERATIONAL_REVIEW_REQUIRED, COMPLETION_DISPUTED, CANCELLED_DURING_EXECUTION.

## Business Rules
BR-04-001 through BR-04-010 (see `04_BUSINESS_RULES.md`).

## Non-Functional Requirements
- Every state transition must be atomic and emit its corresponding event synchronously.
- The engine must never allow a state skip (e.g. SCHEDULED directly to IN_PROGRESS) outside a documented exception path.

## Edge Cases (structural, non-legal)
- Provider request to complete while an open Exception exists → session may still complete, but the Exception's own lifecycle continues independently (BR-04-068).
- Customer never responds during CUSTOMER_CONFIRMATION_PENDING → provider-submitted confirmation problem request routes to Organization/Platform Team call.

## Future Extension
- Configurable session types with different required state paths (e.g. shorter appointment-style sessions for other marketplace verticals).

## Open Questions
- Exact SLA for "how long is a session allowed to sit in CUSTOMER_UNAVAILABLE before automatic escalation" was not numerically fixed in Discovery; left as an admin-configurable default.

## Related ADR
ADR-04-001, ADR-04-012 (see `28_ADR.md`)

## Related Domain Objects
ServiceSession, CompletionRecord, HandoverRecord, Timeline
