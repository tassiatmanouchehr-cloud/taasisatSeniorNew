# SECURITY AND TENANCY FINDINGS

---

## High Severity

### FR-001: No Automated Tenant Isolation
- `TenantAwareModel.tenant_id` is UUIDField, not FK
- `TenantScopedManager.for_tenant()` is opt-in
- No middleware enforces tenant filtering
- 4 known unscoped queries documented

### FR-002: RBAC Enforcement Toggle
- `rbac.enforcement.enabled` can disable ALL RBAC per-tenant
- No audit when toggle changes
- Default is True but configurable

---

## Medium Severity

### FR-003: ownership_authorized_by Bypass
- PermissionService trusts caller for ownership verification
- Any caller can bypass RBAC by passing ownership_authorized_by

### FR-006: UserAccount Global Queries
- Login queries are not tenant-scoped
- Phone numbers are globally unique identifiers

### FR-007: SupplierRegistry Unscoped
- `find_by_linked_entity()` has no tenant filter
- Caller must validate tenant independently

### FR-008: No @login_required
- Custom auth checks per portal module
- No single enforcement point to audit

### FR-009: TenantAwareModel.tenant_id Not FK
- No DB-level referential integrity with Tenant
- No CASCADE/PROTECT on tenant deletion

---

## Low Severity

### FR-013: CSRF_COOKIE_HTTPONLY Not Set
- Django default is False
- Could be hardened

---

## Positive Security Findings

| Finding | Evidence |
|---------|----------|
| No raw SQL | Only `SELECT 1` health check |
| No eval/exec | Zero instances found |
| No pickle deserialization | Zero instances found |
| No csrf_exempt | Zero instances found |
| No mark_safe with user input | Only hardcoded SVG paths |
| CSRF middleware active | In middleware stack |
| Production security headers | HSTS, XSS, nosniff, secure cookies, SSL redirect, DENY frames |
| Architecture guardrails | test_architecture_guardrails.py, test_permission_registry_guardrails.py |
| Permission key registry | Regex-validated format |
| Portal views resolve from session | Never accept IDs from request parameters |
