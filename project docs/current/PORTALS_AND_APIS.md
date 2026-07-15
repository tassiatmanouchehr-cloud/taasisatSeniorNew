# PORTALS, APIS, AND ENTRY POINTS

**Last verified HEAD:** phase2-caregiver-professional-profile-foundation (from main @ 0c9d70c; PR #6 BG-022 remediation in progress)
**Last verified date:** 2026-07-15

---

## URL Routing

Root URL config: `config/urls.py`

| URL Prefix | App | Auth Required |
|------------|-----|---------------|
| `/` | public_site | No |
| `/accounts/` | accounts | Partial |
| `/admin/` | Django admin | Yes (staff) |
| `/admin-portal/` | admin_portal | Yes (admin permission) |
| `/api/v1/` | api | Yes (permission-based) |
| `/organization/` | organization_portal | Yes (org membership) |
| `/portal/` | portal | Yes (customer) |
| `/provider/` | provider_portal | Yes (provider) |
| `/ui/` | showcase | No |

## Customer Portal (30+ views)

Dashboard, profile, care recipients (CRUD), requests (list/detail/financial), share links, wizard (7-step order creation), notifications.

Entry: `_guard()` → `require_authenticated()` → `resolve_tenant_id()` → `resolve_customer_profile()`

## Provider Portal (26 views)

Dashboard, assignments (list/detail/confirm/decline), visits (start/complete), availability (working windows, blocked periods), earnings, profile, documents, skills (list/add/remove — Phase 2.1), experience (list/add/edit/delete — Phase 2.1).

Entry: `_guard()` → `require_authenticated()` → `resolve_tenant_id()` → `resolve_supplier()`. Profile-editing views additionally use `_guard_with_caregiver()`, resolving `request.user.caregiver_profile`.

## Organization Portal (18 views)

Dashboard, staff (list/approve/suspend), assignments, capacity, financial, reports, notifications, profile, documents.

Entry: `_guard()` → `require_authenticated()` → `resolve_tenant_id()` → `resolve_organization()`

## Admin Portal (12 views)

Home, tenants, suppliers, orders, finance, escrows, disputes, feature gates, system status.

Entry: `require_admin_permission()` → `require_authenticated()` → RBAC check

## API (12 endpoints)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/health/` | GET | Health check |
| `/api/v1/sample/order-counts/` | GET | Sample order counts |
| `/api/v1/sample/providers/` | GET | Sample provider reports |
| `/api/v1/discovery/suppliers/` | GET | Supplier discovery (permission-gated `DISCOVERY_SUPPLIERS_READ`, granted to no role in `DEFAULT_TENANT_ROLES` — internal/operator tooling, not a public/anonymous surface; confirmed out of scope for the BG-022 public-visibility remediation, see `traceability/IMPLEMENTATION_JOURNAL.md`) |
| `/api/v1/pricing/quotes/` | POST | Quote creation |
| `/api/v1/reviews/` | POST | Review submission |
| `/api/v1/suppliers/<id>/reputation/` | GET | Supplier reputation |
| `/api/v1/wallet/balance/` | GET | Wallet balance |
| `/api/v1/wallet/transactions/` | GET | Wallet transactions |
| `/api/v1/payments/intents/` | POST | Payment intent creation |
| `/api/v1/payments/intents/<id>/attempts/` | POST | Payment attempt |
| `/api/v1/payments/callbacks/fake/` | POST | Fake PSP callback (unauthenticated) |

## Public Site (18 views)

Home, about, services, how-it-work, contact, pricing, trust-safety, caregivers, organizations, find-a-caregiver, caregiver profile, organization profile, FAQ, privacy, terms, accessibility, support, service-areas.

## Presentation Services

Each portal has presentation services that transform domain models into view-ready data:
- `CustomerDashboardPresentationService`, `CustomerProfilePresentationService`, etc. (portal)
- `ProviderProfilePresentationService` (provider_portal)
- `OrganizationProfilePresentationService` (organization_portal)
- `HomePageService`, `CaregiverDirectoryService`, `CaregiverPublicProfileService` (public_site) — all three resolve caregiver/organization public visibility through the same canonical function, `apps.public_site.services.common.is_publicly_visible_attrs()` (BG-022 remediation, 2026-07-15); there is exactly one implementation of "is this publicly visible," never a per-surface duplicate
- `CaregiverSkillService`, `CaregiverExperienceService`, `PublicCredentialSelector` (accounts, Phase 2.1 — domain services/selectors, not presentation services; called by provider_portal/public_site)
