# Generic Service Marketplace Framework — Module 01: Request Engine

**Version:** v1.0  
**Status:** Frozen / Approved  
**Project:** Generic Service Marketplace Framework  
**Module Owner:** Platform Architecture Team  
**Language:** Persian business domain, English technical structure  

> Module 01 — Request Engine is the intake foundation of the Generic Service Marketplace Framework. It is frozen and treated as the baseline for all downstream modules (Matching, Provider, Company, Payment, and others). Later modules must not change Module 01 decisions unless a major architectural conflict is discovered.


# Logical Data Model

> This is a logical model, not final SQL.

## Tables / Collections

### requests

- id
- owner_user_id
- care_receiver_id
- status
- entry_path: SERVICE_FIRST / CARE_RECEIVER_FIRST
- is_recurring
- contract_id nullable
- tracking_number
- city
- address
- requested_time
- urgency: NORMAL / URGENT
- created_at
- updated_at

### request_service_needs

- id
- request_id
- service_type_id
- need_status
- notes
- created_at

### care_receivers

- id
- owner_user_id
- display_name
- age
- condition_notes
- created_at

### request_attachments

- id
- request_id
- file_ref
- suggested_type
- confirmed_type
- media_kind: PHOTO / VIDEO / DOCUMENT
- size_bytes
- visibility_scope
- created_at

### request_validations

- id
- request_id
- is_sufficient
- missing_fields json/list
- validated_at

### request_publications

- id
- request_id
- strategy: TARGETED_BY_SERVICE_AND_CITY / SMART_DISTRIBUTION_FUTURE
- recipient_count
- published_at

### applications

- id
- request_id
- provider_id
- status: APPLIED / IN_SELECTION_QUEUE / SELECTED / CONFIRMED / WITHDRAWN / NOT_SELECTED
- applied_at

### contracts

- id
- request_id
- provider_id nullable
- recurrence_rule
- total_sessions
- status
- created_at

### contract_sessions

- id
- contract_id
- session_index
- scheduled_at
- status: SCHEDULED / DONE / CANCELLED / REPLACEMENT_PROPOSED
- provider_id nullable

### request_timeline_entries

- id
- request_id
- event_type
- actor_role
- visible_to_roles json/list
- payload json
- created_at

### request_events

- id
- request_id
- event_name
- payload json
- emitted_at

### protection_signals

- id
- request_id
- signal_type: PHONE_IN_CHAT / PHONE_IN_IMAGE / PHONE_IN_PDF / EXTERNAL_PRICE / CANCEL_AFTER_ARRIVAL
- status: DETECTED / FLAGGED / REVIEWED
- reviewed_by nullable
- created_at

### customer_request_history

- id
- owner_user_id
- request_id
- action: CREATED / EDITED / DELETED / AUTO_DELETED
- reason nullable
- created_at

### request_settings

- id
- key  (e.g. selection_reminder_hours=24, publish_max_recipients)
- value
- updated_by
- updated_at

## Index Recommendations

- requests(status, service context)
- request_service_needs(service_type_id, need_status)
- request_publications(strategy)
- applications(request_id, status)
- contract_sessions(contract_id, status)
- request_timeline_entries(request_id, created_at)
- request_events(request_id, emitted_at)
- protection_signals(status, signal_type)
- customer_request_history(owner_user_id, action)
