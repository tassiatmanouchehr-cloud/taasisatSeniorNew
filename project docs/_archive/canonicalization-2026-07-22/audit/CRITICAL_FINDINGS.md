# CRITICAL FINDINGS

---

## FR-001: No Automated Tenant Isolation at ORM Level

**Severity:** CRITICAL
**Confidence:** HIGH

**Affected subsystem:** All apps with tenant-scoped models

**Evidence:**
- `apps/common/models.py:53` — `tenant_id = UUIDField(db_index=True)`, not a ForeignKey
- `apps/common/managers.py:34` — `TenantScopedManager.for_tenant()` is opt-in, not default
- No Django middleware injects tenant_id into queries
- Every service must independently pass `tenant_id`

**Runtime impact:** A single forgotten `tenant_id` parameter in a new service or view creates a cross-tenant data leak. The system currently has 4 known unscoped queries (see FR-006, FR-007, FR-004, FR-006b).

**Security impact:** CRITICAL — multi-tenant isolation is the foundational security guarantee.

**Reproduction path:** Write a new service that queries `Order.objects.all()` without filtering by tenant_id. All orders from all tenants become visible.

**Why it matters:** The current system has ~70 models inheriting from TenantAwareModel. Each depends on the developer remembering to pass tenant_id. One mistake leaks data across tenants.

**Suggested future action:**
1. Short-term: Add architecture guardrail test that catches unscoped queries
2. Medium-term: Consider PostgreSQL Row-Level Security (RLS)
3. Long-term: Consider middleware-based tenant injection

---

## FR-002: RBAC Enforcement Can Be Disabled Per-Tenant

**Severity:** CRITICAL
**Confidence:** HIGH

**Affected subsystem:** kernel (permission_service)

**Evidence:**
- `apps/kernel/services/permission_service.py:135` — if `RBACConfiguration.get_enforcement_enabled(tenant_id)` is False, `require()` returns immediately
- `apps/kernel/services/rbac_configuration.py:15` — default is True, but can be changed via ConfigurationValue table
- No audit logging when enforcement is toggled

**Runtime impact:** Setting `rbac.enforcement.enabled=false` in the ConfigurationValue table disables ALL permission checks for that tenant. Any user can access any resource.

**Security impact:** CRITICAL — single configuration change bypasses entire authorization system.

**Reproduction path:** Insert a ConfigurationValue row with key=`rbac.enforcement.enabled`, value=`false` for any tenant. All `PermissionService.require()` calls become no-ops.

**Why it matters:** There is no alert, audit, or monitoring when this toggle changes. A compromised or malicious tenant admin could silently disable all authorization.

**Suggested future action:**
1. Add AuditService.log() call when enforcement toggle changes
2. Consider removing the toggle in production
3. Add monitoring alert for enforcement toggle changes
