# Generic Service Marketplace Framework — Module 01: Request Engine

**Version:** v1.0  
**Status:** Frozen / Approved  
**Project:** Generic Service Marketplace Framework  
**Module Owner:** Platform Architecture Team  
**Language:** Persian business domain, English technical structure  

> Module 01 — Request Engine is the intake foundation of the Generic Service Marketplace Framework. It is frozen and treated as the baseline for all downstream modules (Matching, Provider, Company, Payment, and others). Later modules must not change Module 01 decisions unless a major architectural conflict is discovered.


# State Machines

## 1. Request Life Cycle

```text
DRAFT
  ↓
WAITING_FOR_VALIDATION
  ↓  (validation fails → back to DRAFT with reasons)
PUBLISHED
  ↓
RECEIVING_APPLICATIONS
  ↓
WAITING_FOR_CUSTOMER_SELECTION
  ↓
PROVIDER_SELECTED
  ↓
CONFIRMED
  ↓
SERVICE_STARTED
  ↓
COMPLETED
```

Cancellation / deletion branches:

```text
DRAFT → DELETED (free, before acceptance)
PUBLISHED / RECEIVING_APPLICATIONS → DELETED (free, no provider accepted yet)
WAITING_FOR_CUSTOMER_SELECTION → 24h reminder → phone follow-up → AUTO_DELETED (retained in history)
PROVIDER_SELECTED / CONFIRMED → CANCELLED (rule-based, penalties may apply)
```

Rules:

- A request may be deleted freely while no provider has been accepted.
- After a provider is selected, cancellation is rule-based and may trigger penalties.
- Deleted / auto-deleted requests remain in the customer history.

## 2. Application State (provider side)

```text
APPLIED
  ↓
IN_SELECTION_QUEUE
  ↓
SELECTED → CONFIRMED
```

Alternatives:

```text
APPLIED → WITHDRAWN
APPLIED → NOT_SELECTED (another provider chosen or request deleted)
```

## 3. Contract & Session State

```text
CONTRACT_ACTIVE
  ↓
SESSION_SCHEDULED
  ↓
SESSION_DONE
```

Alternatives:

```text
SESSION_SCHEDULED → SESSION_CANCELLED (single session)
SESSION_SCHEDULED → PROVIDER_UNAVAILABLE → REPLACEMENT_PROPOSED → SESSION_SCHEDULED
CONTRACT_ACTIVE → CONTRACT_CANCELLED
```

## 4. Attachment Classification State

```text
UPLOADED
  ↓
AI_SUGGESTED_TYPE
  ↓
USER_CONFIRMED / USER_CORRECTED
```

Rule: a medical file type is never finalized without user confirmation.

## 5. Selected-Provider Follow-Up State

```text
SELECTED
  ↓
PRE_APPOINTMENT_REMINDER_SENT  (~1h before)
  ↓
ARRIVAL_CHECK_SENT  (at appointment time, to customer)
  ↓
ARRIVED / DELAYED / NO_SHOW
```

## 6. Protection Signal State

```text
DETECTED
  ↓
FLAGGED
  ↓
REVIEWED → ACTIONED / DISMISSED
```
