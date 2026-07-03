# Senior Platform — Module 17 — Analytics, Reporting & BI Engine v1.0

**Status:** Frozen Draft / Enterprise Package v1.0  
**Domain:** Generic Service Marketplace Framework  
**Zero-domain-leakage:** Mandatory  
**Multi-tenant boundary:** Mandatory  

Metrics, dashboards, funnels, cohorts, exports, scheduled reports, semantic layer, data governance and KPI definitions.

---

## Configuration Principles
- Every configuration is tenant-scoped unless explicitly platform-global.
- Every override has precedence, effective window and audit reason.
- Historical interpretation uses the configuration snapshot active at the time of the event.

## Configuration Keys
### `enabled`
- Scope: platform default + tenant override.
- Type: policy/configuration value.
- Change control: audited; high-risk changes require approval.

### `tenant_scope_mode`
- Scope: platform default + tenant override.
- Type: policy/configuration value.
- Change control: audited; high-risk changes require approval.

### `default_policy_version`
- Scope: platform default + tenant override.
- Type: policy/configuration value.
- Change control: audited; high-risk changes require approval.

### `audit_level`
- Scope: platform default + tenant override.
- Type: policy/configuration value.
- Change control: audited; high-risk changes require approval.

### `retention_days`
- Scope: platform default + tenant override.
- Type: policy/configuration value.
- Change control: audited; high-risk changes require approval.

### `rate_limit_per_minute`
- Scope: platform default + tenant override.
- Type: policy/configuration value.
- Change control: audited; high-risk changes require approval.

### `idempotency_window_seconds`
- Scope: platform default + tenant override.
- Type: policy/configuration value.
- Change control: audited; high-risk changes require approval.

### `pii_masking_enabled`
- Scope: platform default + tenant override.
- Type: policy/configuration value.
- Change control: audited; high-risk changes require approval.

### `cross_tenant_access_blocked`
- Scope: platform default + tenant override.
- Type: policy/configuration value.
- Change control: audited; high-risk changes require approval.

### `event_publish_mode`
- Scope: platform default + tenant override.
- Type: policy/configuration value.
- Change control: audited; high-risk changes require approval.

### `dead_letter_enabled`
- Scope: platform default + tenant override.
- Type: policy/configuration value.
- Change control: audited; high-risk changes require approval.

### `admin_approval_required`
- Scope: platform default + tenant override.
- Type: policy/configuration value.
- Change control: audited; high-risk changes require approval.

### `rollback_allowed`
- Scope: platform default + tenant override.
- Type: policy/configuration value.
- Change control: audited; high-risk changes require approval.

### `pii_export_approval_required`
- Scope: platform default + tenant override.
- Type: policy/configuration value.
- Change control: audited; high-risk changes require approval.

### `scheduled_reports_enabled`
- Scope: platform default + tenant override.
- Type: policy/configuration value.
- Change control: audited; high-risk changes require approval.

### `metric_refresh_interval_minutes`
- Scope: platform default + tenant override.
- Type: policy/configuration value.
- Change control: audited; high-risk changes require approval.
