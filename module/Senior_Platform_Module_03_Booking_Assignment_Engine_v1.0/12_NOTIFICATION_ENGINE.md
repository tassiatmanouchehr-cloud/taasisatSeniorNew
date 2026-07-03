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

# 12 — Notification Engine

## Purpose
Define how Module 03 events reach customers, providers, companies, and Platform Owner's team through the platform's configurable notification channels (Push, SMS, Email, In-App — established in Module 02).

## Business Goal
Make sure no booking-critical moment (commitment needed, commitment failed, provider silent, arrival check) goes unnoticed by the party who needs to act.

## Functional Specification

| Event | Primary Recipient | Channel (default) | Escalation |
|---|---|---|---|
| ProviderCommitmentRequested | Provider / Company | Push | SMS after non-response window |
| ProviderCommitmentRejected / TimedOut | Customer | Push + In-App | — |
| SelectionLockExpired | Customer | Push + In-App | — |
| ServiceAssignmentConfirmed | Customer, Provider | Push + In-App | — |
| ServiceAssignmentReplaced | Customer | Push + In-App | Support notified if customer had specific-person expectation |
| ReminderSent | Provider | Push | — |
| ProviderNonResponseEscalated | Provider, Company | Push + direct call | Platform Owner dashboard flag |
| ArrivalCheckSent | Customer | Push + In-App | — |
| ServiceCaseOnHold | Customer (as appropriate), Support | In-App | Platform Owner dashboard flag |
| ServiceStarted | Customer, Provider | In-App | — |

## Business Rules
Channel enablement and fallback rules follow Module 02's precedent (BR-241 through BR-245): Push primary, SMS fallback for unopened/urgent, all configurable by Platform Owner.

## Non-Functional Requirements
- Escalation notifications (BR-318) must bypass normal batching/delay and fire immediately.
- Notification failures must be logged and retried via fallback channel.

## Edge Cases (structural, non-legal)
- Provider has notifications disabled at the OS level — escalation must still attempt a direct call per BR-318, not rely solely on push.

## Future Extension
- WhatsApp / IVR / auto-call channels (reserved in Module 02's architecture, applies here too).

## Open Questions
- Exact SMS fallback delay for `ReminderSent` non-acknowledgment is not numerically fixed; configurable default.

## Related ADR
ADR-03-10 (see `20_ADR.md`)

## Related Domain Objects
CoordinationEvent, ServiceCase, ServiceAssignment
