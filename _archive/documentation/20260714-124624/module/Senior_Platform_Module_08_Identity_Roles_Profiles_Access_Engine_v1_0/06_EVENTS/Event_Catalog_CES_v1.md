# Module 08 CES Event Catalog

All events use CES v1.0 envelope and include tenant/scope metadata where applicable.

## Identity & Account Events
- `identity.created`
- `identity.updated`
- `identity.verification_state_changed`
- `account.created`
- `account.activated`
- `account.restricted`
- `account.locked`
- `account.closed`
- `credential.created`
- `credential.rotated`
- `credential.revoked`
- `session.started`
- `session.ended`
- `session.revoked`
- `device.registered`
- `device.trusted`
- `device.revoked`
- `device.suspicious_activity_detected`

## Actor Events
- `actor.created`
- `actor.activated`
- `actor.suspended`
- `actor.revoked`
- `actor.context_added`
- `actor.context_removed`

## Organization Events
- `organization.registration_submitted`
- `organization.activated`
- `organization.rejected`
- `organization.suspended`
- `organization.department_created`
- `organization.department_updated`
- `organization.staff_invited`
- `organization.staff_joined`
- `organization.staff_role_assigned`
- `organization.staff_role_revoked`
- `organization.staff_removed`

## Provider Affiliation Events
- `provider.registration_submitted`
- `provider.affiliation_requested`
- `provider.affiliation_approved`
- `provider.affiliation_rejected`
- `provider.affiliation_revoked`
- `provider.affiliation_suspended`
- `provider.independent_context_activated`
- `provider.organization_context_activated`

## Customer & Trusted Access Events
- `customer.registration_completed`
- `trusted_access.invited`
- `trusted_access.accepted`
- `trusted_access.activated`
- `trusted_access.revoked`
- `trusted_access.expired`
- `trusted_access.access_denied`

## Role & Permission Events
- `role.created`
- `role.updated`
- `role.archived`
- `permission_group.created`
- `permission_group.updated`
- `role_assignment.created`
- `role_assignment.revoked`
- `permission.delegated`
- `permission.delegation_revoked`
- `temporary_permission.granted`
- `temporary_permission.expired`

## Profile Events
- `profile.created`
- `profile.updated`
- `profile.publication_requested`
- `profile.published`
- `profile.hidden`
- `profile.suspended`
- `profile.media_added`
- `profile.media_removed`
- `profile.visibility_changed`

## Verification & Badge Events
- `verification.request_created`
- `verification.submitted`
- `verification.in_review`
- `verification.approved`
- `verification.rejected`
- `verification.expired`
- `verification.revoked`
- `badge.issued`
- `badge.revoked`
- `badge.expired`

## Access Security Events
- `access.decision_logged`
- `access.denied`
- `access.sensitive_data_viewed`
- `access.impersonation_started`
- `access.impersonation_ended`
- `access.emergency_started`
- `access.emergency_ended`
- `access.policy_violation_detected`
