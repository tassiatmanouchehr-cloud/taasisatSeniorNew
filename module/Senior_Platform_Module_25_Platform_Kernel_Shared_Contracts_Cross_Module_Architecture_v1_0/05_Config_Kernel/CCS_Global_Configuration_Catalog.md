# CCS Global Configuration Catalog

## Kernel Configuration Keys
- platform.kernel.contract_validation.enabled
- platform.kernel.strict_dependency_validation.enabled
- platform.kernel.cross_module_write_blocking.enabled
- platform.kernel.event_schema_compatibility.mode
- platform.kernel.config_schema_compatibility.mode
- platform.kernel.deprecation_warning_days
- platform.kernel.freeze_manifest.required
- platform.kernel.audit_envelope.required
- platform.kernel.tenant_boundary.enforcement_mode
- platform.kernel.error_contract.strict_mode

## Compatibility Modes
- advisory: log violations.
- enforced: block incompatible changes.
- migration: allow with migration plan.
- emergency: temporary override with approval and expiry.
