# Decision History

Status: current as of the Repository Documentation & Project Governance
sprint, `main` @ `25b5f8ec3dab673beaa4ff954c577c6338d4764f`.

This is **not** another ADR. It is an index of every ADR in the
repository — where to find it, what it decided, why, and whether it still
holds. Read the linked ADR for the full Context/Decision/Consequences
reasoning; this table exists so a new developer can scan the whole
decision history in one page before diving into any single document.

Dates are the month the underlying decision was actually made (verified
against `git log`), which for several ADRs predates the ADR *document*
being written — several of these were formally recorded during the
architecture-consolidation sprint (Module 18) to document decisions
already made in earlier modules. Where that's true, it's noted.

| Date | Decision | ADR | Reason | Current Status |
|---|---|---|---|---|
| 2026-07 | Architecture Freeze — 24 binding pre-code decisions | [ADR-001](../../build_architecture_records/ADR_001_ARCHITECTURE_FREEZE_v1_0.md) | Freeze the Person≠UserAccount≠Provider identity chain, `ServiceSupplier` abstraction, tenant isolation model, aggregate boundaries, and 15 other named things before any Django model existed, so 25 modules could be built independently without re-litigating the same questions. | **Active** — binding; any deviation requires a new, owner-approved ADR (ADR-001.23) |
| 2026-07 | Matching Engine ships a minimal, honest subset | [ADR-002](../adr/ADR-002_MATCHING_ENGINE.md) | The frozen Blueprint describes a matching subsystem depending on entities (`Request`, `CandidateResponse`, `CustomerSelection`) that don't exist yet. Rather than invent them prematurely, Matching persists only what it can support today (`MatchRound`/`MatchCandidate`) and defers the rest. | **Active** — the deferred pieces (customer selection, candidate response, RBAC enforcement) remain deferred; see `PROJECT_MODULE_STATUS.md` Module 02 |
| 2026-07 | API Foundation rebuilt on real Django REST Framework | [ADR-003](../adr/ADR-003_API_FOUNDATION_DRF.md) | An initial inspection checked only `pyproject.toml`, found no DRF dependency, and built a hand-rolled JSON API layer. This was wrong — `requirements/base.txt` (the real dependency manifest) already declared `djangorestframework` as intentional. Corrected mid-module. *(Formally documented in the Module 18 consolidation sprint, decision made in the API foundation module.)* | **Active** — standard API layer for the whole platform |
| 2026-07 | `apps.wallet` is the canonical wallet bounded context | [ADR-004](../adr/ADR-004_CANONICAL_WALLET_CONTEXT.md) | `apps.finance`'s earlier wallet (`WalletAccount`/`WalletTransaction`) was dormant scaffolding — nothing outside its own tests ever used it. Building a second, real wallet concept for real customer-wallet requirements would have duplicated it; instead the Finance version was marked legacy/frozen. *(Formally documented in the Module 18 consolidation sprint, decision made in the Wallet module.)* | **Active** — guardrail-enforced (`NoDuplicateWalletModelTest`); avoids duplicate wallet systems |
| 2026-07 | `PaymentIntent` (Payments) and `PaymentTransaction` (Finance) are separate, unbridged bounded contexts | [ADR-005](../adr/ADR-005_PAYMENT_INTENT_VS_FINANCE_PAYMENT_TRANSACTION.md) | `finance.PaymentTransaction` is a single-shot, already-succeeded settlement record. The Payment Gateway module needed a genuine multi-step orchestration state machine (create → attempt → callback → settle) that shape can't represent. Built as a new, upstream context instead of overloading the old one. *(Formally documented in the Module 18 consolidation sprint, decision made in the Payments module.)* | **Active** — the bridge between the two remains deliberately unbuilt; see `GAP_ANALYSIS.md` |
| 2026-07 | Reporting is a pure, models-less read layer | [ADR-006](../adr/ADR-006_REPORTING_READ_MODEL.md) | Avoids introducing OLAP, a data warehouse, or a cached/materialized reporting layer before the product needs one. Every report is computed live via ORM aggregation over existing operational tables. *(Formally documented in the Module 18 consolidation sprint, decision made in the Reporting module.)* | **Active** — read-only reporting; no caching layer exists |
| 2026-07 | Service-layer ownership & the thin-controller rule, formalized with an automated guardrail | [ADR-007](../adr/ADR-007_SERVICE_LAYER_THIN_CONTROLLER_RULE.md) | Every module had independently converged on "business logic lives in services, not views" since Module 08, but the rule had never been written down or checked. A real violation was found and fixed during a Module 17B review, proving convention alone wasn't durable enough. | **Active** — enforced by `ApiViewOrmDisciplineTest`/`AdminPortalOrmDisciplineTest` at test time, not just by convention |
| 2026-07 | Demand-side domain model: one requester account, no `FamilyMemberProfile` | [ADR-008](../adr/ADR-008_DEMAND_SIDE_DOMAIN_MODEL.md) | Product clarification: a customer requesting care "for my father" is the same kind of account event as requesting care "for myself" — the care recipient is data, not a second account. Scopes a future, reusable `CareRecipient` entity and a future, invitation-based Order Share Link, explicitly ruling out a family-member account type. | **Active** — `CareRecipient` and Order Share Link remain future work, not yet implemented |

---

## Where each ADR lives

- **ADR-001** — `build_architecture_records/ADR_001_ARCHITECTURE_FREEZE_v1_0.md` (repository root level, pre-code freeze package — not under `docs/adr/` because it predates the `docs/` structure).
- **ADR-002 through ADR-008** — `docs/adr/` (as-built decisions, made during implementation).

## Reading order

New to this decision history? Read them in the table's date order — each
one either narrows or corrects something ADR-001 froze, and later ADRs
sometimes reference earlier ones (ADR-008 assumes the multi-role account
model that ADR-001's identity chain made possible; ADR-005 assumes the
`FinancialParty` abstraction ADR-004 relies on).

For what's actually built against each of these decisions today, see
[`PROJECT_MODULE_STATUS.md`](PROJECT_MODULE_STATUS.md). For what's still
open because of them, see [`GAP_ANALYSIS.md`](GAP_ANALYSIS.md).
