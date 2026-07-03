# 04 — Query, Filter & Facet Model

## 1. Query object

A search query consists of:

- tenant context;
- actor context;
- surface context;
- text query;
- result scopes;
- structured filters;
- geo filters;
- time filters;
- availability filters;
- price filters;
- trust/compliance filters;
- sort mode;
- ranking profile;
- facet request;
- pagination cursor.

## 2. Query normalization

The engine must normalize:

- whitespace;
- Unicode variants;
- locale-specific characters;
- casing;
- stop words when configured;
- synonyms when configured;
- typo tolerance when configured;
- unsupported operators;
- time zone boundaries;
- geo precision;
- price currency constraints.

## 3. Filter expression model

Filters use a provider-agnostic expression format:

```json
{
  "and": [
    {"field": "service_category_id", "op": "in", "value": ["cat_1", "cat_2"]},
    {"field": "location.distance_km", "op": "lte", "value": 15},
    {"field": "availability.start_at", "op": "gte", "value": "2026-07-03T10:00:00Z"}
  ]
}
```

Supported operators:

- eq;
- neq;
- in;
- not_in;
- gt;
- gte;
- lt;
- lte;
- between;
- exists;
- not_exists;
- contains;
- prefix;
- geo_within;
- geo_distance;
- time_overlaps;
- full_text;
- bool_is.

## 4. Facet model

A facet is a governed aggregation over the actor-visible result set.

Facet responses must respect:

- tenant boundary;
- actor permissions;
- result-scope restrictions;
- redaction policy;
- minimum bucket count rules;
- anti-enumeration thresholds;
- suppressed document exclusions.

Facet types:

- term facet;
- range facet;
- date histogram facet;
- geo bucket facet;
- boolean facet;
- hierarchical facet;
- availability-window facet;
- price-band facet.

## 5. Sorting

Allowed sort modes:

- relevance;
- newest;
- oldest;
- distance;
- price_low_to_high;
- price_high_to_low;
- availability_soonest;
- quality_score;
- response_time;
- administrative_priority.

Each sort mode must be explicitly allowed per surface and actor role.

## 6. Pagination

Cursor-based pagination is required for all production APIs. Offset pagination may exist only for internal diagnostics.

Cursor payload must include:

- query hash;
- sort state;
- last result key;
- index snapshot token when supported;
- expiration timestamp;
- integrity signature.

## 7. Autocomplete

Autocomplete must be separate from full search and must enforce:

- minimum query length;
- rate limits;
- tenant context;
- result-scope context;
- safe suggestion dictionary;
- sensitive-term suppression;
- no private entity leakage.

## 8. Empty result behavior

When zero results are found, the engine may return:

- relaxed filter hints;
- nearby category suggestions;
- broader time window suggestions;
- saved search offer;
- request creation redirect;
- support escalation path.

The engine must not fabricate results.
