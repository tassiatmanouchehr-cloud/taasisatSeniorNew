# 03 — Search Index Model

## 1. Index strategy

Module 09 supports multiple index layouts. The implementation must select one or more by configuration.

| Strategy | Use case |
|---|---|
| Per-tenant physical index | strict isolation, large tenants, enterprise compliance |
| Shared physical index with tenant partition key | small and medium tenants, lower operational overhead |
| Hybrid index | public discovery shared; private/admin indexes per tenant |
| Ephemeral index | temporary migration, reindexing, blue/green deployment |

The default enterprise strategy is shared physical index with mandatory tenant_id filtering and optional per-tenant physical index override.

## 2. Index groups

| Index group | Documents |
|---|---|
| public_discovery | public-safe provider, organization, category, and offer projections |
| private_marketplace | actor-visible requests, assignments, availability, offers |
| administrative | admin/operator records and support-search references |
| autocomplete | suggestion terms and prefix documents |
| telemetry_aggregate | anonymized aggregate search statistics |

## 3. Searchable document principles

A document must include only fields that are allowed for the index group. Do not index raw sensitive information by default.

Required metadata:

```json
{
  "tenant_id": "tenant_123",
  "source_module": "module_08_identity_roles_profiles_access",
  "source_entity_type": "provider_profile",
  "source_entity_id": "profile_123",
  "source_entity_version": 17,
  "projection_version": "1.0",
  "visibility_state": "visible",
  "permission_tags": ["provider_profile:public_read"],
  "indexed_at": "2026-07-03T00:00:00Z"
}
```

## 4. Field classes

| Field class | Examples | Policy |
|---|---|---|
| metadata | tenant_id, source ids, versions | always required |
| searchable text | title, summary, normalized keywords | redacted and normalized |
| structured filters | category_id, capability_codes, state | schema-defined only |
| geo fields | lat/lng, service area, distance bands | precision controlled by privacy policy |
| availability fields | time windows, capacity flags | stale-safe and bounded |
| price fields | min_price, max_price, currency | display permission checked |
| ranking signals | quality score, freshness score | not directly exposed unless allowed |
| permission tags | visibility labels | mandatory |

## 5. Index mutation types

- upsert_document;
- partial_update_document;
- delete_document;
- suppress_document;
- restore_document;
- rebuild_document;
- expire_document;
- rotate_alias;
- backfill_batch;
- reconcile_document.

## 6. Idempotency

Every index mutation must use this idempotency key format:

```text
{tenant_id}:{source_module}:{source_entity_type}:{source_entity_id}:{source_entity_version}:{projection_version}:{operation_type}
```

Duplicate operations with the same idempotency key must not create duplicate documents, duplicate audit entries, or duplicate downstream notifications.

## 7. Reindexing

Enterprise reindexing must support:

- full tenant reindex;
- entity-type reindex;
- projection-version reindex;
- failed-operation replay;
- blue/green index alias switch;
- dry-run validation;
- checksum comparison;
- drift report.

## 8. Staleness policy

Each document may define max_staleness_seconds. Query response must include a staleness signal when configured.

If a critical suppression event is delayed beyond configured SLA, the engine must block affected entity types or tenant surfaces until reconciliation completes.
