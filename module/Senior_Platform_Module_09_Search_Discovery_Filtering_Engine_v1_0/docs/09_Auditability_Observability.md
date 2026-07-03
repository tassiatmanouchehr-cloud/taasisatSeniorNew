# 09 — Auditability & Observability

## 1. Audit objectives

Module 09 must answer:

- who searched;
- under which tenant;
- under which role and permission context;
- which surface was used;
- which filters and result scopes were requested;
- which policy decision allowed or denied the query;
- which result entities were returned when audit policy requires it;
- which index mutation occurred;
- which upstream event caused it;
- whether a document was suppressed, restored, or deleted;
- whether search behavior may indicate abuse.

## 2. Audit events

Audit events are defined in `audit/Audit_Event_Model.md` and the CES catalog.

## 3. Observability metrics

Required metrics:

- search_query_count;
- search_query_latency_ms;
- search_zero_result_rate;
- search_error_rate;
- search_timeout_rate;
- autocomplete_query_count;
- saved_search_evaluation_count;
- index_operation_lag_seconds;
- index_operation_failure_rate;
- dead_letter_queue_size;
- index_drift_count;
- critical_suppression_lag_seconds;
- facet_latency_ms;
- redaction_failure_count;
- permission_denied_count;
- rate_limit_trigger_count.

## 4. Logs

Structured logs must include:

- correlation_id;
- tenant_id;
- actor_id hash or system actor;
- surface;
- query hash;
- result scope;
- policy decision id;
- latency;
- outcome;
- error code.

Raw query text must not be logged by default.

## 5. Tracing

Distributed traces should cover:

- API gateway;
- permission resolution;
- query normalization;
- search provider request;
- post-filtering;
- redaction;
- response serialization;
- audit sink.

## 6. Dashboards

Minimum dashboards:

- search traffic and latency;
- zero-result diagnostics;
- index pipeline health;
- critical suppression SLA;
- saved search alert health;
- abuse/rate-limit monitoring;
- tenant-level search usage;
- provider adapter error rates.

## 7. Retention

Retention is CCS-configurable by data class:

- raw query disabled by default;
- redacted query text short retention;
- query hash medium retention;
- aggregate telemetry long retention;
- security audit logs controlled by compliance policy.
