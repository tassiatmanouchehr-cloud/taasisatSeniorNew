# ADR-006 — Reporting as a Pure, Models-less Read Layer

## Status

Accepted — Module 16, reaffirmed in Module 18.

## Context

Module 16 needed to expose operational/provider/financial/marketplace
statistics for future dashboards without introducing OLAP, a data
warehouse, external BI integration, or a cached/materialized reporting
layer — all explicitly out of scope. The obvious alternative designs
(a dedicated reporting database, denormalized snapshot tables refreshed
by a scheduled job, a GraphQL-style query layer) all would have
introduced state and infrastructure this stage of the project doesn't
need yet.

## Decision

`apps.reporting` owns **no models and no migrations at all**. Every
report is computed live via Django ORM `aggregate()`/`annotate()`
against the existing operational tables (`Order`, `SupplierAssignment`,
`ExecutionSession`, `FinancialDocument`, `PaymentTransaction`, `Wallet`,
`WalletTransaction`, `ReputationSnapshot`, `ServiceSupplier`,
`OrganizationProfile`, `CustomerProfile`), and returned as immutable
frozen-dataclass DTOs — never raw ORM objects, never a `QuerySet` leaked
to a caller.

Every report method takes an explicit `tenant_id` and filters through it
first; nothing aggregates across tenants. Aggregation always uses `Sum`/
`Count`/`.count()` at the database level — proven necessary in Module
17B, where the shared pagination utility (`apps.api.pagination.paginate`)
was found to call `len()` on a `QuerySet` (forcing full evaluation into
memory) rather than `.count()`, and was fixed to check
`isinstance(items, QuerySet)` explicitly.

## Consequences

- `apps.reporting` has the widest import fan-in of any app (reads across
  orders/booking/execution/finance/wallet/reviews — see
  `docs/architecture/dependency-graph.md`) by design; this is the
  intended shape of a read model, not layering drift.
- No caching means every request recomputes from scratch — acceptable at
  current data volumes (documented as a known limitation, not a defect,
  in `docs/architecture/technical-debt-register.md`).
- `apps.api`'s reporting endpoints (Module 17A) are thin passthroughs to
  `apps.reporting.services` — confirming the DTO-based read-model
  contract is exactly what an API view needs, with no adaptation layer
  required.
- If materialization is ever needed, it should be introduced additively
  (a cache or snapshot table behind the existing `ReportingService` call
  sites) rather than changing the public contract those call sites rely
  on.
