# System Overview

Status: current as of Module 18 (Architecture Consolidation), `main` @ `f136f9a5`.

## What this is

A multi-tenant Django platform for a senior-care service marketplace
(سالمندیار). Customers request in-home care services; independent
providers and organizations (with their own caregivers) deliver them.
The platform coordinates matching, booking, execution, pricing, payment,
reviews, and reporting across that lifecycle.

## Technology

- Django 5.x, PostgreSQL (PostGIS optional via `GIS_ENABLED`).
- Django REST Framework (`rest_framework`) for the API layer (Module 17A) —
  a real, declared dependency (`requirements/base.txt`), not experimental.
- No Celery-driven business logic yet (the outbox worker exists as
  infrastructure — see `event-architecture.md` — but this codebase does
  not yet depend on it for anything user-facing).
- No SPA/frontend framework; `apps.public_site`/`apps.showcase` are
  server-rendered shells, out of scope for this document.

## The 16 business/platform apps

| App | Owns |
|---|---|
| `kernel` | Tenant, Person, UserAccount, RBAC (Role/RoleAssignment/PermissionService), ServiceSupplier (the generic supply-side abstraction), ConfigResolver, DomainEvent + EventOutbox/CES, AuditService |
| `accounts` | CustomerProfile, CaregiverProfile, OrganizationProfile, OrganizationMembership, affiliation requests |
| `orders` | Order lifecycle/status machine, ServiceCategory/ServiceType catalog |
| `matching` | MatchRound/MatchCandidate — candidate generation, eligibility, ranking for assignment |
| `booking` | SupplierAssignment — the operative commitment of a supplier to an order |
| `execution` | ExecutionSession — the on-the-ground service-delivery lifecycle |
| `finance` | FinancialParty, FinancialDocument, PaymentTransaction (ledger), FinancialObligation, LedgerEntry, SettlementBatch — the settlement/accounting layer |
| `notifications` | Notification rows created by DomainEvent handlers (Module 09) |
| `availability` | ProviderWorkingWindow, AvailabilityBlockedPeriod, CapacityRule |
| `pricing` | PricingRule, Promotion, Quote — deterministic price computation |
| `discovery` | Read-only supplier search/ranking (no models of its own) |
| `reviews` | Review, ReviewRating, ReputationSnapshot, reputation aggregation |
| `wallet` | Wallet, WalletTransaction — the canonical internal stored-value ledger |
| `payments` | PaymentIntent, PaymentAttempt, PaymentCallback — provider-agnostic payment orchestration (pre-settlement) |
| `reporting` | Read-only aggregation services over the above (no models of its own) |
| `api` | The `/api/v1/` DRF surface — routing, serializers, permission/pagination/error-envelope plumbing |

See `bounded-contexts.md` for ownership boundaries and `dependency-graph.md`
for the import graph between them.

## Core architectural principles (established across Modules 01–17B, still holding)

1. **ServiceSupplier is the universal supply-side abstraction.** Business
   modules never import `CaregiverProfile`/`OrganizationProfile` directly —
   they go through `kernel.ServiceSupplier`, resolved via
   `apps.accounts.services.supplier_bridge` when the concrete profile is
   genuinely needed (rare — mostly backward-compat properties).
2. **FinancialParty is the universal financial-counterparty abstraction.**
   `apps.wallet`, `apps.payments`, and `apps.finance` all reference
   `FinancialParty`, never a raw customer/supplier id.
3. **Every module's mutating operations live in a `services/` package**,
   never in models or views. See `service-layer-guidelines.md`.
4. **Tenant scoping is explicit everywhere** — either via
   `TenantScopedManager.for_tenant()` or an explicit `tenant_id=` filter.
   See `service-layer-guidelines.md` and the tenant-isolation note in
   `technical-debt-register.md`.
5. **RBAC is centralized**: `apps.kernel.services.permission_service
   .PermissionService` is the sole evaluator of Role/RoleAssignment;
   nothing else queries those tables for an authorization decision.
6. **The API layer is thin**: `apps/api/views/*.py` call services and
   serialize DTOs/model instances; they never contain business logic or
   multi-row ORM queries. See `api-guidelines.md`.
