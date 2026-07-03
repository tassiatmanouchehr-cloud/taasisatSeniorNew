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

# 14 — API Contract

> Contracts are conceptual. Final endpoint naming depends on implementation stack.

## Customer / Family APIs

### GET /service-cases/{service_case_id}
Returns live Service Case status (replaces the need for a separate one-time summary screen — FR-307).

### GET /service-cases/{service_case_id}/sessions
Returns the session schedule and live status.

### POST /service-cases/{service_case_id}/withdraw
Withdraws before service start (subject to Module 01 cancellation rules).

Errors:
- SERVICE_ALREADY_STARTED
- WITHDRAWAL_NOT_ALLOWED

## Provider APIs

### GET /provider/commitments/pending
Returns pending commitment requests for the provider.

### POST /provider/commitments/{commitment_id}/accept
Accepts a commitment request.

### POST /provider/commitments/{commitment_id}/reject
Rejects a commitment request.

### POST /provider/sessions/{session_id}/en-route
Signals "on the way."

### POST /provider/sessions/{session_id}/start-service
Records Service Started (Module 03 → Module 04 handoff).

## Company APIs

### GET /company/commitments/pending
Returns pending commitment requests owned by the company.

### POST /company/commitments/{commitment_id}/accept
Accepts at the company level.

### POST /company/assignments/{assignment_id}/assign-provider
Assigns or substitutes a provider for a company / company-package Assignment (BR-309, BR-310).

### GET /company/dispatch/today
Returns today's dispatches, en-route staff, and problem cases (dashboard).

## Admin APIs

### PATCH /admin/booking/settings
Updates selection lock TTL, commitment window, escalation threshold, hold policy.

### POST /admin/service-cases/{service_case_id}/hold
Places a Service Case on hold with a reason.

### POST /admin/service-cases/{service_case_id}/release-hold
Releases a hold.

### POST /admin/service-assignments/{assignment_id}/manual-assign
Manually creates or overrides an Assignment (audited).

### POST /admin/selection-locks/{lock_id}/extend
Manually extends a Selection Lock.

### GET /admin/service-cases/{service_case_id}/audit
Returns full audit trail.

## Internal Services

### SelectionLockService.manage(lock)
Handles TTL, renewal, expiry, release.

### CommitmentService.requestCommitment(need, candidate, path)
Runs the correct commitment strategy for the path (independent / company provider / company package).

### AssignmentService.createAssignment(commitment)
Creates a Service Assignment (or plan entry) on successful commitment.

### CoordinationService.coordinate(session)
Drives reminders, en-route tracking, and escalation (BR-318).

### EscalationService.checkNonResponse(session)
Scheduled job implementing BR-318/BR-303.

### EventBus.emit(event)
Emits Module 03 domain events (see `11_EVENT_ENGINE.md`).
