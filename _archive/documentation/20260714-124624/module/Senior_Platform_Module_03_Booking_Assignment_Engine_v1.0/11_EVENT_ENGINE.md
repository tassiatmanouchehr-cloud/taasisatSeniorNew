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

# 11 — Event Engine

## Purpose
Define the events Module 03 emits so downstream consumers (dashboards, notifications, Module 04) can react without tight coupling, continuing the event-driven foundation established in Module 01.

## Business Goal
Guarantee that every meaningful booking/coordination change is observable and reactable in real time.

## Functional Specification

### Event Catalogue

```text
SelectionLockCreated
SelectionLockRenewed
SelectionLockExpired
SelectionLockReleased

ProviderCommitmentRequested
ProviderCommitmentAccepted
ProviderCommitmentRejected
ProviderCommitmentTimedOut

ServiceAssignmentCreated
ServiceAssignmentConfirmed
ServiceAssignmentReplaced
ServiceAssignmentFailed
ServiceAssignmentCancelled

ServiceCaseCreated
ServiceCaseConfirmed
ServiceCaseOnHold
ServiceCaseReleased
ServiceCaseCancelled

ServiceSessionScheduled
ReminderSent
ProviderEnRouteSignalled
ProviderNonResponseEscalated
ArrivalCheckSent
ProviderArrived
ServiceStarted
```

### Consumers

- Notification Engine (`12_NOTIFICATION_ENGINE.md`)
- Role Dashboards (`16_UI_SCREEN_CATALOG.md`)
- Module 04 (subscribes to `ServiceStarted` as its entry trigger)
- Audit log (every event is persisted for traceability, BR-329)

## Business Rules
Every event listed above must be persisted with actor, timestamp, and payload (BR-329, BR-330).

## Non-Functional Requirements
- Events must be emitted synchronously with the state change that causes them (no "eventually consistent" gaps for booking-critical events).
- Event payloads must carry enough context for a consumer to act without an extra lookup for the common case.

## Edge Cases (structural, non-legal)
- `ProviderNonResponseEscalated` must not fire more than once per non-response window (avoid alert spam) but must be able to re-fire if the situation repeats for a later Session.

## Future Extension
- AI Decision Engine (referenced in the project's overall Engine list) subscribing to commitment and escalation events for smarter dispatch suggestions.

## Open Questions
- Whether `ServiceCaseOnHold` should automatically pause Session reminders or require an explicit separate pause action is not fully decided; current design assumes automatic pause (see `06_STATE_MACHINES.md`).

## Related ADR
ADR-03-10 (see `20_ADR.md`)

## Related Domain Objects
ServiceCase, ServiceAssignment, ServiceSession, SelectionLock, ManualHold
