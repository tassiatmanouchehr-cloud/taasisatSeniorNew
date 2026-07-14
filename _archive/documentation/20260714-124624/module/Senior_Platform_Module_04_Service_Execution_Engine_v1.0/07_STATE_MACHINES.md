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

# 07 — State Machines

## 1. Session Lifecycle (Primary Engine)

### Core Path

```text
SCHEDULED
   ↓
PROVIDER_EN_ROUTE
   ↓
PROVIDER_ARRIVED
   ↓
START_CHECK_PENDING
   ↓
IN_PROGRESS
   ↓
PROVIDER_COMPLETED
   ↓
CUSTOMER_CONFIRMATION_PENDING
   ↓
CUSTOMER_CONFIRMED
   ↓
CLOSED
```

### Exception States

```text
START_BLOCKED
PAUSED
INTERRUPTED
CUSTOMER_UNAVAILABLE
OPERATIONAL_REVIEW_REQUIRED
COMPLETION_DISPUTED
CANCELLED_DURING_EXECUTION
```

### State Definitions (summary)

- **SCHEDULED** — Session created, not yet executing. Allowed actors: Provider, Organization, Platform Team. Next: PROVIDER_EN_ROUTE, CANCELLED_DURING_EXECUTION. Event: `session_ready_for_execution`.
- **PROVIDER_EN_ROUTE** — Provider declares moving toward the address. Requires timestamp, GPS, provider identity, target address reference (GPS mandatory for reference implementation). Next: PROVIDER_ARRIVED, START_BLOCKED, OPERATIONAL_REVIEW_REQUIRED. Events: `provider_en_route`, `provider_location_captured`.
- **PROVIDER_ARRIVED** — Provider declares arrival. Requires GPS, arrival timestamp, distance validation, optional photo/evidence. Next: START_CHECK_PENDING, START_BLOCKED, CUSTOMER_UNAVAILABLE, OPERATIONAL_REVIEW_REQUIRED. Events: `provider_arrived`, `arrival_verified`, `arrival_location_mismatch`.
- **START_CHECK_PENDING** — Pre-start checks run: customer availability, customer confirmation, start checklist, required evidence, optional signature, service-specific requirements. Next: IN_PROGRESS, START_BLOCKED, CUSTOMER_UNAVAILABLE, OPERATIONAL_REVIEW_REQUIRED. Events: `start_check_started`, `start_check_completed`, `start_check_failed`.
- **IN_PROGRESS** — Session formally started; provider performing service. Allowed actions: add activity, add note, add observation, add evidence, request support, report issue, request overtime, request temporary leave, complete session. Next: PAUSED, INTERRUPTED, PROVIDER_COMPLETED, OPERATIONAL_REVIEW_REQUIRED, CANCELLED_DURING_EXECUTION. Events: `session_started`, `session_in_progress`.
- **PAUSED** — Temporarily stopped with a recorded reason (e.g. customer temporarily unavailable, approved temporary leave, operational waiting). Requires pause reason, actor, timestamp, optional expected resume time. Next: IN_PROGRESS, INTERRUPTED, OPERATIONAL_REVIEW_REQUIRED. Events: `session_paused`, `session_resumed`.
- **INTERRUPTED** — Abnormally stopped (unauthorized departure, customer refuses continuation, unsafe condition, dispute, serious operational issue). Next: IN_PROGRESS, OPERATIONAL_REVIEW_REQUIRED, CANCELLED_DURING_EXECUTION, PROVIDER_COMPLETED. Event: `session_interrupted`.
- **PROVIDER_COMPLETED** — Provider declares work done. Requires completion timestamp, completion note, final checklist if configured, final evidence if required, request for customer confirmation. Rule: provider cannot close the session directly. Next: CUSTOMER_CONFIRMATION_PENDING, OPERATIONAL_REVIEW_REQUIRED. Events: `session_completed_by_provider`, `customer_confirmation_requested`.
- **CUSTOMER_CONFIRMATION_PENDING** — Awaiting customer confirmation. Customer actions: confirm completion, submit feedback, rate service, report dispute, indicate payment status if applicable. If customer cannot confirm, provider submits a confirmation problem request, then Organization or Platform Team calls the customer. Next: CUSTOMER_CONFIRMED, COMPLETION_DISPUTED, OPERATIONAL_REVIEW_REQUIRED. Events: `customer_confirmation_pending`, `customer_confirmation_failed`, `operational_confirmation_requested`.
- **CUSTOMER_CONFIRMED** — Customer confirmed completion. Requires confirmation timestamp, customer actor, feedback status, optional rating, payment reference status if applicable. Next: CLOSED. Event: `session_completion_confirmed_by_customer`.
- **CLOSED** — Session execution formally closed. Rule: after Closed, execution records never change — only audit notes/administrative records may be added; no financial output is generated; only events are sent to later modules. Events: `session_closed`, `execution_completed`.

## 2. Presence & Location Engine (Supporting)

```text
NOT_TRACKED
   ↓
EN_ROUTE_LOCATION_CAPTURED
   ↓
ARRIVAL_LOCATION_CAPTURED
   ↓
PRESENCE_VERIFIED
   ↓
SESSION_LOCATION_ACTIVE
   ↓
DEPARTURE_CAPTURED
```

Exception states: `GPS_UNAVAILABLE`, `LOCATION_MISMATCH`, `PRESENCE_UNVERIFIED`, `MANUAL_REVIEW_REQUIRED`, `UNAUTHORIZED_DEPARTURE`.

## 3. Execution Activity Lifecycle (Primary)

```text
Created → Available → Started → Completed
Created → Started → Skipped
Created → Failed
```

Status values: PLANNED, AVAILABLE, STARTED, IN_PROGRESS, COMPLETED, SKIPPED, FAILED, CANCELLED.

## 4. Evidence Lifecycle (Supporting)

```text
CAPTURED → ATTACHED → SUBMITTED → ACCEPTED
```

Exception states: `REJECTED`, `FLAGGED`, `UNDER_REVIEW`, `REPLACED_BY_NEW_EVIDENCE`, `ACCESS_RESTRICTED`.

## 5. Interaction Lifecycle (Primary)

```text
CREATED → DELIVERED → VIEWED → RESPONDED → RESOLVED → CLOSED
CREATED → EXPIRED
CREATED → ESCALATED
```

## 6. Exception Lifecycle (Primary, Independent of Session)

```text
OPEN → UNDER_REVIEW → WAITING_INFORMATION / WAITING_CUSTOMER / WAITING_PROVIDER / WAITING_ORGANIZATION / WAITING_PLATFORM → RESOLVED → CLOSED
```

Runs on a state machine fully independent of the Session's own state (BR-04-068).

## 7. Extension & Overtime Lifecycle (Supporting)

```text
REQUESTED → WAITING_COUNTERPART_APPROVAL → APPROVED → APPLIED → CLOSED
```

Exception states: `REJECTED`, `DISPUTED`, `EXPIRED`, `CANCELLED`, `OPERATIONAL_REVIEW_REQUIRED`.

## 8. Completion & Handover Lifecycle (Primary)

```text
PROVIDER_COMPLETED → CUSTOMER_CONFIRMATION_PENDING → CUSTOMER_CONFIRMED → SESSION_CLOSED → HANDOVER_COMPLETED
```

Exception path:

```text
PROVIDER_COMPLETED → DISPUTED → OPERATIONAL_REVIEW → RESOLVED → SESSION_CLOSED
```
