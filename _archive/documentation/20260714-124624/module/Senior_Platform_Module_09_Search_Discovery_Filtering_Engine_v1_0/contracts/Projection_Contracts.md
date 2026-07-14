# Projection Contracts

## 1. Projection contract rules

Every upstream module that wants an entity searchable must expose or emit a projection that includes:

- tenant_id;
- source_module;
- source_entity_type;
- source_entity_id;
- source_entity_version;
- projection_version;
- discoverability_state;
- permission_tags;
- redaction_profile_id;
- lifecycle_state;
- searchable fields;
- structured filter fields;
- ranking signals if any.

## 2. Generic request projection

```json
{
  "tenant_id": "tenant_123",
  "source_module": "module_01_request_engine",
  "source_entity_type": "request",
  "source_entity_id": "req_123",
  "source_entity_version": 4,
  "projection_version": "1.0",
  "lifecycle_state": "active",
  "discoverability_state": "discoverable",
  "searchable_text": {
    "title": "Generic service request",
    "summary": "Permission-safe request summary"
  },
  "structured_fields": {
    "service_category_id": "cat_123",
    "service_unit_codes": ["unit_generic"]
  },
  "permission_tags": ["provider:eligible_request_discovery"],
  "redaction_profile_id": "request_discovery_default_v1"
}
```

## 3. Generic provider profile projection

```json
{
  "tenant_id": "tenant_123",
  "source_module": "module_08_identity_roles_profiles_access",
  "source_entity_type": "provider_profile",
  "source_entity_id": "profile_123",
  "source_entity_version": 11,
  "projection_version": "1.0",
  "lifecycle_state": "active",
  "discoverability_state": "discoverable",
  "searchable_text": {
    "display_name": "Generic Provider",
    "summary": "Permission-safe capability summary"
  },
  "structured_fields": {
    "service_category_ids": ["cat_123"],
    "capability_codes": ["capability_generic"]
  },
  "permission_tags": ["public:read"],
  "redaction_profile_id": "provider_public_v1"
}
```

## 4. Projection validation

A projection is rejected if:

- tenant_id is missing;
- source identity is incomplete;
- source version is missing;
- permission_tags are missing;
- redaction_profile_id is missing;
- a prohibited sensitive field is present;
- lifecycle state is unmapped;
- projection version is unsupported.
