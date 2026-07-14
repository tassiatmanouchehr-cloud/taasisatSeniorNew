# Permissions and Audit

## Permission Boundaries

### Location Read Permissions
Actors may read location data only when authorized by tenant policy, role policy, workflow state, and privacy configuration.

Examples:
- requester may see approximate provider ETA during active booking
- provider may see service destination after assignment or configured reveal point
- support operator may see precise coordinates only with explicit permission
- tenant admin may configure service areas
- platform operator may manage provider integrations without reading tenant movement history

## Sensitive Actions

The following actions require audit records:

- address normalization override
- manual coordinate edit
- geofence policy change
- service area polygon change
- live-location session start/stop by non-owner
- precise location access by support/operator/admin
- location retention policy change
- map provider configuration change
- trust signal manual override

## Audit Record Fields

- audit_id
- tenant_id
- actor_id
- actor_role
- action_type
- target_entity_type
- target_entity_id
- previous_value_hash optional
- new_value_hash optional
- reason_code optional
- request_id
- ip_hash optional
- user_agent_hash optional
- occurred_at

## Access Rule

Precise location access must be purpose-bound. Every support/admin access must have either workflow justification or explicit reason capture.
