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

# 13 — Data Model

> This is a logical model, not final SQL.

## Tables / Collections

### selection_locks

- id
- request_service_need_id
- match_candidate_id
- status: LOCKED / RENEWED / CONSUMED / EXPIRED / RELEASED
- locked_at
- expires_at

### provider_commitments

- id
- selection_lock_id
- commitment_path: INDEPENDENT_PROVIDER / ORGANIZATION_PROVIDER / ORGANIZATION_PACKAGE
- responsible_party_id (provider_id or company_id)
- status: PENDING_COMMITMENT / ACCEPTED / REJECTED / TIMED_OUT
- requested_at
- resolved_at

### service_assignments

- id
- service_case_id
- request_service_need_id
- provider_commitment_id
- assignment_type: INDIVIDUAL / ORGANIZATION_PROVIDER / ORGANIZATION_PACKAGE
- status: CREATED / CONFIRMED / ACTIVE / FAILED / REPLACED / CANCELLED
- assigned_provider_id
- created_at
- updated_at

### assignment_plans

- id
- request_id
- service_assignment_ids json/list
- status

### service_cases

- id
- request_id
- customer_user_id
- care_receiver_id
- address
- agreed_terms json
- status: DRAFT / CONFIRMING / CONFIRMED / COORDINATING / READY_TO_START / SERVICE_STARTED / FAILED / ON_HOLD / CANCELLED
- created_at
- updated_at

### service_sessions

- id
- service_case_id
- service_assignment_id
- session_index
- scheduled_at
- status: SCHEDULED / REMINDER_SENT / EN_ROUTE_SIGNALLED / ARRIVED / SERVICE_STARTED / RESCHEDULED / CANCELLED
- started_at nullable

### coordination_events

- id
- service_session_id
- event_type
- created_at

### manual_holds

- id
- service_case_id
- actor_id
- reason
- status: ON_HOLD / RELEASED / CANCELLED
- created_at
- resolved_at

### assignment_audit_log

- id
- service_assignment_id nullable
- service_case_id nullable
- actor_id
- actor_role
- action_type
- reason
- before_state json
- after_state json
- created_at

### booking_settings

- id
- key (e.g. selection_lock_ttl_minutes, commitment_window_minutes, escalation_threshold_minutes, hold_policy)
- value
- updated_by
- updated_at

## Index Recommendations

- selection_locks(status, expires_at)
- provider_commitments(status, commitment_path)
- service_assignments(service_case_id, status)
- service_cases(status)
- service_sessions(service_case_id, status, scheduled_at)
- manual_holds(service_case_id, status)
- assignment_audit_log(service_case_id, created_at)
