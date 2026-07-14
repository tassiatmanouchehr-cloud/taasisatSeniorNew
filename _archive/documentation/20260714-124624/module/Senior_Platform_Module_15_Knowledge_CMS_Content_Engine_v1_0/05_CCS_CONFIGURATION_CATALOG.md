# Senior Platform — Module 15 — Knowledge, CMS & Content Engine v1.0

**Status:** Frozen Draft / Enterprise Package v1.0  
**Domain:** Generic Service Marketplace Framework  
**Zero-domain-leakage:** Mandatory  
**Multi-tenant boundary:** Mandatory  

Headless content, help center, policies, landing pages, localization, versioning, approvals and publication governance.

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

### `content_approval_required`
- Scope: platform default + tenant override.
- Type: policy/configuration value.
- Change control: audited; high-risk changes require approval.

### `default_locale`
- Scope: platform default + tenant override.
- Type: policy/configuration value.
- Change control: audited; high-risk changes require approval.

### `seo_metadata_required`
- Scope: platform default + tenant override.
- Type: policy/configuration value.
- Change control: audited; high-risk changes require approval.

### `legal_page_versioning_required`
- Scope: platform default + tenant override.
- Type: policy/configuration value.
- Change control: audited; high-risk changes require approval.
