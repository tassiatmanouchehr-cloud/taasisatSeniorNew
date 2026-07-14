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

# 08 — Service Case Specification

## Purpose
Define the Service Case: the single operational record that aggregates everything needed to deliver a confirmed service, from confirmation through to the moment care starts.

## Business Goal
Give every role (customer, provider, company, Platform Owner) one authoritative place that reflects the true, current state of a booked service — eliminating ambiguity about "is this actually happening."

## Functional Specification

- A Service Case is created once at least one Assignment for a request begins confirming (BR-315).
- A Service Case holds: customer reference, service recipient, provider/company reference(s), address, agreed timing, agreed terms (price/range, cancellation terms), linked Assignments, linked Sessions.
- A multi-need request produces one Service Case with multiple Assignments, which may be in different states simultaneously (e.g. one need confirmed, another still pending commitment).
- A Service Case exposes live status to the customer's and provider's own panels (FR-307); no separate one-time confirmation screen is required.
- A Service Case can be placed ON_HOLD by Platform Owner/support before it reaches READY_TO_START (FR-308, BR-326).
- A Service Case's Module 03 lifecycle ends the instant "Service Started" is recorded (BR-331); after that, Module 04 owns it.

## Business Rules
See `03_BUSINESS_RULES.md` — BR-315, BR-316, BR-326, BR-327, BR-331 apply directly.

## Non-Functional Requirements
- Must reflect state changes in near-real-time for dashboards.
- Must remain queryable in a consistent state even while individual Assignments are still resolving.

## Edge Cases (structural, non-legal)
- Mixed-state multi-need case: some needs confirmed, others still pending — Service Case status must clearly reflect partial confirmation, not falsely show fully ready.
- Manual hold placed after coordination has already begun — coordination activities (reminders, en-route) must pause while on hold.

## Future Extension
- GPS-based live location integrated into the Service Case view (explicitly deferred from Module 01 and reaffirmed here).
- AI-assisted risk flags contributing to automatic hold suggestions.

## Open Questions
- Exact SLA for "commitment window" per provider type is not yet numerically fixed; left as a configurable default (see `17_ADMIN_CONFIGURATION.md`).

## Related ADR
ADR-03-04, ADR-03-07, ADR-03-08 (see `20_ADR.md`)

## Related Domain Objects
ServiceAssignment, AssignmentPlan, ServiceSession, SelectionLock, ManualHold
