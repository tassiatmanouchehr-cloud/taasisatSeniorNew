# CCS Kernel Envelope

## Configuration Envelope
```yaml
config_key: platform.kernel.example
owner_module: Module25
schema_version: 1.0
scope_level: platform|tenant|organization|region|role|actor|environment
value_type: boolean|string|number|object|array
default_value: null
override_policy: locked|inheritable|tenant_override|role_override
change_requires_approval: true
activation_mode: immediate|scheduled|next_cycle
rollback_supported: true
audit_class: standard
```

## Configuration Rules
- Every configuration key has one owning module.
- Keys must be namespaced.
- Values must be schema-validated.
- Sensitive configuration must be encrypted or reference secrets indirectly.
- Configuration changes must be auditable.
- Tenant overrides must never change platform security invariants.
