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

# 08 — Flows

## Flow 1 — Standard Session Execution (Happy Path)

```text
Module 03 hands off "Service Started"
↓
Provider declares en route (GPS captured)
↓
Provider arrives (distance validated)
↓
Start Checklist runs (presence, customer confirmation, checklist items, evidence)
↓
Session enters IN_PROGRESS
↓
Provider records activities, observations, evidence throughout
↓
Provider marks PROVIDER_COMPLETED
↓
Customer confirms → CUSTOMER_CONFIRMED
↓
Session CLOSED → Handover updates Service Case
↓
Events emitted for Module 05/06
```

## Flow 2 — GPS Problem During En Route

```text
Provider cannot capture GPS
↓
Provider reports GPS problem (reason, device status, note, optional photo, optional customer confirmation)
↓
System applies configured mismatch behavior:
  BLOCK_START / ALLOW_WITH_REASON / ALLOW_WITH_CUSTOMER_CONFIRMATION /
  ALLOW_WITH_ORGANIZATION_APPROVAL / SEND_TO_OPERATIONAL_REVIEW
```

## Flow 3 — Customer Unavailable at Start

```text
Provider arrives, customer does not respond
↓
Session → CUSTOMER_UNAVAILABLE
↓
Exception created (owner: Organization or Platform Team)
↓
Resolution recorded (even if "No Action Required")
```

## Flow 4 — Pause and Resume

```text
IN_PROGRESS
↓
Pause requested (reason, actor, timestamp, optional expected resume time)
↓
PAUSED
↓
Resume → IN_PROGRESS
```

## Flow 5 — Unauthorized Departure

```text
Provider leaves location mid-session
↓
Classified as: temporary leave (authorized) / unauthorized departure (not authorized) / operational review (unclear)
↓
If unauthorized: Exception created, Session may move to INTERRUPTED
```

## Flow 6 — Overtime / Extension Request

```text
Provider or Customer requests extension
↓
Counterpart approval requested
↓
If both agree → APPROVED → APPLIED (session plan updated: end time, duration, timeline)
↓
If not agreed → Organization / Platform Team intervenes (Operational Review)
↓
Extension record closed (immutable); price impact explicitly recorded, but not invoiced here
```

## Flow 7 — Completion & Customer Confirmation

```text
Provider marks PROVIDER_COMPLETED (completion note, final checklist, final evidence)
↓
Customer asked to confirm
↓
If confirmed → CUSTOMER_CONFIRMED → CLOSED
↓
If customer cannot confirm → provider submits confirmation problem request →
  Organization or Platform Team calls customer → resolution recorded
```

## Flow 8 — Exception Running in Parallel to Session

```text
Exception created (e.g. "customer not home") tied to a Session
↓
Exception has its own state machine: OPEN → UNDER_REVIEW → WAITING_* → RESOLVED → CLOSED
↓
Session state changes independently (e.g. remains IN_PROGRESS or moves to PAUSED)
↓
Exception resolution recorded; Exception closed (never deleted)
```

## Flow 9 — Handover to Service Case

```text
Session CLOSED
↓
Service Case updated: remaining sessions, progress, next planned session, completion statistics
↓
Events: session_closed, session_handed_over, service_case_updated,
        next_session_ready, customer_feedback_available
↓
Financial processing (invoice/settlement/payout) deferred entirely to Module 05/06
```

## Flow 10 — Interaction as the Universal Exchange Pattern

```text
Any actor-to-actor exchange (message, approval, confirmation, rating, escalation)
↓
Created as an Interaction: CREATED → DELIVERED → VIEWED → RESPONDED → RESOLVED → CLOSED
                             (or → EXPIRED / → ESCALATED)
↓
Same engine reused for future modules: invoice approval, payment confirmation,
  complaint, quality review, dispute resolution, refund approval
```
