# PERMISSION AND TENANT MODEL

**Last verified HEAD:** a5dbaf28703142edaa1d770ea8f3c2a45a12640f
**Last verified date:** 2026-07-14

---

## RBAC Architecture

### Permission Key Registry

All permission keys are defined in `apps/kernel/permissions/registry.py` with regex-validated format: `{module}.{resource}.{action}`.

### Permission Enforcement

`PermissionService.require()` in `apps/kernel/services/permission_service.py`:

1. If `RBACConfiguration.get_enforcement_enabled(tenant_id)` is False → **ALL RBAC BYPASSED** (configurable per-tenant)
2. If `actor is None` and `ownership_authorized_by is None` → system context, authorized
3. Normal RBAC check via `RoleAssignment` records
4. Ownership fallback: if `ownership_authorized_by` is set and has no RoleAssignment → authorized (caller-verified)

### Role Definitions

14 role categories defined via `seed_auth_roles` management command:
- platform-owner, platform-admin, platform-support
- organization-owner, organization-admin, organization-member
- customer, family-member
- independent-provider, organization-provider
- operator, dispatcher, reviewer, auditor

### Permission Enforcement Points

| Enforcement Point | Location |
|-------------------|----------|
| Customer Portal | `portal/views.py:_guard()` → `require_authenticated()` |
| Provider Portal | `provider_portal/views.py:_guard()` → `require_authenticated()` |
| Organization Portal | `organization_portal/views.py:_guard()` → `require_authenticated()` |
| Admin Portal | `admin_portal/views.py:require_admin_permission()` |
| API | `api/permissions.py:require_permission()` |
| Services | `PermissionService.require()` called explicitly |

### Critical Finding: No Middleware Enforcement

There is no Django middleware that automatically:
- Injects tenant_id into queries
- Enforces authentication
- Enforces RBAC

Every view and service must independently call auth/tenant/permission checks.

## Tenant Isolation

### How It Works

1. `TenantAwareModel.save()` validates `tenant_id` is non-empty
2. `TenantScopedManager.for_tenant(tenant_id)` provides convenience filtering
3. Services accept `tenant_id` parameter and use it in queries
4. Views resolve tenant from authenticated user's session

### Critical Finding: No Automated Tenant Isolation

Tenant filtering depends entirely on every developer passing `tenant_id` to every query. A single forgotten parameter creates a cross-tenant data leak.

### Unscoped Queries (Known)

| Location | Query | Risk |
|----------|-------|------|
| `commission/services/authorization.py:156-159` | `FinancialParty.objects.filter(id=party_id)` | Low (UUID random) |
| `accounts/views.py:86,124,163,241` | `UserAccount.objects.filter(phone=phone)` | By design (global login) |
| `kernel/services/supplier_registry.py:69-74` | `ServiceSupplier.objects.filter(linked_entity_id=...)` | Low (UUID random) |
| `api/views/payments.py:90` | `PaymentAttempt.objects.get(provider_reference=...)` | Low (unguessable token) |

## Security Configuration

Production settings include:
- HSTS (1 year), XSS filter, content-type nosniff
- Secure cookies (session + CSRF)
- SSL redirect
- X-Frame-Options: DENY
- No `csrf_exempt` decorators found
- No `eval()`, `exec()`, `pickle.loads()` found
- No raw SQL except `SELECT 1` health check
- No `mark_safe()` with user input
