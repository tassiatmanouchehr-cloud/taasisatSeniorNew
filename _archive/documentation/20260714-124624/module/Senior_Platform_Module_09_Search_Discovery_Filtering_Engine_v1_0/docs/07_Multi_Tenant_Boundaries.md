# 07 — Multi-Tenant Boundaries

## 1. Tenant isolation rule

Every index document, saved search, query log, facet definition override, ranking profile override, and index operation is tenant-scoped unless explicitly declared platform-global.

Platform-global data must be read-only to tenants and must not include tenant private data.

## 2. Tenant modes

| Mode | Description |
|---|---|
| single tenant | tenant has isolated marketplace search |
| multi-organization tenant | organizations share a tenant boundary with organization-scoped permissions |
| platform marketplace | platform-level discovery across tenants only when explicitly enabled |
| private enterprise tenant | physically isolated indexes and strict administrative boundaries |

## 3. Cross-tenant search

Cross-tenant search is denied by default.

It may be allowed only when:

- Module 08 grants platform-level permission;
- CCS enables the cross-tenant surface;
- each result document is marked cross_tenant_discoverable;
- redaction profile is platform-safe;
- audit logging is enabled.

## 4. Organization boundaries

Within a tenant, organization visibility is governed by Module 08 membership and Module 03/06 eligibility signals.

Search must distinguish:

- organization-owned records;
- actor-owned records;
- tenant-wide records;
- platform-owned records.

## 5. Tenant-specific configuration

Tenants may configure:

- enabled surfaces;
- available facets;
- ranking profile weights;
- autocomplete settings;
- saved search limits;
- retention windows;
- index isolation mode;
- geo precision;
- price visibility;
- analytics consent policy.

Tenant overrides must not weaken platform security baselines.

## 6. Data residency

For enterprise deployments, index selection must support data residency constraints. A tenant assigned to a region must not index private documents outside that region unless explicitly permitted.

## 7. Tenant deletion

Tenant deletion requires:

- stop accepting new index operations;
- delete or anonymize search documents;
- delete saved searches;
- purge query logs per retention policy;
- retain mandatory audit logs if legally required;
- emit search.tenant_search_data_purged.
