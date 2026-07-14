# ADR-002 — Matching Engine (Module 02) Foundation

## Status

Accepted — Sprint 4A (foundation). Supersedes nothing. Builds directly on
ADR-001 (Architecture Freeze) and the Sprint 3A tenant isolation / supplier
registry work (kernel `ServiceSupplier`, `SupplierRegistry`, `SupplierResolver`).

## Context

The frozen architecture (`ARCHITECTURE_INTAKE_REPORT_v1.0.md` §"Module 02 —
Matching Engine", `PHASE_0_5_ENTERPRISE_DOMAIN_MODEL_FREEZE.md` §1.8, and the
module's own frozen ADRs in
`module/Senior_Platform_Module_02_Matching_Engine_v1.0/14_Module_02_ADRs.md`)
describes a rich matching subsystem: `MatchRound`, `MatchCandidate`,
`CandidateResponse`, `CustomerSelection`, `EligibilityEvaluation`,
`RankingScore`, operating against a separate `Request`/`RequestServiceNeed`
aggregate (Module 01) that does not exist yet in this codebase.

The current codebase implements a simpler, already-shipped `Order` model
(`apps.orders`) that plays the role the frozen `Request` will eventually
play, plus a working `ServiceSupplier` abstraction (`apps.kernel`, hardened
in Sprint 3A: tenant isolation via real FKs, `SupplierRegistry` as the sole
creation/lookup owner, `SupplierResolver` for marketplace-model-aware
querying — including an already-defined but previously unused
`get_suppliers_for_matching()` entry point clearly reserved for this
module).

This ADR defines a **minimal, honest subset** of Module 02 that fits the
current codebase today, without inventing entities the surrounding system
(Request Engine, Booking Engine, notification infrastructure) cannot yet
support. It intentionally defers `CandidateResponse`, `CustomerSelection`,
and `EligibilityEvaluation`/`RankingScore` as separate persisted entities —
their essential information is captured on `MatchCandidate` — until those
prerequisite modules exist and the aggregate boundaries genuinely require
the split (Module 01/03 will drive that decision, not this one).

## Domain Boundaries

- **`apps.matching`** owns: candidate generation, eligibility evaluation,
  ranking, and the persisted record of a matching run (`MatchRound`,
  `MatchCandidate`).
- **`apps.kernel`** owns: `ServiceSupplier` identity/lifecycle
  (`SupplierRegistry`), tenant-and-marketplace-model-aware querying
  (`SupplierResolver`), configuration (`ConfigResolver`), events
  (`EventPublisher`).
- **`apps.orders`** owns: `Order` lifecycle and the status machine,
  including the *only* legitimate mutation of `Order.assigned_supplier`.
- **`apps.accounts`** owns: `CaregiverProfile`, `OrganizationProfile`,
  `OrganizationMembership`, `CompanyAffiliationRequest` — accounts-specific
  identity/affiliation data that matching must never query directly.

Dependency direction is one-way: `apps.matching` → `apps.orders` +
`apps.kernel`. Neither `apps.orders` nor `apps.kernel` know `apps.matching`
exists. `apps.matching` never imports `apps.accounts` — it only ever sees
the generic `ServiceSupplier` abstraction, exactly like every other business
module per the kernel supplier-abstraction rule established in Sprint 3A.

## Matching Responsibilities

1. **Candidate generation** — given an `Order`, produce the set of
   `ServiceSupplier`s that could plausibly serve it (tenant + marketplace
   model + category + availability, via `SupplierResolver.get_suppliers_for_matching`).
2. **Eligibility evaluation** — a pure, structured, explainable pass/fail
   per candidate (`EligibilityService`, `EligibilityCode` + JSON reason —
   per module ADR-02-07 "Explainable Eligibility").
3. **Ranking** — deterministic ordering of eligible candidates via a
   pluggable strategy (`RankingService` + `RankingStrategy`, per module
   ADR-02-22 "MVP uses configurable rule-based ranking").
4. **Persistence of what happened** — `MatchRound` + `MatchCandidate` rows,
   so a run is auditable and reproducible from its `config_snapshot`.
5. **Event emission** — `Matching.RunStarted/RunCompleted/RunFailed.v1`
   via the existing kernel `EventPublisher`, following the same outbox
   pattern every other module uses.

## What Matching Does NOT Own

- **Assignment.** Matching never writes `Order.assigned_supplier` and never
  calls `Order.save()` for assignment purposes. See "Assignment Ownership"
  below.
- **Supplier identity/lifecycle.** Matching never creates a `ServiceSupplier`
  — it only reads via `SupplierResolver`. Creation stays with
  `SupplierRegistry` (kernel) and the accounts `supplier_bridge`.
- **Customer selection.** No `CustomerSelection` entity or flow exists yet
  — out of scope this sprint (see below).
- **Supplier response workflow.** No accept/decline (`CandidateResponse`)
  flow exists yet — out of scope this sprint.
- **Auto-assignment.** Matching proposes; a human (operator, for now) picks.
- **UI/presentation.** No templates, no HTMX, no views in this sprint.

## Assignment Ownership

`apps.orders.services.status_machine.assign_supplier()` (established in
Sprint 3A) remains the **only** code path that may set
`Order.assigned_supplier`. `MatchOrchestrator.run()` never touches it.

The integration surface is deliberately thin and one-directional:

```
MatchOrchestrator.run(order_id)               # proposes candidates
      → (human picks a MatchCandidate)
      → orders.status_machine.assign_supplier(order_id, supplier)   # actually assigns
      → MatchOrchestrator.mark_candidate_selected(match_candidate_id)  # records the outcome
```

`mark_candidate_selected()` only flips a `MatchCandidate.status` to
`SELECTED` for audit/reporting after assignment has already happened
elsewhere — it performs no assignment itself and is proven not to by test
(`test_mark_selected_does_not_perform_assignment`).

## Tenant Isolation

Follows the exact pattern established in Sprint 3A — no new pattern
introduced:

- `MatchRound.tenant` and `MatchCandidate.tenant` are real
  `ForeignKey("kernel.Tenant", on_delete=models.PROTECT)` fields, not raw
  UUIDs (Sprint 3A's referential-integrity finding applies equally here).
- Both models use `TenantScopedManager` as `objects`.
- `SupplierResolver.get_suppliers_for_matching()` is already tenant-scoped
  (`ServiceSupplier.objects.filter(tenant_id=tenant_id, ...)`); the
  orchestrator always derives `tenant_id` from `order.tenant_id`, never
  from ambient/request context (this codebase has no tenant middleware).
- `EligibilityService` independently re-checks `supplier.tenant_id ==
  order.tenant_id` as its first, cheapest rule (`WRONG_TENANT` code) —
  defense in depth even though generation should already exclude
  cross-tenant suppliers structurally.
- Verified by tests: cross-tenant suppliers never appear in generated
  candidates, and a `MatchOrchestrator.run()` against an order with only
  cross-tenant suppliers in play produces zero `MatchCandidate` rows.

## Supplier Abstraction

Matching interacts exclusively with `ServiceSupplier` — never
`CaregiverProfile`, `OrganizationProfile`, or any vertical-specific model.
This is the same rule enforced in kernel's `SupplierRegistry`/
`SupplierResolver` (Sprint 3A): business modules depend on supplier
capabilities/type/configuration, never on `if company: ...` branching.

`MatchCandidate.supplier` is a direct FK to `kernel.ServiceSupplier`. If a
caller needs the underlying accounts-side profile (e.g., to display a
caregiver's name), that resolution happens through
`apps.accounts.services.supplier_bridge.resolve_supplier_entity()` — the
same bridge Order's `assigned_provider`/`assigned_organization` properties
already use. Matching code itself never calls that bridge; it stays at the
`ServiceSupplier` level throughout.

## Events

Emitted this sprint (via the existing `EventPublisher`, `source_module="M02"`):

- `Matching.RunStarted.v1` — `{order_id}`
- `Matching.RunCompleted.v1` — `{order_id, candidate_count, eligible_count}`
- `Matching.RunFailed.v1` — `{order_id, error}`

Deferred to later sprints (once the entities that would trigger them exist):

- `matching.candidate.generated` / `matching.candidate.filtered` /
  `matching.candidate.ranked` / `matching.candidate.presented` —
  per-candidate granularity deferred; this sprint emits one run-level
  completed event carrying aggregate counts instead.
- `matching.response.received` / `matching.response.expired` — no
  supplier-response workflow exists yet.
- `matching.selection.made` — no `CustomerSelection` entity exists yet.
- `matching.recomputed` — no re-matching trigger exists yet.

## Out of Scope (This Sprint)

- Customer-facing selection flow / `CustomerSelection` entity.
- Supplier accept/decline response workflow / `CandidateResponse` entity.
- Auto-assignment or auto-accept policies.
- Capability-entity-based eligibility (`ServiceSupplier.capabilities` stays
  an unvalidated placeholder JSON field — no `Capability` model exists to
  validate against yet).
- Real proximity/geo ranking (no GPS/geofencing infra — that's Module 04's
  domain) and `reputation_score`-driven ranking (always null today — Module
  06/14 doesn't populate it; treated as 0 by `SimpleRankingStrategy`).
- Enforcing `matching.ranking.max_candidates` as a hard cap on persisted
  candidates — the value is resolved and stored in `config_snapshot` for
  forward compatibility, but this sprint persists every generated
  candidate for full audit transparency rather than truncating.
- RBAC enforcement of `matching.*` protected operations — Module 08
  (permission evaluation engine) doesn't exist anywhere in this codebase
  yet; registering `Permission` rows for these operations is deferred
  alongside it, consistent with how every other module in this codebase
  currently handles RBAC.
- Organization-affiliation-aware eligibility (`ORGANIZATION_PROVIDER`
  suppliers whose underlying `CompanyAffiliationRequest`/
  `OrganizationMembership` has lapsed) — flagged as a real gap, deferred to
  keep this sprint's eligibility rule set to what was explicitly specified.
- UI, templates, HTMX — none in this sprint, per explicit instruction.

## Future Modules

- **Module 01 (Request Engine)** — once it exists, `MatchOrchestrator.run()`
  will operate against `RequestServiceNeed` instead of (or alongside)
  `Order`; this sprint's `Order`-centric design is a deliberate, temporary
  simplification, not a permanent coupling.
- **Module 03 (Booking/Assignment Engine)** — owns the frozen
  `supplier_id` + `execution_provider_id` + `assignment_mode` split
  documented in §16.6 of the intake report. Current `Order.assigned_supplier`
  only carries the commercial-owner level; resolving which specific person
  at an organization executes the service is Module 03's concern, not
  Module 02's, and not addressed here.
- **Module 06 (Trust/Quality/Governance)** — will start populating
  `ServiceSupplier.reputation_score`, at which point
  `SimpleRankingStrategy`'s reputation component becomes meaningful instead
  of always contributing zero.
- **Module 08 (Identity/Access)** — will evaluate the `matching.*`
  `Permission` rows this sprint stops short of registering/enforcing.
