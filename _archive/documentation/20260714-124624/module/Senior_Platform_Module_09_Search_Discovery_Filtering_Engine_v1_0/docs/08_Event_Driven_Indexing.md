# 08 — Event-Driven Indexing

## 1. Event ingestion

Module 09 consumes CES events from Modules 01–08. Each consumed event must be:

- authenticated;
- schema validated;
- tenant checked;
- idempotency checked;
- ordered where source guarantees sequence;
- transformed through projection builder;
- applied to index;
- recorded as IndexOperation.

## 2. Event-to-index mapping

| Upstream event class | Search action |
|---|---|
| entity created | build and upsert document if searchable |
| entity updated | partial update or rebuild document |
| lifecycle changed | update lifecycle_state and visibility_state |
| assignment changed | update request/provider discoverability |
| availability changed | update availability fields |
| price summary changed | update pricing fields if allowed |
| trust/compliance changed | suppress, demote, restore, or update trust fields |
| profile visibility changed | suppress or update profile document |
| permission changed | rebuild permission tags and redaction profile |
| tenant membership changed | suppress or rebuild organization/actor documents |
| entity deleted | delete or tombstone document |

## 3. Outbox/inbox requirement

Production implementations must use durable outbox/inbox patterns. Search indexing must not rely on synchronous UI requests.

## 4. Ordering

When events for the same source entity arrive out of order, the engine must compare source_entity_version. Older events must not overwrite newer documents.

## 5. Index operation states

- queued;
- processing;
- succeeded;
- retrying;
- failed_terminal;
- skipped_not_searchable;
- skipped_stale_event;
- suppressed_by_policy;
- awaiting_dependency;
- cancelled_by_reindex.

## 6. Retry policy

Retry behavior is CCS-configurable:

- exponential backoff;
- maximum attempts;
- dead-letter queue;
- alert thresholds;
- manual replay;
- tenant-scoped replay;
- source-entity replay.

## 7. Reconciliation

The reconciliation worker compares canonical projections with indexed documents and emits:

- search.index_drift_detected;
- search.index_reconciliation_started;
- search.index_document_reconciled;
- search.index_reconciliation_completed.

## 8. Critical events

The following require priority processing:

- compliance block;
- profile hidden;
- account suspended;
- tenant access revoked;
- deletion requested;
- sensitive field removed;
- trust safety suppression;
- legal hold changes.

If critical processing fails, affected surfaces must degrade to safe mode.
