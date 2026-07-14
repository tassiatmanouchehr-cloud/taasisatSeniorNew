# Canonical Data Model

## Canonical Concepts
- Tenant: isolated business/account boundary.
- Actor: authenticated or system principal performing an action.
- Party: person or organization participating in the marketplace.
- Resource: identifiable object owned by a module.
- Policy: versioned rule set that influences behavior.
- Event: immutable fact emitted after state transition.
- Command: request to perform a state transition.
- Projection: derived read model from source facts.
- Audit Record: immutable record of material action.
- Configuration: versioned setting resolved through scope hierarchy.

## Canonical Actor Reference
```yaml
actor:
  actor_id: string
  actor_type: user|service|system|integration
  tenant_id: string
  roles: [string]
  permissions_snapshot: [string]
  impersonation: optional
```

## Canonical Tenant Scope
```yaml
scope:
  tenant_id: string
  organization_id: optional string
  region_id: optional string
  environment: production|staging|development|test
```
