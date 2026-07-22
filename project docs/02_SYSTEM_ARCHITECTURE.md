# SYSTEM ARCHITECTURE

## Repository Structure

```
src/
├── manage.py                    Django management entry point
├── config/
│   ├── settings/
│   │   ├── base.py              Shared settings (all environments)
│   │   ├── development.py       Local dev (DEBUG=True, SQLite fallback)
│   │   ├── testing.py           Test runner (DEBUG=False, fast passwords)
│   │   └── production.py        Production hardening (no deployment infra)
│   └── urls.py                  Root URL configuration
├── apps/                        25 Django applications (see below)
├── templates/                   126 HTML templates (8 namespaces)
├── ui/                          76 UI components, design tokens, themes, fonts
├── static/                      Compiled CSS/JS assets
├── tests/visual/                Playwright specs + 525 baseline PNGs
├── tools/                       4 validation scripts (RTL, tokens, themes, components)
├── scripts/                     Alpine.js build script
├── docker/                      Dockerfile.dev + entrypoint (dev only)
├── requirements/                base.txt, dev.txt, prod.txt, test.txt
└── pyproject.toml               Ruff config, pytest config, project metadata
```

## Applications (25)

### Layer 0 — Infrastructure

| App | Purpose | Models |
|---|---|---|
| `common` | Abstract base models, shared managers, enums, validators | TimestampedModel, TenantAwareModel, SoftDeleteMixin |
| `kernel` | Tenants, identity, RBAC, audit, config, feature flags, events, suppliers | Tenant, Person, UserAccount, Role, Permission, RoleAssignment, AuditLog, ConfigurationKey/Value, FeatureFlag, EventOutbox, ServiceSupplier, PolicyDefinition/Version |

### Layer 1 — Domain Core

| App | Purpose | Models |
|---|---|---|
| `accounts` | Identity, profiles, verification, affiliations, favorites, gallery | CustomerProfile, ElderProfile, CaregiverProfile, OrganizationProfile, OrganizationMembership, CompanyAffiliationRequest, VerificationDocument, OTPChallenge, CaregiverSkill, CaregiverExperience, CaregiverGalleryItem, Favorite, TrustedContact, PlatformTeamMember |
| `orders` | Order lifecycle, service catalog, offers | ServiceCategory, ServiceType, Order, OrderOffer, OrderStatusHistory, OrderOrganizationEligibility, OrderShareLink |
| `booking` | Supplier assignment to orders | SupplierAssignment |
| `matching` | Automated supplier matching | MatchRound, MatchCandidate |
| `execution` | Service delivery session tracking | ExecutionSession |
| `availability` | Working schedule and capacity | ProviderWorkingWindow, AvailabilityBlockedPeriod, CapacityRule |
| `discovery` | Supplier search and ranking | (no models — pure service layer) |
| `reviews` | Customer reviews and reputation | Review, ReviewRating, ReputationSnapshot |
| `notifications` | Cross-channel notification dispatch | Notification, NotificationDeliveryAttempt |

### Layer 2 — Financial Domain

| App | Purpose | Models |
|---|---|---|
| `commission` | Commission contracts, escrow, disputes | CommissionContract, CommissionSnapshot, PaymentDeadline/Extension, ObjectionPeriod/Extension, Dispute/DisputeLine/DisputeResolution, ReleaseInstruction, RefundInstruction |
| `finance` | Financial documents, escrow, ledger | FinancialDocument/Item, EscrowRecord/Movement, LedgerEntry, FinancialObligation, FinancialParty, PaymentTransaction, SettlementBatch/Item, WalletAccount (LEGACY) |
| `wallet` | Canonical wallet system | Wallet, WalletTransaction, WalletBalanceSnapshot |
| `pricing` | Pricing rules and quotes | PricingRule, Quote, QuoteLine, Promotion, PromotionCondition, PromotionEffect |
| `payments` | Payment collection via PSP | PaymentIntent, PaymentAttempt, PaymentCallback |

### Layer 3 — Infrastructure Services

| App | Purpose | Models |
|---|---|---|
| `jobs` | Durable background job system | JobDefinition, JobRun |
| `reporting` | Report generation | (no models — pure service layer) |

### Layer 4 — Presentation

| App | Purpose | Routes |
|---|---|---|
| `portal` | Customer portal | ~50 routes under `/portal/` |
| `provider_portal` | Caregiver portal | ~40 routes under `/provider/` |
| `organization_portal` | Company portal | 28 routes under `/organization/` |
| `admin_portal` | Platform admin | 20 routes under `/admin-portal/` |
| `public_site` | Public marketplace | 21 routes at root `/` |
| `api` | REST API (DRF) | 12 endpoints under `/api/v1/` |
| `showcase` | UI component dev showcase | 15 routes under `/ui/` |

## Architecture Rules

### Service-Layer Discipline

**Views never touch the ORM directly.** This is enforced by 6 automated guardrail tests that scan all portal/API view source files for forbidden patterns (`objects.`, `.filter(`, `.save(`, `.delete()`). All data access flows through service methods.

### Dependency Rules

Applications may only depend downward through the layer hierarchy:

```
Presentation → Domain/Financial → Infrastructure
```

No circular dependencies exist. Verified by inspection of all import statements.

High fan-in (most depended upon): `kernel` (22 apps), `accounts` (11), `orders` (10), `common` (9)

### Domain Boundaries

Each domain app owns its models exclusively. Cross-domain writes go through the owning app's service layer. Enforced by sole-writer guardrail tests:

- Only `OrderEligibilityService` writes `OrderOrganizationEligibility`
- Only `ProfileActivationService` transitions profile status to ACTIVE/SUSPENDED/ARCHIVED
- Only `SupplierRegistry` creates/modifies `ServiceSupplier` records
- Only `EventPublisher` + outbox worker touch `EventOutbox`

## Tenant Isolation

- Every `TenantAwareModel` carries a `tenant` FK to `kernel.Tenant`
- 168 service methods accept explicit `tenant_id` parameter
- All queries filter by `tenant_id`
- Cross-tenant access returns domain-specific errors (never 500s)
- **No tenant-scoping middleware** — isolation is per-service discipline only

## Security Model

### Authentication

All portals require session-based authentication (`AuthenticationMiddleware`). Public site is anonymous by design (except favorite toggles).

### Authorization — Dual Model

| Surface | Model |
|---|---|
| Customer/Provider/Organization portals | **Ownership** — `resolve_*_profile()` scopes to the authenticated user's own data |
| Admin portal | **RBAC** — `PermissionService.require()` with 11 permission keys |
| Domain services | **RBAC** — `PermissionService.require()` at mutation entry points (42 call sites) |
| REST API | **RBAC + Ownership** — permission keys for operator endpoints, ownership for customer endpoints |

### Permission Registry

40 permission keys registered at startup via `apps.kernel.permissions.keys`. All keys have at least one enforcement call site. Zero unused permissions.

### RBAC System

- `Role` — tenant-scoped data row with JSON permissions list
- `RoleAssignment` — binds user to role with scope (platform/organization/branch) + expiry
- `PermissionService.require()` — sole evaluator. Fail-closed. Supports `ownership_authorized_by` fallback.
- `RBACConfiguration` — emergency enforcement toggle (management-command-only, audit-logged)
- 12 DEFAULT_TENANT_ROLES + 14 DEV_BOOTSTRAP_ROLES defined in `role_catalog.py`

## Transaction Strategy

- **159 `@transaction.atomic` blocks** across production code
- Every mutation service method wraps its work in an atomic transaction
- `transaction.on_commit()` used for non-transactional side effects (file deletion, event dispatch)
- Nested atomics use savepoints for partial-failure handling (e.g., order number retry)

## Concurrency Strategy

- **95 `select_for_update()` call sites** across production code
- Lock ordering: parent row first for cross-row invariants (e.g., lock CaregiverProfile before gallery count check)
- `select_for_update(skip_locked=True)` for background job claiming
- 12 dedicated `TransactionTestCase` concurrency test files with real multi-threading

## Audit Logging

- `AuditLog` model — immutable (blocks update, raises on delete)
- Classification: standard / financial / security / compliance
- Before/after snapshots, correlation tracking, actor + tenant identification
- **51 `AuditService.log()` call sites** across production code
- Every domain mutation creates an audit entry

## Design Principles

1. **Code is the source of truth** — documentation follows implementation, never the reverse
2. **Service-layer architecture** — views are thin controllers, all logic in services
3. **Explicit over implicit** — tenant_id passed explicitly, never inferred from context
4. **Fail-closed security** — RBAC denies by default; enforcement toggle defaults to enabled
5. **Immutable audit** — every mutation is permanently recorded
6. **Concurrency-safe by default** — row locking before every check-then-write

## Extension Points

- `FeatureFlagService` — tenant-aware flags for gradual rollout (boolean/percentage/actor_list/rule_based)
- `EventOutbox` — transactional outbox for domain events; consumers can be added without modifying producers
- `PolicyDefinition/PolicyVersion` — versioned business rules (immutable after activation)
- `ConfigResolver` — 6-level scope hierarchy for runtime configuration (actor→role→branch→org→tenant→platform)
- `PaymentProviderRegistry` — pluggable PSP adapters (currently only FakePaymentProvider)
- `RankingStrategy` — pluggable supplier ranking algorithms

## Technology Stack

| Component | Technology |
|---|---|
| Language | Python 3.12+ |
| Framework | Django 5.2 |
| Database | PostgreSQL 16 (optional PostGIS) |
| Cache | Redis (optional, falls back to LocMemCache) |
| Task Queue | Celery (optional in dev) |
| API | Django REST Framework |
| Frontend | Server-rendered templates + HTMX + Alpine.js |
| CSS | TailwindCSS (RTL-first) |
| Fonts | IRANSansX, Vazirmatn, JetBrains Mono |
| Linting | Ruff |
| Testing | Django TestCase + Playwright |
| CI | GitHub Actions (2 workflows) |
| Containerization | Docker (dev only) |

## Development Workflow

### Running Locally

```bash
cd src/
cp .env.example .env  # adjust DATABASE_PORT if needed
python manage.py migrate
python manage.py seed_tenant
python manage.py seed_auth_roles
python manage.py seed_service_catalog
python manage.py seed_product_walkthrough --reset-demo
python manage.py runserver
```

### Running Tests

```bash
cd src/
python manage.py test  # full regression (2,546 tests)
python manage.py test apps.orders  # single app
```

### Linting

```bash
ruff check src/
ruff format src/
```

### Visual Tests

```bash
cd src/tests/visual/
npm install
npx playwright test
```
