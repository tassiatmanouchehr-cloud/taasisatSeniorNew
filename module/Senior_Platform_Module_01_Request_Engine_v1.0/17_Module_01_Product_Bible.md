# Generic Service Marketplace Framework — Module 01: Request Engine

**Version:** v1.0  
**Status:** Frozen / Approved  
**Project:** Generic Service Marketplace Framework  
**Module Owner:** Platform Architecture Team  
**Language:** Persian business domain, English technical structure  

> Module 01 — Request Engine is the intake foundation of the Generic Service Marketplace Framework. It is frozen and treated as the baseline for all downstream modules (Matching, Provider, Company, Payment, and others). Later modules must not change Module 01 decisions unless a major architectural conflict is discovered.


# Module 01 Product Bible

## Executive Summary

Module 01 — Request Engine is the foundation of the Generic Service Marketplace Framework Reference Implementation platform. It turns a family's care need into a structured, validated, published request and manages that request's whole life from birth to close. It is deliberately designed as a workflow engine, not an order form, because everything downstream (matching, contract, payment) depends on the quality of what happens here.

The module is built for trust, privacy, operational fairness, event-driven scalability, and long-term extension.

## Product Philosophy

The platform assists families but protects a fair process for everyone.

Two platform-wide principles are established in this module:

```text
Principle 1 — Need-to-Know:
  Show the right information, to the right people,
  at the right time, only as much as necessary.

Principle 2 — Platform First:
  Not customer-first, not provider-first.
  The platform protects a fair process.
  No one is always right; a fair process is always right.
```

System behavior:

```text
Let a family describe a need simply
Collect information and files safely
Validate before publishing
Publish only to the right providers
Track the request's whole life as events
Protect the platform from being bypassed
Hand a clean request to Module 02
```

## Key Frozen Decisions

1. Request creation is step-by-step.
2. Guests can build a request; identity is captured at the final step.
3. Form-first interface with text, photo, and video (compressed, size-limited).
4. AI suggests file types; the user confirms or corrects them.
5. A request may contain multiple service needs.
6. A request must be validated before publishing.
7. Publishing is need-to-know and bounded, never a blind fan-out.
8. Providers see new-request counts; behaviour is recorded for future ranking.
9. The request follows an explicit life cycle.
10. Editing after creation re-confirms or re-notifies depending on status.
11. A single service need can be removed without cancelling the request.
12. Deletion is free before acceptance and always recorded.
13. No-selection timeout ladder: 24h reminder → phone → auto-delete with retention.
14. Selected providers get a pre-appointment reminder plus an arrival check.
15. Recurring needs are Contracts of Sessions; single sessions can be cancelled.
16. Provider unavailability triggers replacement plus platform assistance.
17. All roles can cancel under rules; repeated abuse is penalized.
18. Platform protection (anti-bypass) begins at request time.
19. The system is event-driven.
20. Every request has a role-filtered timeline.
21. GPS is deferred to a later phase.
22. Module 01 ends at a published request handed to Module 02.

## Final Architecture

```text
Request Start
        ↓
Information Collection (form + files + AI classify)
        ↓
Validation
        ↓
Request Creation (event: RequestCreated)
        ↓
Targeted Publishing
        ↓
Applications Collected
        ↓
Module 02 — Matching Engine
```

Cross-cutting layers: Workflow/Status Engine, Event Layer, Contract & Scheduling, Timeline, Platform Protection.

## MVP Implementation Priorities

### Phase 1

- Step-by-step request creation with guest start
- Attachments with compression and AI type confirmation
- Multi-service-need requests
- Validation
- Targeted publishing
- Applications collection
- Request life cycle and timeline
- Event emission

### Phase 2

- Editing rules and re-confirmation
- No-selection timeout ladder
- Selected-provider follow-up
- Contract / sessions and single-session cancellation
- Cancellation penalties
- Admin settings and audit

### Phase 3

- Platform protection detection (chat / image / PDF / price / cancel-after-arrival)
- Richer customer history
- Behaviour signal capture for future ranking

### Future

- Smart distribution
- Live GPS
- AI-assisted request understanding

## Development Notes

Do not implement the Request Engine as one giant function.

Recommended services:

- RequestDraftService
- AttachmentService (+ AI classifier)
- ValidationService
- PublishingService
- WorkflowService
- ContractService
- TimelineService
- EventBus
- ProtectionService

## Quality Bar

A feature is not complete unless:

- It respects the need-to-know principle.
- It is testable.
- It has explainable validation/publishing behavior.
- It handles failure and edge states.
- It is permission-controlled if admin-facing.
- It emits events and writes timeline entries where relevant.
- It creates audit logs when manually changed.

## Freeze Statement

Module 01 met all four exit criteria — Business Complete, Edge Cases Complete, Enterprise Ready, Future Ready — and answered the scale question (100k requests/day) affirmatively. It is now architecturally frozen. Future changes are handled as explicit ADRs unless a major architectural conflict is discovered. Next: Module 02 — Matching Engine.
