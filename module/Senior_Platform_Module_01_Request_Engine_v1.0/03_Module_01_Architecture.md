# Generic Service Marketplace Framework — Module 01: Request Engine

**Version:** v1.0  
**Status:** Frozen / Approved  
**Project:** Generic Service Marketplace Framework  
**Module Owner:** Platform Architecture Team  
**Language:** Persian business domain, English technical structure  

> Module 01 — Request Engine is the intake foundation of the Generic Service Marketplace Framework. It is frozen and treated as the baseline for all downstream modules (Matching, Provider, Company, Payment, and others). Later modules must not change Module 01 decisions unless a major architectural conflict is discovered.


# Architecture

## 1. Architectural Style

Module 01 is designed as an event-driven, workflow-oriented request subsystem. It is not "just an order form" — it is a **Workflow Engine** for the life of a service request.

Two platform-wide architecture principles are set here:

- **Principle 1 — Need-to-Know:** show the right information, to the right people, at the right time, only as much as necessary.
- **Principle 2 — Platform First:** the platform protects a fair process; it is neither customer-first nor provider-first.

## 2. Main Pipeline

```text
Request Start
        ↓
Information Collection (form + files + AI classify)
        ↓
Validation
        ↓
Request Creation
        ↓
Targeted Publishing
        ↓
Applications Collected
        ↓
Handoff to Module 02 (Matching)
```

## 3. Request Start Layer

Handles guest entry, service-first or service-recipient-first paths, and defers identity capture to the final step.

## 4. Information Collection Layer

Collects structured form data plus optional free text, photos, and video. Attachments are compressed and size-limited. An assistive AI classifier suggests a file type; the user confirms or corrects it.

## 5. Validation Layer

Answers:

```text
Sufficient / Insufficient (with reasons)
```

It blocks publishing until the request has enough information.

## 6. Request Creation Layer

Persists the request and its service needs, assigns a tracking number, and emits `RequestCreated`.

## 7. Publishing / Distribution Layer

Publishes to eligible providers using a bounded, most-relevant strategy rather than broadcasting to everyone.

MVP:

```text
TARGETED_BY_SERVICE_AND_CITY (bounded subset)
```

Future:

```text
SMART_DISTRIBUTION (AI-selected recipients)
```

## 8. Workflow / Status Engine

Owns the request status machine (Draft → … → Completed / Cancelled) and enforces edit, cancel, and timeout transitions.

## 9. Event Layer (Event-Driven Foundation)

Every meaningful action becomes an event:

```text
RequestCreated
ProviderApplied
CustomerUpdatedAddress
ProviderConfirmed
ReminderSent
CustomerConfirmedArrival
Completed
RequestCancelled
```

Downstream modules subscribe to these events instead of being called directly.

## 10. Contract & Scheduling Layer

Splits recurring needs into a Contract that contains Sessions, supporting single-session cancellation and mid-contract replacement.

## 11. Timeline Layer

Builds a role-filtered chronological timeline for family, provider, company, support, and owner.

## 12. Platform Protection Layer

Runs alongside the request from creation: detects off-platform bypass attempts (phone numbers in chat/photo/PDF, external price agreement, cancel-after-arrival abuse) and raises protection signals.

## 13. Performance Approach

To stay fast at 100k+ requests/day:

- Emit events and let downstream work happen asynchronously.
- Publish to a bounded recipient subset instead of fan-out to all providers.
- Index requests by service, city/coverage, and status.
- Compress and offload media; never block request creation on heavy file work.
- Run AI file classification and protection scanning as background jobs.

## 14. Module Boundary

Module 01 ends when a validated request is published and applications begin to arrive. Module 02 — Matching Engine owns eligibility scoring, ranking, and candidate presentation from there.
