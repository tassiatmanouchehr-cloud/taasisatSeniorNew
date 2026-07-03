# Reindexing & Backfill Runbook

## Full tenant reindex

```text
1. Create reindex job with tenant_id and projection version.
2. Lock mapping version for target index.
3. Create target index with new alias candidate.
4. Export canonical projections in batches.
5. Validate each projection against schema.
6. Bulk upsert documents.
7. Run count comparison.
8. Run permission/redaction sample validation.
9. Run checksum comparison.
10. Rotate read alias.
11. Monitor error rate and latency.
12. Retain old index until rollback window expires.
```

## Backfill from new projection

```text
1. Register projection version.
2. Build compatibility report.
3. Start backfill with dry-run.
4. Review rejected projections.
5. Run live backfill.
6. Enable new ranking/facet profile if needed.
7. Mark old projection deprecated.
```

## Failed operation replay

```text
1. Filter index operations by tenant, status, and source entity type.
2. Exclude stale operations.
3. Replay with original idempotency key.
4. Verify status transitions to succeeded or skipped.
5. Escalate terminal failures.
```
