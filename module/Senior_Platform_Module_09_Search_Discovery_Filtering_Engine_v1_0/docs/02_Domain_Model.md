# 02 — Domain Model

## 1. Aggregate roots owned by Module 09

### SearchSession

A short-lived analytical and security context for a sequence of searches by an actor or anonymous visitor.

Fields:

- search_session_id;
- tenant_id;
- actor_id nullable;
- anonymous_session_id nullable;
- channel;
- locale;
- device_class;
- started_at;
- expires_at;
- risk_score_snapshot;
- consent_state_snapshot.

### SearchQuery

A single normalized search execution request.

Fields:

- search_query_id;
- search_session_id;
- tenant_id;
- actor_id nullable;
- query_text_hash;
- query_text_redacted nullable;
- filters;
- facets_requested;
- sort_mode;
- ranking_profile_id;
- result_scope;
- page_size;
- page_cursor;
- executed_at;
- latency_ms;
- result_count_total nullable;
- result_count_returned;
- policy_decision_id.

### SearchableDocument

A denormalized, permission-safe projection of a canonical entity.

Fields:

- search_document_id;
- tenant_id;
- source_module;
- source_entity_type;
- source_entity_id;
- source_entity_version;
- projection_type;
- projection_version;
- lifecycle_state;
- visibility_state;
- trust_state;
- compliance_state;
- searchable_text;
- structured_fields;
- location_fields;
- availability_fields;
- pricing_fields;
- ranking_signals;
- permission_tags;
- redaction_profile_id;
- indexed_at;
- expires_at nullable.

### FacetDefinition

A governed filter dimension available to specific surfaces.

Fields:

- facet_definition_id;
- tenant_id nullable for platform default;
- facet_key;
- label_key;
- field_path;
- value_type;
- allowed_operators;
- surface_scope;
- actor_scope;
- display_order;
- is_public;
- is_active;
- version.

### RankingProfile

A configurable scoring policy for a discovery surface.

Fields:

- ranking_profile_id;
- tenant_id nullable;
- surface_scope;
- actor_scope;
- base_sort;
- boost_rules;
- demotion_rules;
- tie_breakers;
- fairness_policy;
- freshness_policy;
- geo_policy;
- availability_policy;
- version;
- effective_from;
- effective_until nullable.

### SavedSearch

A stored query owned by an actor or organization.

Fields:

- saved_search_id;
- tenant_id;
- owner_actor_id;
- owner_organization_id nullable;
- name;
- normalized_query;
- alert_policy;
- notification_channel_preferences;
- last_evaluated_at nullable;
- last_notification_at nullable;
- is_active;
- created_at;
- updated_at.

### IndexOperation

A durable record of an attempted index mutation.

Fields:

- index_operation_id;
- tenant_id;
- source_event_id;
- operation_type;
- source_module;
- source_entity_type;
- source_entity_id;
- target_index;
- idempotency_key;
- attempt_count;
- status;
- error_code nullable;
- error_message_hash nullable;
- created_at;
- completed_at nullable.

## 2. Read models not owned by Module 09

Module 09 may consume projections of:

- request summary;
- provider profile summary;
- organization profile summary;
- service category summary;
- booking availability summary;
- assignment visibility summary;
- trust and compliance summary;
- pricing summary;
- location coverage summary.

The canonical ownership remains in Modules 01–08.

## 3. Lifecycle states

Searchable documents use generic states:

- draft;
- pending_review;
- active;
- paused;
- assigned;
- in_progress;
- completed;
- cancelled;
- blocked;
- archived;
- deleted.

Each source module maps its canonical state into these generic search lifecycle states through projection contracts.

## 4. Result entity types

Supported generic result types:

- request;
- provider_profile;
- organization_profile;
- service_category;
- service_offer;
- availability_slot;
- location_area;
- support_case_reference;
- administrative_record_reference.

Administrative result types require explicit permissions and must never appear in public discovery surfaces.
