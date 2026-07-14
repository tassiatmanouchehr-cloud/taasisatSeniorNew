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

# 19 — Product Bible Update

## Executive Summary

Module 03 — Booking, Assignment & Service Activation Engine converts a customer's locked selection (from Module 02) into a real, provider-committed, coordinated Service Case, ending precisely when care actually begins. It is the module that makes "selected" mean "someone is really coming."

## Key Frozen Decisions (Module 03)

1. Module 03 begins at Selection Lock and ends at Service Started (Decision 03-051).
2. Module 03 is not responsible for Matching, Ranking, or Eligibility (Decision 03-002).
3. Module 03 is responsible for converting selection into a Confirmed Service Assignment (Decision 03-003).
4. Payment, settlement, and invoicing are out of scope (Decision 03-004).
5. Real care delivery and in-service reporting are out of scope (Decision 03-005).
6. Three separate commitment paths are required: independent provider, company provider, company package (Decision 03-006).
7. No redundant pre-service summary/confirmation screen is built; live dashboards suffice (scenario 1 decision).
8. Platform Owner's team can hold a Service Case before start if risk is identified (scenario 2 decision).
9. Provider silence near appointment time triggers immediate direct contact plus company involvement (scenario 3 decision, BR-318).
10. Role dashboards (customer, provider, company, Platform Owner) are a first-class Module 03 deliverable.
11. The legally sensitive crisis-scenario library is explicitly deferred pending legal consultation.
12. From Module 03 onward, documentation is produced as a versioned package with per-file headers (Depends On / Next Modules) and a fixed enriched section template.

## Final Architecture (Module 03)

```text
Module 02 → Selection Lock
        ↓
Provider Commitment (3 paths)
        ↓
Service Assignment / Assignment Plan
        ↓
Service Case
        ↓
Session Scheduling & Pre-Service Coordination
        ↓
Service Started → Module 04
```

## MVP Implementation Priorities

### Phase 1
- Selection Lock management
- Three commitment paths
- Assignment / Assignment Plan / Service Case creation
- First-session scheduling

### Phase 2
- Pre-service coordination (reminders, en-route, arrival check, escalation)
- Manual hold and manual override
- Role dashboards
- Audit trail

### Phase 3
- Recurring contract full-schedule coordination at scale
- Refined escalation timing tuning

### Future / Deferred
- Legal-reviewed crisis-scenario library
- GPS-based live coordination
- AI-assisted dispatch and risk flags

## Quality Bar

A feature is not complete unless it respects the Module 03 boundary (Selection Lock → Service Started), is testable, handles the decided structural failure/recovery cases, is permission-controlled if admin-facing, and creates an audit log when manually changed.

## Freeze Statement

Module 03 met the project's freeze bar for all decided scope; the legal crisis-scenario catalogue is intentionally carried forward as an open issue rather than blocking the freeze. Module 03 is considered architecturally frozen for its decided scope. Next: Module 04 — Service Execution / Care Delivery Engine.
