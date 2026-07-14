# Generic Service Marketplace Framework — Module 02: Matching Engine

**Version:** v1.0  
**Status:** Frozen / Approved  
**Project:** Generic Service Marketplace Framework  
**Module Owner:** Platform Architecture Team  
**Language:** Persian business domain, English technical structure  

> Module 01 — Request Engine is frozen and is treated as baseline. Module 02 must not change Module 01 decisions unless a major architectural conflict is discovered.


# Logical Data Model

> This is a logical model, not final SQL.

## Tables / Collections

### providers

- id
- provider_type: INDEPENDENT_PROVIDER / ORGANIZATION_PROVIDER / COMPANY
- display_name
- lifecycle_status
- verification_status
- public_profile_visible
- company_id nullable
- created_at
- updated_at

### provider_service_profiles

- id
- provider_id
- service_type_id
- is_active
- price_type
- price_min
- price_max
- experience_years
- qualification_status
- required_document_status
- created_at
- updated_at

### provider_documents

- id
- provider_id
- document_type
- status
- expires_at
- verified_by
- verified_at
- rejection_reason

### service_coverages

- id
- provider_id
- coverage_type: CITY / AREA / RADIUS / POLYGON_FUTURE
- province
- city
- area
- center_lat
- center_lng
- radius_km
- is_active

### provider_availability_slots

- id
- provider_id
- weekday
- start_time
- end_time
- availability_type
- is_active

### provider_busy_intervals

- id
- provider_id
- source_type
- source_id
- start_at
- end_at

### match_rounds

- id
- request_id
- strategy
- status
- reminder_at
- expires_at
- reopened_count
- created_at
- updated_at

### match_candidates

- id
- match_round_id
- request_service_need_id nullable
- candidate_type
- provider_id nullable
- company_id nullable
- covers_need_ids json/list
- coverage_status: FULL / PARTIAL
- eligibility_status
- fitness_score
- ranking_score
- warning_codes json/list
- status

### candidate_responses

- id
- match_candidate_id
- responder_provider_id
- response: ACCEPTED / REJECTED / WITHDRAWN
- responded_at
- withdrawal_reason nullable

### customer_selections

- id
- request_id
- request_service_need_id nullable
- match_candidate_id
- selected_by_user_id
- status: SELECTION_LOCKED / HANDED_TO_MODULE_03 / CANCELLED
- selected_at

### ranking_weight_settings

- id
- key
- weight
- is_active
- updated_by
- updated_at

### notification_settings

- id
- event_type
- channel
- is_enabled
- fallback_after_minutes
- updated_by
- updated_at

### notification_events

- id
- event_type
- recipient_type
- recipient_id
- channel
- status
- sent_at
- opened_at
- fallback_event_id

### manual_intervention_logs

- id
- actor_id
- actor_role
- request_id
- match_round_id
- action_type
- reason
- before_state json
- after_state json
- created_at

## Index Recommendations

- providers(provider_type, lifecycle_status)
- provider_service_profiles(service_type_id, is_active, qualification_status)
- service_coverages(city, area)
- match_candidates(match_round_id, status, ranking_score)
- candidate_responses(match_candidate_id, response)
- customer_selections(request_service_need_id, status)
- notification_events(recipient_id, status)
