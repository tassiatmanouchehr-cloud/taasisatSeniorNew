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

# 03 — Product Specification

## Purpose

Design the complete Service Execution lifecycle: everything that happens from the moment a provider starts a Service Session to the moment it is closed and handed back to the Service Case, in a way that is reusable across any future service marketplace, not just reference implementation.

## Business Goal

Guarantee that "the service happened" is provable, auditable, and mutually confirmed — while keeping the core execution engine domain-neutral so future marketplaces can reuse it by changing only the reference implementation mapping layer.

## Terminology (Ubiquitous Language, Core / reference implementation)

| Core Platform Term | reference implementation Mapping |
|---|---|
| Customer | Customer or Customer Delegate |
| Provider | Independent Provider / Organization Provider |
| Organization | Organization |
| Service Session | Service Session |
| Activity | اقدام مراقبتی |
| Observation | مشاهده وضعیت Customer |
| Evidence | عکس، امضا، مدرک مراقبتی |
| Customer Confirmation | تایید Customer یا خانواده |
| Operational Review | تماس Organization یا تیم Platform Owner |
| Interaction | هر نوع تعامل عملیاتی بین طرفین |
| Exception | هر وضعیت غیرعادی در طول اجرا |

## Actors

- Customer (Customer / خانواده)
- Provider (Independent Provider / Organization Provider)
- Organization (Organization)
- Platform Team (تیم Platform Owner)
- System

## Functional Specification

### FR-401 — Ten Sub-Engine Decomposition
Module 04 is designed as ten sub-engines (five Primary, five Supporting) rather than one monolithic workflow, so future implementations can omit Supporting engines they don't need.

### FR-402 — Session Start Requirements
A Service Session may only enter execution after presence verification, GPS capture (mandatory for reference implementation, configurable in Core), customer confirmation (or a recorded exception), a completed start checklist, and configured evidence (photo/signature).

### FR-403 — During-Session Recording
During execution, the provider may record notes, tasks, observations, photos, vitals, medication usage, delays, temporary leave, and support calls, in any number, all entering the Timeline.

### FR-404 — Early Completion Allowed
If work genuinely finishes early, the provider may complete the session early with no special exception required (BR-04-008).

### FR-405 — Operational Problem Path
Operational problems are primarily resolved through Operational Calls; intervention during execution is limited to Organization and Platform Team (not arbitrary third parties).

### FR-406 — Two-Sided Completion
Completion requires both provider completion and customer confirmation; the provider cannot close a session alone.

### FR-407 — No Financial Output
Module 04 produces zero financial output. It only produces an Execution Completion Event for future financial modules.

### FR-408 — Immutable Execution Records (ADR-04-001)
Once a Provider records an execution record, it is immutable. No one — including Organization and Platform Team — may edit or delete it. They may only add: Review, Internal Note, Correction, Administrative Comment, Dispute, Verification Result, Audit Result.

### FR-409 — Universal Interaction Model (ADR-04-009)
All actor-to-actor operational exchanges (messages, approvals, confirmations, ratings, escalations) are modeled as a single Interaction type, not as a bespoke messaging system.

### FR-410 — Independent Exception Lifecycle (ADR-04-010)
Exceptions are independent entities with their own state machine, timeline, interactions, evidence, and audit trail — decoupled from Session state, so the same engine can later serve complaints, quality, and disputes.

### FR-411 — Platform-Controlled Communication (ADR-04-008)
All operational communication between customer and provider happens inside the platform; real phone numbers are never revealed to each other.

### FR-412 — Session Completion ≠ Business Completion (ADR-04-012)
Completing one session never implies the Service Case, contract, or payment is complete.

## Non-Functional Requirements

- Event-driven throughout (Action → Event → Interaction → Decision → State Change → Timeline → Notification).
- Immutability and audit-by-design for every operational record.
- Configuration over hardcoding (GPS mandatory/optional, evidence required/optional, checklist templates — all configurable by Organization / Service Type / Risk Level).
- Event-based location capture by default, not continuous tracking (privacy, battery, cost).
- Domain isolation: Core Platform code must never reference reference implementation-specific meaning.

## MVP Philosophy

Version 1 must prove execution happened, keep every actor accountable, and stay strictly domain-neutral at the Core layer — while deferring legally sensitive crisis scenarios and all financial logic to dedicated future modules.
