# PORTALS, APIS, AND ENTRY POINTS

**Last verified HEAD:** a5dbaf28703142edaa1d770ea8f3c2a45a12640f
**Last verified date:** 2026-07-14

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

## Provider Portal (21 views)

Dashboard, assignments (list/detail/confirm/decline), visits (start/complete), availability (working windows, blocked periods), earnings, profile, documents.

Entry: `_guard()` → `require_authenticated()` → `resolve_tenant_id()` → `resolve_supplier()`

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
| `/api/v1/discovery/suppliers/` | GET | Supplier discovery |
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
- `HomePageService`, `CaregiverDirectoryService`, etc. (public_site)
