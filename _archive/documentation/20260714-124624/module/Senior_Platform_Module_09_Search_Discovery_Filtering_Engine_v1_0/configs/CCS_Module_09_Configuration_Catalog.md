# CCS — Module 09 Configuration Catalog v1.0

All configuration keys use prefix `search_discovery_filtering.`.

## 1. Tenant isolation

| Key | Type | Default | Description |
|---|---:|---|---|
| search_discovery_filtering.index.strategy | enum | shared_partitioned | per_tenant, shared_partitioned, hybrid |
| search_discovery_filtering.cross_tenant.enabled | boolean | false | Enables governed cross-tenant search |
| search_discovery_filtering.data_residency.region | string | null | Tenant index region |

## 2. Query controls

| Key | Type | Default | Description |
|---|---:|---|---|
| search_discovery_filtering.query.max_page_size | integer | 50 | Maximum results per page |
| search_discovery_filtering.query.default_page_size | integer | 20 | Default page size |
| search_discovery_filtering.query.max_filter_depth | integer | 5 | Maximum nested filter expression depth |
| search_discovery_filtering.query.max_filter_terms | integer | 50 | Maximum total filter terms |
| search_discovery_filtering.query.raw_text_logging_enabled | boolean | false | Whether raw query text may be stored |
| search_discovery_filtering.query.redacted_text_retention_days | integer | 30 | Retention for redacted query text |
| search_discovery_filtering.query.hash_retention_days | integer | 365 | Retention for query hashes |

## 3. Facets

| Key | Type | Default | Description |
|---|---:|---|---|
| search_discovery_filtering.facets.enabled | boolean | true | Enables facets |
| search_discovery_filtering.facets.min_bucket_count | integer | 3 | Anti-enumeration minimum bucket size |
| search_discovery_filtering.facets.max_buckets_per_facet | integer | 50 | Maximum buckets returned per facet |
| search_discovery_filtering.facets.timeout_ms | integer | 500 | Facet aggregation timeout |

## 4. Ranking

| Key | Type | Default | Description |
|---|---:|---|---|
| search_discovery_filtering.ranking.default_profile_id | string | generic_default_v1 | Default ranking profile |
| search_discovery_filtering.ranking.fairness_rotation_enabled | boolean | true | Enables fairness rotation |
| search_discovery_filtering.ranking.explainability_enabled | boolean | false | Allows explanations for authorized actors |

## 5. Autocomplete

| Key | Type | Default | Description |
|---|---:|---|---|
| search_discovery_filtering.autocomplete.enabled | boolean | true | Enables autocomplete |
| search_discovery_filtering.autocomplete.min_chars | integer | 2 | Minimum characters |
| search_discovery_filtering.autocomplete.max_suggestions | integer | 10 | Maximum suggestions |
| search_discovery_filtering.autocomplete.private_entity_suggestions_enabled | boolean | false | Private suggestions disabled by default |

## 6. Saved searches

| Key | Type | Default | Description |
|---|---:|---|---|
| search_discovery_filtering.saved_search.enabled | boolean | true | Enables saved searches |
| search_discovery_filtering.saved_search.max_per_actor | integer | 50 | Maximum saved searches per actor |
| search_discovery_filtering.saved_search.evaluation_interval_minutes | integer | 60 | Evaluation cadence |
| search_discovery_filtering.saved_search.notification_dedupe_hours | integer | 24 | Duplicate alert suppression |

## 7. Indexing

| Key | Type | Default | Description |
|---|---:|---|---|
| search_discovery_filtering.indexing.retry_max_attempts | integer | 8 | Retry attempts |
| search_discovery_filtering.indexing.retry_backoff_seconds | integer | 30 | Initial backoff |
| search_discovery_filtering.indexing.critical_suppression_sla_seconds | integer | 30 | Max lag for critical suppression |
| search_discovery_filtering.indexing.reconciliation_enabled | boolean | true | Enables drift reconciliation |
| search_discovery_filtering.indexing.reconciliation_interval_minutes | integer | 1440 | Daily reconciliation |
| search_discovery_filtering.indexing.blue_green_reindex_enabled | boolean | true | Allows zero-downtime reindex |

## 8. Abuse protection

| Key | Type | Default | Description |
|---|---:|---|---|
| search_discovery_filtering.abuse.rate_limit_per_actor_per_minute | integer | 60 | Actor search rate limit |
| search_discovery_filtering.abuse.rate_limit_anonymous_per_minute | integer | 20 | Anonymous rate limit |
| search_discovery_filtering.abuse.enumeration_detection_enabled | boolean | true | Detects enumeration patterns |
| search_discovery_filtering.abuse.max_cursor_chain_length | integer | 20 | Prevents deep scraping |

## 9. Geo and privacy

| Key | Type | Default | Description |
|---|---:|---|---|
| search_discovery_filtering.geo.public_precision | enum | area | none, area, approximate, precise |
| search_discovery_filtering.geo.authenticated_precision | enum | approximate | none, area, approximate, precise |
| search_discovery_filtering.privacy.redaction_fail_closed | boolean | true | Redaction failure denies response |
