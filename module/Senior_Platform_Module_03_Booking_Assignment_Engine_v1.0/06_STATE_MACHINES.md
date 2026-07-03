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

# 06 — State Machines

## 1. Selection Lock State

```text
LOCKED
  ↓
RENEWED (optional, if configured)
  ↓
CONSUMED (provider committed)
```

Alternative:

```text
LOCKED → EXPIRED → RELEASED (returns toward Matching)
```

## 2. Provider Commitment State

```text
PENDING_COMMITMENT
  ↓
ACCEPTED
```

Alternatives:

```text
PENDING_COMMITMENT → REJECTED
PENDING_COMMITMENT → TIMED_OUT
```

## 3. Service Assignment State

```text
CREATED
  ↓
CONFIRMED
  ↓
ACTIVE
```

Alternatives:

```text
CREATED → FAILED (commitment rejected/timed out)
CONFIRMED → REPLACED (provider substituted)
CONFIRMED → CANCELLED
```

## 4. Service Case State

```text
DRAFT
  ↓
CONFIRMING
  ↓
CONFIRMED
  ↓
COORDINATING
  ↓
READY_TO_START
  ↓
SERVICE_STARTED  ← handoff to Module 04
```

Alternatives:

```text
CONFIRMING → FAILED (no commitment reached)
CONFIRMED / COORDINATING → ON_HOLD (manual hold, BR-326)
ON_HOLD → COORDINATING / CANCELLED
any pre-start state → CANCELLED
```

## 5. Service Session State

```text
SCHEDULED
  ↓
REMINDER_SENT
  ↓
EN_ROUTE_SIGNALLED
  ↓
ARRIVED
  ↓
SERVICE_STARTED
```

Alternatives:

```text
SCHEDULED → RESCHEDULED
REMINDER_SENT → NO_RESPONSE → ESCALATED (BR-318)
any pre-start state → CANCELLED
```

## 6. Manual Hold State

```text
NONE
  ↓
ON_HOLD
  ↓
RELEASED / CANCELLED
```
