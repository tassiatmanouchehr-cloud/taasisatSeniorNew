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

# 04 — Architecture

## Architectural Style

Module 03 is an event-driven booking/coordination subsystem sitting between the decision layer (Module 02) and the execution layer (Module 04). It is structurally split into three parallel commitment paths sharing a common Service Case / Assignment / Session core.

## Main Pipeline

```text
Module 02 → Customer Selected Candidate / Selection Lock
        ↓
Selection Lock Management
        ↓
Provider Commitment  ─┬─ Independent Provider Path
                       ├─ Company Provider Path
                       └─ Company Package Path
        ↓
Assignment Creation (Assignment / Assignment Plan)
        ↓
Service Case Creation
        ↓
Session Scheduling
        ↓
Pre-Service Coordination (reminder → en route → arrival)
        ↓
Service Started  →  Module 04
```

## Selection Lock Layer

Owns TTL, renewal, expiry, and release-back-to-matching behavior. Configurable by Platform Owner.

## Provider Commitment Layer

Three independent strategies behind a common interface:

- `IndependentProviderCommitmentStrategy`
- `CompanyProviderCommitmentStrategy`
- `CompanyPackageCommitmentStrategy`

Each returns Confirmed / Rejected / TimedOut, with reasons.

## Assignment & Service Case Layer

Builds Assignments (and Assignment Plans for multi-need requests), then a Service Case that aggregates them.

## Session Layer

Generates the first Session immediately on confirmed timing; generates the full recurring schedule for Contracts (from Module 01).

## Coordination Layer

Drives reminders, en-route signalling, and arrival checks; escalates to direct contact plus company involvement when a provider is silent close to appointment time (BR-318).

## Manual Intervention Layer

Supports hold, manual assignment, lock extension, and override — always transparent and audited (mirrors Module 02's manual-intervention design).

## Dashboard Layer

Publishes live, role-specific views (customer, provider, company, Platform Owner) from Service Case / Assignment / Session state and events — see `16_UI_SCREEN_CATALOG.md`.

## Event Layer

All meaningful transitions are emitted as events (see `11_EVENT_ENGINE.md`) so Module 04, notifications, and dashboards react without tight coupling.

## Performance Approach

- Precompute dashboard read models from events rather than recomputing on every view.
- Run escalation checks (BR-318, BR-303) as scheduled background jobs, not blocking requests.
- Index Service Cases and Assignments by status and appointment time for fast coordination queries.

## Module Boundary

Module 03 ends when the "Service Started" event is recorded (Decision 03-051). Module 04 — Service Execution / Care Delivery Engine owns everything after that point.
