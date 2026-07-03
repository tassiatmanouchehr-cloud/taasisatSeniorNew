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

# 10 — Presence & Location Engine (Supporting)

## Purpose
Prove and manage the provider's physical presence throughout Session execution: en route, arrival, distance validation, mid-session departure, and mismatch handling.

## Business Goal
Give the platform trustworthy, minimally invasive proof of "the provider was actually there," without resorting to continuous live tracking.

## Functional Specification

- Core Concepts: Location Capture, Presence Proof, Target Service Location, Geofence, Distance Validation, Manual Override, Location Mismatch, Presence Event.
- Main states: NOT_TRACKED → EN_ROUTE_LOCATION_CAPTURED → ARRIVAL_LOCATION_CAPTURED → PRESENCE_VERIFIED → SESSION_LOCATION_ACTIVE → DEPARTURE_CAPTURED, with exception states GPS_UNAVAILABLE, LOCATION_MISMATCH, PRESENCE_UNVERIFIED, MANUAL_REVIEW_REQUIRED, UNAUTHORIZED_DEPARTURE.
- Location capture is event-based (en route, arrived, start, pause, resume, temporary leave, completion, checkout), not continuous (ADR-04-002).

## Business Rules
BR-04-011 through BR-04-020 (see `04_BUSINESS_RULES.md`).

## Non-Functional Requirements
- Must not depend on continuous background GPS streaming (battery and privacy).
- Distance validation threshold must be configurable per implementation and risk level.

## Edge Cases (structural, non-legal)
- Provider's device reports GPS unavailable at arrival — provider can still proceed via BR-04-016's problem-report path rather than being permanently blocked.
- Mid-session departure that is ambiguous (not clearly authorized or unauthorized) routes to MANUAL_REVIEW_REQUIRED rather than being force-classified.

## Future Extension
- Continuous live tracking as an opt-in feature for high-risk services (explicitly reserved, not built in v1).
- Geofencing refinements (dynamic radius by neighborhood density).

## Open Questions
- Exact default distance radius per service type beyond the reference implementation 100–300m default is not yet fixed for other future marketplaces.

## Related ADR
ADR-04-002 (see `28_ADR.md`)

## Related Domain Objects
PresenceRecord, ServiceSession, Exception
