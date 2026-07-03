# 01 — Enterprise Architecture

## 1. Architectural position

The Search, Discovery & Filtering Engine is a read-optimized discovery layer between canonical business modules and user-facing marketplace surfaces.

It accepts normalized, permission-safe projections from upstream modules, transforms them into searchable documents, and exposes query endpoints that enforce tenant, actor, permission, privacy, lifecycle, and compliance boundaries before results are returned.

Search is never treated as a source of truth. It is an eventually consistent projection layer with strict reconciliation, audit, and fallback behavior.

## 2. Core components

| Component | Responsibility |
|---|---|
| Search API Gateway | Receives search, autocomplete, facet, saved-search, and discovery requests |
| Query Policy Resolver | Resolves tenant, actor, role, permissions, visibility gates, query limits |
| Query Normalizer | Canonicalizes query text, filters, sorting, pagination, locale, geo constraints |
| Filter Compiler | Converts generic filter expressions into search-provider-compatible predicates |
| Facet Engine | Computes countable filter dimensions from allowed result sets |
| Ranking Engine | Applies deterministic ranking profile, boosts, demotions, and tie-breakers |
| Redaction Engine | Removes fields the actor cannot see before response emission |
| Search Index Adapter | Abstracts OpenSearch, Elasticsearch, Postgres FTS, Meilisearch, Typesense, or hosted search providers |
| Index Projection Consumer | Consumes CES events from Modules 01–08 and applies index mutations |
| Reconciliation Worker | Detects drift between canonical modules and search documents |
| Saved Search Manager | Stores reusable queries and alert subscriptions |
| Telemetry & Audit Sink | Captures compliant search analytics and audit events |

## 3. Enterprise design rules

1. Every query is evaluated under an explicit tenant context.
2. Every query is evaluated under an explicit actor context.
3. Every result must pass visibility policy after search-provider retrieval.
4. Index documents are denormalized projections, not canonical records.
5. Search ranking must be deterministic for the same index snapshot and query profile.
6. A result may be suppressed by trust, compliance, lifecycle, capacity, or access rules.
7. Search telemetry must avoid storing raw sensitive free-text unless explicitly allowed.
8. Reindexing must be possible without downtime.
9. Provider-specific search technology must not leak into module contracts.
10. All filters must be schema-defined and versioned.

## 4. Primary surfaces

- global marketplace search;
- service request discovery;
- provider discovery;
- organization discovery;
- service category discovery;
- location and coverage discovery;
- availability discovery;
- price-range discovery;
- capability and credential discovery;
- administrative search;
- support/operator search;
- saved search alerts;
- autocomplete and suggestion surfaces.

## 5. Consistency model

Module 09 uses eventual consistency for normal indexing. Each indexed document carries:

- source module;
- source entity type;
- source entity id;
- source version;
- projection version;
- tenant id;
- visibility policy version;
- last indexed at;
- index operation id.

Critical visibility removals, such as suspension, compliance block, tenant removal, deletion, fraud lock, or privacy withdrawal, must be processed with high-priority index mutation queues.

## 6. Data flow

```text
Canonical Modules 01–08
        │
        ├── CES events
        │
Index Projection Consumer
        │
Projection Builder + Redaction Rules
        │
Search Index Adapter
        │
Search API Gateway
        │
Query Policy + Filter + Ranking + Redaction
        │
Marketplace UI / Admin UI / Operator UI / API Clients
```

## 7. Zero-domain-leakage rule

The engine must only use generic vocabulary:

- actor;
- requester;
- provider;
- organization;
- service unit;
- service category;
- request;
- booking;
- assignment;
- execution;
- location;
- capability;
- credential;
- availability;
- price range;
- trust status;
- compliance status.

No vertical-specific nouns, statuses, credentials, or service types are allowed in this module.
