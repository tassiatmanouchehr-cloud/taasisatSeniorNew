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

# 12 — Execution Activity Engine (Primary)

## Purpose
Record every action a provider performs during a Session, without the Core engine needing to know what the action means.

## Business Goal
Give the platform a complete, reusable, domain-neutral record of "what was done" that works identically for a provider giving medication or a hairdresser doing a haircut.

## Functional Specification

The engine's key principle: it does not know what an activity *is* — it only knows that "an activity happened at a specific time, by a specific actor, inside a specific session."

### Core Object — Execution Activity
Fields: Activity ID, Session ID, Activity Type, Actor, Started At, Finished At, Duration, Status, Visibility, Source, Timeline Position, Created At, Created By, Version, Audit Metadata.

### Activity Types (Core Categories Only)
TASK, CHECK, ACTION, OBSERVATION, MEASUREMENT, COMMUNICATION, SYSTEM_EVENT, CUSTOM_EVENT.

### Activity Status
PLANNED, AVAILABLE, STARTED, IN_PROGRESS, COMPLETED, SKIPPED, FAILED, CANCELLED.

### Visibility
Provider Only, Customer, Organization, Platform Team, Internal Only, Public To Session, Custom.

### Source
Manual, System Generated, Automation, Integration, API, Admin Action.

### Dependencies & Ordering
Some activities depend on a prior activity (Core stores the dependency link only; domain logic for what depends on what lives in the mapping layer). Activities are ordered by Timeline Sequence, Execution Order, and Logical Dependency — not solely by timestamp.

## Business Rules
BR-04-029 through BR-04-036 (see `04_BUSINESS_RULES.md`).

## Non-Functional Requirements
- Must remain fully domain-agnostic at the Core layer; no reference implementation-specific field names in Core schema.
- Every activity write must be append-only.

## Edge Cases (structural, non-legal)
- Activity marked SKIPPED still enters the Timeline (skipping is not deleting).
- An Activity that depends on a prior Activity which failed — Core only stores the dependency link; how to handle a failed dependency is a domain-mapping decision, not a Core rule.

## Future Extension
- Dependency-aware activity templates (predefined activity chains) per Organization or Service Type.

## Open Questions
- None explicitly raised in Discovery beyond the domain-mapping dependency question above.

## Related ADR
None assigned directly to this engine name, but it is foundational to ADR-04-001 (Immutable Records) and the Primary/Supporting classification.

## Related Domain Objects
ExecutionActivity, ObservationRecord, EvidenceItem, Interaction, ServiceSession
