# 13 — Acceptance Criteria

## 1. Architecture acceptance

- Module 09 has no vertical-specific terminology or business logic.
- Search is treated as projection, not source of truth.
- All search documents are tenant-scoped.
- Every query requires tenant and actor context.
- Result visibility is permission-checked and redacted after retrieval.
- Index synchronization is event-driven and idempotent.
- Reindexing and reconciliation are documented.
- CCS configuration exists for tenant overrides.
- CES event catalog exists for all owned events.

## 2. Security acceptance

- Anonymous search cannot access private documents.
- Cross-tenant search is denied by default.
- Field redaction fails closed.
- Raw query logging is disabled by default.
- Facet enumeration controls exist.
- Rate limits and query complexity limits exist.
- Critical suppression events are priority processed.

## 3. Functional acceptance

- Full-text search supports query normalization.
- Structured filtering supports governed operators.
- Facets are computed only over actor-visible results.
- Ranking profiles are configurable and versioned.
- Autocomplete is isolated from private data.
- Saved searches can be created, evaluated, updated, disabled, and deleted.
- Index operations are durable and replayable.

## 4. Operational acceptance

- Index drift can be detected and reconciled.
- Tenant reindex can run without downtime.
- Search provider failure has safe degradation behavior.
- Metrics, logs, traces, and dashboards are specified.
- Audit records support investigation.

## 5. Integration acceptance

- Module 01 request projections can be indexed.
- Module 02 matching signals can be used as optional ranking signals.
- Module 03 availability and assignment projections can affect discoverability.
- Module 04 execution states can suppress completed or unavailable records.
- Module 05 price summaries can be filtered only when visible.
- Module 06 trust/compliance events can suppress or demote documents.
- Module 07 receives saved-search notification handoff events only.
- Module 08 remains the authority for identity, roles, permissions, and profiles.
