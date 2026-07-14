# Global Identifier Standard

## Required Identifier Fields
Every persisted entity and emitted event must support:
- id: stable globally unique identifier.
- tenant_id: tenant boundary identifier unless explicitly platform-global.
- module_id: owning module.
- entity_type: canonical entity type.
- external_ref: optional provider or external system reference.
- created_at: immutable creation timestamp.
- updated_at: last mutation timestamp.
- version: optimistic concurrency version.

## Identifier Rules
- IDs must be opaque.
- IDs must not encode business meaning.
- IDs must not expose sequential tenant-sensitive information.
- External IDs must never replace internal IDs.
- A deleted or merged entity ID must not be reused.

## Canonical Reference Format
```yaml
reference:
  id: string
  tenant_id: string
  module_id: string
  entity_type: string
  display_label: optional string
  contract_version: string
```
