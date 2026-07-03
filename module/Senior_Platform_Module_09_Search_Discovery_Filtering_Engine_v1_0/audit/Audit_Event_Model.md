# Audit Event Model

## Audit record fields

- audit_event_id;
- tenant_id;
- actor_id nullable;
- actor_type;
- module_id;
- action;
- resource_type;
- resource_id nullable;
- correlation_id;
- policy_decision_id nullable;
- result;
- reason_code nullable;
- metadata;
- occurred_at.

## Audited actions

- search.query.execute;
- search.query.deny;
- search.result.redact;
- search.result.suppress;
- search.saved_search.create;
- search.saved_search.update;
- search.saved_search.disable;
- search.saved_search.delete;
- search.index.upsert;
- search.index.delete;
- search.index.suppress;
- search.index.restore;
- search.reindex.start;
- search.reindex.complete;
- search.reconciliation.start;
- search.reconciliation.complete;
- search.abuse.detect.

## Sensitive audit handling

Audit metadata must use query hashes and field names, not raw sensitive values, unless a compliance policy explicitly requires secure retention.
