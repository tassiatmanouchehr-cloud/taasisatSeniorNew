# CES — Module 09 Event Catalog v1.0

All Module 09 events use prefix `search.` and follow the Core Event Specification established in previous modules.

## Event list

| Event | Producer | Consumers | Purpose |
|---|---|---|---|
| search.query_executed | Module 09 | Audit, analytics | A search query was executed |
| search.query_denied | Module 09 | Audit, security | Query denied by policy |
| search.zero_results_returned | Module 09 | Analytics, product | Query returned no results |
| search.autocomplete_executed | Module 09 | Analytics | Autocomplete request executed |
| search.document_index_requested | Module 09 | Index worker | Index mutation requested |
| search.document_indexed | Module 09 | Audit, ops | Document indexed successfully |
| search.document_index_failed | Module 09 | Ops, alerting | Index mutation failed |
| search.document_suppressed | Module 09 | Audit, ops | Document hidden from search |
| search.document_restored | Module 09 | Audit, ops | Document restored to search |
| search.document_deleted | Module 09 | Audit, ops | Document removed from index |
| search.index_drift_detected | Module 09 | Ops | Drift found between canonical source and index |
| search.index_reconciliation_started | Module 09 | Ops | Reconciliation started |
| search.index_document_reconciled | Module 09 | Ops, audit | One document reconciled |
| search.index_reconciliation_completed | Module 09 | Ops | Reconciliation completed |
| search.reindex_started | Module 09 | Ops | Reindex job started |
| search.reindex_completed | Module 09 | Ops | Reindex job completed |
| search.reindex_failed | Module 09 | Ops, alerting | Reindex job failed |
| search.saved_search_created | Module 09 | Audit | Saved search created |
| search.saved_search_updated | Module 09 | Audit | Saved search updated |
| search.saved_search_disabled | Module 09 | Audit | Saved search disabled |
| search.saved_search_deleted | Module 09 | Audit | Saved search deleted |
| search.saved_search_evaluated | Module 09 | Module 07, analytics | Saved search evaluated |
| search.saved_search_match_found | Module 09 | Module 07 | Saved search found new eligible result |
| search.abuse_signal_detected | Module 09 | Module 06, security | Search abuse pattern detected |
| search.tenant_search_data_purged | Module 09 | Audit, ops | Tenant search data purged |

## Standard event envelope

```json
{
  "event_id": "evt_...",
  "event_type": "search.query_executed",
  "event_version": "1.0",
  "occurred_at": "2026-07-03T00:00:00Z",
  "producer_module": "module_09_search_discovery_filtering_engine",
  "tenant_id": "tenant_123",
  "actor_id": "actor_123",
  "correlation_id": "corr_123",
  "causation_id": "evt_previous",
  "idempotency_key": "...",
  "payload": {}
}
```

## Event payloads

### search.query_executed

```json
{
  "search_query_id": "sq_123",
  "search_session_id": "ss_123",
  "surface": "provider_directory",
  "query_hash": "sha256:...",
  "result_scope": ["provider_profile"],
  "filter_hash": "sha256:...",
  "ranking_profile_id": "provider_discovery_default_v1",
  "result_count_returned": 20,
  "result_count_total": 431,
  "latency_ms": 83,
  "policy_decision_id": "pd_123"
}
```

### search.query_denied

```json
{
  "surface": "admin_global_search",
  "reason_code": "permission_denied",
  "query_hash": "sha256:...",
  "policy_decision_id": "pd_123"
}
```

### search.document_indexed

```json
{
  "index_operation_id": "idxop_123",
  "search_document_id": "sdoc_123",
  "source_module": "module_01_request_engine",
  "source_entity_type": "request",
  "source_entity_id": "req_123",
  "source_entity_version": 9,
  "projection_version": "1.0",
  "target_index": "private_marketplace",
  "operation_type": "upsert_document"
}
```

### search.document_suppressed

```json
{
  "search_document_id": "sdoc_123",
  "source_module": "module_06_trust_safety_dispute_compliance",
  "source_entity_type": "compliance_subject",
  "source_entity_id": "subj_123",
  "suppression_reason_code": "compliance_blocked",
  "critical": true
}
```

### search.saved_search_match_found

```json
{
  "saved_search_id": "svs_123",
  "owner_actor_id": "actor_123",
  "matched_result_refs": [
    {
      "source_module": "module_01_request_engine",
      "source_entity_type": "request",
      "source_entity_id": "req_123"
    }
  ],
  "dedupe_key": "svs_123:req_123:2026-07-03"
}
```
