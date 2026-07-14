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

# 21 — Data Model

> Logical model, not final SQL. Core Platform tables are domain-neutral; reference implementation-specific meaning lives only in `field_key` / `type` values, never in schema.

## service_sessions

- id
- service_case_id (Module 03)
- service_assignment_id (Module 03)
- status (Session Lifecycle states)
- scheduled_at
- started_at nullable
- closed_at nullable
- created_at / updated_at

## presence_records

- id
- service_session_id
- capture_point: EN_ROUTE / ARRIVED / START / PAUSE / RESUME / TEMP_LEAVE / COMPLETION / CHECKOUT
- gps_lat / gps_lng nullable
- distance_from_target nullable
- status: EN_ROUTE_LOCATION_CAPTURED / ARRIVAL_LOCATION_CAPTURED / PRESENCE_VERIFIED / LOCATION_MISMATCH / GPS_UNAVAILABLE / MANUAL_REVIEW_REQUIRED / UNAUTHORIZED_DEPARTURE
- reported_problem json nullable
- created_at

## start_checklist_instances

- id
- service_session_id
- template_id
- status: PENDING / COMPLETED / FAILED
- completed_at nullable

## start_checklist_items

- id
- checklist_instance_id
- item_type: BOOLEAN_CONFIRMATION / TEXT_INPUT / NUMBER_INPUT / PHOTO_REQUIRED / SIGNATURE_REQUIRED / CUSTOMER_CONFIRMATION / GPS_CONFIRMATION / FILE_UPLOAD / MULTI_SELECT / SINGLE_SELECT / DOMAIN_FORM_FIELD
- required: boolean
- value json nullable
- completed_at nullable

## execution_activities

- id
- service_session_id
- activity_type: TASK / CHECK / ACTION / OBSERVATION / MEASUREMENT / COMMUNICATION / SYSTEM_EVENT / CUSTOM_EVENT
- actor_id
- actor_role
- status: PLANNED / AVAILABLE / STARTED / IN_PROGRESS / COMPLETED / SKIPPED / FAILED / CANCELLED
- started_at / finished_at
- duration_seconds
- visibility
- source: MANUAL / SYSTEM_GENERATED / AUTOMATION / INTEGRATION / API / ADMIN_ACTION
- depends_on_activity_id nullable
- timeline_position
- created_at
- version

## observation_records

- id
- service_session_id
- activity_id nullable
- category: GENERAL_NOTE / OPERATIONAL_NOTE / CUSTOMER_NOTE / PROVIDER_NOTE / INTERNAL_NOTE / OBSERVATION / MEASUREMENT / WARNING / FOLLOW_UP_REQUIRED / DOMAIN_SPECIFIC_RECORD
- actor_id / actor_role
- field_key
- value
- unit nullable
- unit_system nullable
- value_type nullable
- normal_range_reference nullable
- visibility
- created_at

## evidence_items

- id
- context_type: SESSION / ACTIVITY / OBSERVATION / CHECKLIST_ITEM / COMPLETION_REQUEST / EXCEPTION_CASE / OPERATIONAL_REVIEW
- context_id
- evidence_type: PHOTO / VIDEO / AUDIO / VOICE_NOTE / FILE / SIGNATURE / GPS_SNAPSHOT / CHECKLIST_ATTACHMENT / CUSTOMER_CONFIRMATION / PROVIDER_DECLARATION / ORGANIZATION_APPROVAL / PLATFORM_REVIEW
- requirement_level: REQUIRED / OPTIONAL / CONDITIONAL / NOT_ALLOWED
- status: CAPTURED / ATTACHED / SUBMITTED / ACCEPTED / REJECTED / FLAGGED / UNDER_REVIEW / REPLACED_BY_NEW_EVIDENCE / ACCESS_RESTRICTED
- visibility
- retention_expires_at nullable
- file_ref
- created_at

## interactions

- id
- service_session_id
- interaction_type: MESSAGE / PHONE_CALL / APPROVAL / REJECTION / CONFIRMATION / REQUEST / RESPONSE / RATING / FEEDBACK / SIGNATURE / ESCALATION / OPERATIONAL_DECISION / INTERNAL_COMMENT / SYSTEM_PROMPT
- sender_id / sender_role
- recipient_ids json
- related_activity_id nullable
- related_event_id nullable
- priority
- status: CREATED / DELIVERED / VIEWED / RESPONDED / RESOLVED / CLOSED / EXPIRED / ESCALATED
- visibility
- payload json
- requires_response: boolean
- due_time nullable
- resolution nullable
- created_at

## exceptions

- id
- service_session_id
- category: START_EXCEPTION / EXECUTION_EXCEPTION / COMMUNICATION_EXCEPTION / CUSTOMER_EXCEPTION / PROVIDER_EXCEPTION / LOCATION_EXCEPTION / SAFETY_EXCEPTION / TECHNICAL_EXCEPTION / CONFIGURATION_EXCEPTION / CUSTOM_EXCEPTION
- severity: LOW / MEDIUM / HIGH / CRITICAL
- status: OPEN / UNDER_REVIEW / WAITING_INFORMATION / WAITING_CUSTOMER / WAITING_PROVIDER / WAITING_ORGANIZATION / WAITING_PLATFORM / RESOLVED / CLOSED
- owner_id / owner_role
- resolution nullable
- created_at
- resolved_at nullable

## extension_requests

- id
- service_session_id
- requested_by_id / requested_by_role
- status: REQUESTED / WAITING_COUNTERPART_APPROVAL / APPROVED / APPLIED / CLOSED / REJECTED / DISPUTED / EXPIRED / CANCELLED / OPERATIONAL_REVIEW_REQUIRED
- requested_duration_minutes
- price_impact: NO_EXTRA_COST / EXTRA_COST_AGREED / PRICE_TO_BE_REVIEWED / DISPUTED
- created_at
- resolved_at nullable

## completion_records

- id
- service_session_id
- provider_completed_at
- provider_completion_note
- customer_confirmed_at nullable
- customer_confirmation_status: PENDING / CONFIRMED / FAILED / DISPUTED
- rating nullable
- feedback nullable
- created_at

## handover_records

- id
- service_session_id
- service_case_id
- remaining_sessions
- progress_percent
- next_session_id nullable
- created_at

## session_timeline_entries

- id
- service_session_id
- entry_type: EVENT / ACTIVITY / INTERACTION / REVIEW / CORRECTION / SYSTEM_DECISION
- source_id
- created_at

## audit_entries

- id
- entity_type
- entity_id
- actor_id / actor_role
- action
- reason nullable
- previous_state json nullable
- new_state json nullable
- trigger nullable
- related_session_id nullable
- related_event_id nullable
- created_at

## execution_settings

- id
- key (e.g. gps_mandatory, distance_radius_meters, evidence_required_by_phase, checklist_template_id, extension_agreement_timeout_minutes)
- value
- scope: CORE / ORGANIZATION / SERVICE_TYPE / SESSION
- updated_by
- updated_at

## Index Recommendations

- service_sessions(status, scheduled_at)
- presence_records(service_session_id, capture_point)
- execution_activities(service_session_id, status)
- observation_records(service_session_id, category)
- evidence_items(context_type, context_id, status)
- interactions(service_session_id, status)
- exceptions(service_session_id, status, severity)
- extension_requests(service_session_id, status)
- session_timeline_entries(service_session_id, created_at)
- audit_entries(entity_type, entity_id, created_at)
