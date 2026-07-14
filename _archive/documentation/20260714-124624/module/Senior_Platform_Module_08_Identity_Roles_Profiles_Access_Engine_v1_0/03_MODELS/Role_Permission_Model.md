# Role & Permission Model

## Permission Design
Permissions are atomic capability keys. They must not include tenant-specific names or vertical-specific terms.

Example pattern:
```text
identity.account.read
identity.account.lock
actor.provider.approve_affiliation
organization.staff.invite
organization.staff.assign_role
profile.public.publish
profile.private.read
verification.request.review
access.trusted_person.grant
access.impersonation.start
```

## Role Types
- `SYSTEM_ROLE`: framework-defined, versioned, non-editable.
- `PLATFORM_ROLE`: marketplace-owner role templates.
- `TENANT_ROLE`: organization-level role templates.
- `CUSTOM_ROLE`: tenant-created role with bounded permissions.
- `TEMPORARY_ROLE`: time-limited role assignment.
- `DELEGATED_ROLE`: limited role derived from another actor's authority.

## Permission Groups
Permission groups are curated bundles, not security primitives. The Access Decision Service expands groups into permissions at evaluation time.

## Hierarchy
Hierarchy is explicit through role inheritance. Inheritance must be acyclic and auditable.

## Tenant Awareness
Every role assignment has a scope. Tenant-level role assignments do not apply outside their tenant. Platform-level role assignments require platform-owner authority and critical audit.

## Delegated Permissions
Delegation must define:
- delegator actor;
- delegate actor;
- allowed permission subset;
- scope;
- start/end time;
- revocation policy;
- audit reason.

## Temporary Permissions
Temporary permissions require expiry. Critical temporary permissions may require approval, MFA and elevated logging.

## Deny Rules
Explicit denies override allows where configured. System-level sanctions from governance modules may block otherwise valid permissions.

## Evaluation Order
1. Validate actor/account/session/device state.
2. Validate resource scope and tenant boundary.
3. Apply explicit deny and sanctions.
4. Evaluate direct role assignments.
5. Evaluate inherited roles.
6. Evaluate delegated permissions.
7. Evaluate temporary permissions.
8. Evaluate resource ownership grants.
9. Evaluate trusted access grants.
10. Apply obligations and masking rules.
11. Return decision and audit record.
