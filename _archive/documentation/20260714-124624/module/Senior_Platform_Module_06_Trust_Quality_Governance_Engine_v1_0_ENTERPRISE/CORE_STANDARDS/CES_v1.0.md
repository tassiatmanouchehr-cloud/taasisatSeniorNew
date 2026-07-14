# Core Event Specification — CES v1.0

All framework events must use:

```text
event_id
event_name
event_version
occurred_at
published_at
tenant_id
source_module
source_service
actor_type
actor_id
subject_type
subject_id
correlation_id
causation_id
idempotency_key
trace_id
payload
metadata
```

Rules:
- Events are immutable.
- Events describe past facts.
- Event naming: <Domain><PastAction>.
- Event versioning is mandatory.
- Duplicate event processing must be idempotent.
