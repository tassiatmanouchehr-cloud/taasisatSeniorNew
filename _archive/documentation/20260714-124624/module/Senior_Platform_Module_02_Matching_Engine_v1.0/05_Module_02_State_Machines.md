# Generic Service Marketplace Framework — Module 02: Matching Engine

**Version:** v1.0  
**Status:** Frozen / Approved  
**Project:** Generic Service Marketplace Framework  
**Module Owner:** Platform Architecture Team  
**Language:** Persian business domain, English technical structure  

> Module 01 — Request Engine is frozen and is treated as baseline. Module 02 must not change Module 01 decisions unless a major architectural conflict is discovered.


# State Machines

## 1. Provider Lifecycle

```text
REGISTERED
  ↓
PROFILE_INCOMPLETE
  ↓
PENDING_REVIEW
  ↓
PENDING_DOCUMENTS ↔ PENDING_REVIEW
  ↓
APPROVED
  ↓
ACTIVE
  ↓
TEMPORARILY_UNAVAILABLE ↔ ACTIVE
  ↓
SUSPENDED → UNDER_APPEAL → PENDING_REVIEW / ACTIVE / TERMINATED
  ↓
DEACTIVATED → PENDING_REVIEW → ACTIVE
  ↓
TERMINATED
```

Rules:

- `TERMINATED` is practically irreversible except by high-level Platform Owner decision.
- `SUSPENDED` removes public visibility and matching eligibility.

## 2. Match Round State

```text
CREATED
  ↓
ELIGIBILITY_RUNNING
  ↓
DISTRIBUTING
  ↓
WAITING_FOR_RESPONSES
  ↓
HAS_ACCEPTED_CANDIDATES
  ↓
CUSTOMER_SELECTION_PENDING
  ↓
SELECTED
```

Failure/expiry:

```text
WAITING_FOR_RESPONSES → NO_CANDIDATES_ACCEPTED → MANUAL_INTERVENTION
CUSTOMER_SELECTION_PENDING → EXPIRED
EXPIRED → REOPENED → DISTRIBUTING
```

## 3. Candidate Response State

```text
SENT
  ↓
ACCEPTED
  ↓
WITHDRAWN
```

Alternative:

```text
SENT → REJECTED
SENT → EXPIRED
```

## 4. Customer Selection State

```text
NOT_SELECTED
  ↓
SELECTION_LOCKED
  ↓
HANDOFF_TO_MODULE_03
```

Rules:

- Only one active selection per service need.
- Concurrent selections are rejected after first successful lock.

## 5. Notification State

```text
PENDING
  ↓
SENT
  ↓
DELIVERED / FAILED
  ↓
OPENED / NOT_OPENED
  ↓
FALLBACK_SENT
```

Fallback channels depend on Platform Owner configuration.
