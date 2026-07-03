# 12 — Operational Runbook

## 1. Daily checks

- Verify search query error rate.
- Verify p95 and p99 query latency.
- Verify index operation lag.
- Verify dead-letter queue size.
- Verify critical suppression SLA.
- Review zero-result rate anomalies.
- Review abuse/rate-limit spikes.

## 2. Index drift incident

1. Identify tenant and entity type.
2. Pause non-critical reindex jobs if needed.
3. Run tenant/entity drift report.
4. Replay failed source events.
5. Rebuild affected projection if replay fails.
6. Compare document counts and checksums.
7. Emit reconciliation completion event.
8. Record operational incident note.

## 3. Critical suppression failure

1. Enter safe mode for affected surface or tenant.
2. Identify source event and index operation.
3. Manually suppress affected source_entity_id if required.
4. Replay priority queue.
5. Confirm no suppressed entity appears in search.
6. Exit safe mode after verification.
7. Emit incident audit event.

## 4. Full tenant reindex

1. Freeze tenant mapping version.
2. Create new target index.
3. Export canonical projections from source modules.
4. Bulk index into target index.
5. Validate sample documents and counts.
6. Run permission/redaction validation suite.
7. Rotate alias.
8. Monitor latency and error rate.
9. Delete old index after retention window.

## 5. Search relevance tuning

1. Clone ranking profile.
2. Modify weights or tie-breakers.
3. Run offline evaluation set.
4. Run tenant-approved A/B test if enabled.
5. Compare conversion, zero-result, complaint, and fairness metrics.
6. Promote profile version.
7. Record change in audit log.

## 6. Saved search alert issue

1. Check evaluator queue lag.
2. Check search provider health.
3. Check Module 07 notification handoff events.
4. Replay failed saved_search_evaluated events if idempotent.
5. Confirm duplicate suppression.
