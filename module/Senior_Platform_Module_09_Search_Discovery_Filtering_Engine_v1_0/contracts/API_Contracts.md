# API Contracts

## 1. Search endpoint

`POST /search/query`

Request:

```json
{
  "tenant_id": "tenant_123",
  "surface": "provider_directory",
  "result_scope": ["provider_profile"],
  "query_text": "generic service keyword",
  "filters": {
    "and": [
      {"field": "service_category_id", "op": "eq", "value": "cat_123"}
    ]
  },
  "facets": ["service_category_id", "location_area"],
  "sort": "relevance",
  "page_size": 20,
  "cursor": null
}
```

Response:

```json
{
  "search_query_id": "sq_123",
  "results": [],
  "facets": [],
  "next_cursor": null,
  "result_count_returned": 0,
  "result_count_total": 0,
  "staleness": {
    "is_stale": false,
    "max_index_lag_seconds": 3
  }
}
```

## 2. Autocomplete endpoint

`POST /search/autocomplete`

Request:

```json
{
  "tenant_id": "tenant_123",
  "surface": "marketplace_home",
  "prefix": "gen",
  "result_scope": ["service_category", "provider_profile"],
  "limit": 10
}
```

## 3. Facet endpoint

`POST /search/facets`

Computes governed facets for a normalized query. Must use the same policy engine as `/search/query`.

## 4. Saved search endpoints

- `POST /search/saved-searches`
- `GET /search/saved-searches`
- `GET /search/saved-searches/{saved_search_id}`
- `PATCH /search/saved-searches/{saved_search_id}`
- `DELETE /search/saved-searches/{saved_search_id}`

## 5. Administrative index endpoints

Administrative endpoints require platform or tenant administrator permissions:

- `POST /search/admin/reindex-jobs`
- `GET /search/admin/reindex-jobs/{job_id}`
- `POST /search/admin/reconciliation-jobs`
- `GET /search/admin/index-operations`
- `POST /search/admin/index-operations/{id}/replay`

## 6. Error codes

| Code | Meaning |
|---|---|
| search.permission_denied | Actor cannot use surface or result scope |
| search.invalid_filter | Filter expression invalid |
| search.unsupported_sort | Sort mode not allowed |
| search.query_too_complex | Query exceeds complexity limits |
| search.rate_limited | Rate limit exceeded |
| search.provider_unavailable | Search provider unavailable |
| search.redaction_failed | Field redaction failed; response denied |
| search.cross_tenant_denied | Cross-tenant search not allowed |
| search.cursor_invalid | Cursor invalid or expired |
