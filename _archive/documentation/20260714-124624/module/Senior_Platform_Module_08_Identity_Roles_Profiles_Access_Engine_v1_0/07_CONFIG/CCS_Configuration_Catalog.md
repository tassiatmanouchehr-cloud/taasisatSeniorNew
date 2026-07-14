# Module 08 CCS Configuration Catalog

## Registration Policies
```yaml
identity.registration.company.enabled: boolean
identity.registration.provider.enabled: boolean
identity.registration.customer.enabled: boolean
identity.registration.require_email_verification: boolean
identity.registration.require_phone_verification: boolean
identity.registration.allowed_actor_types: list[string]
```

## Provider Affiliation Policies
```yaml
provider.affiliation.enabled: boolean
provider.affiliation.company_identifier_required_format: string
provider.affiliation.auto_approve: boolean
provider.affiliation.approval_required_role: string
provider.affiliation.request_expiry_hours: integer
provider.affiliation.max_pending_requests_per_provider: integer
provider.affiliation.allow_multiple_organizations: boolean
provider.affiliation.reapproval_required_after_revocation: boolean
```

## Role & Permission Policies
```yaml
access.rbac.custom_roles_enabled: boolean
access.rbac.max_custom_roles_per_tenant: integer
access.rbac.allow_role_inheritance: boolean
access.rbac.temporary_permissions_enabled: boolean
access.rbac.max_temporary_permission_duration_hours: integer
access.rbac.delegation_enabled: boolean
access.rbac.explicit_deny_enabled: boolean
```

## Session & Device Policies
```yaml
security.session.max_duration_hours: integer
security.session.idle_timeout_minutes: integer
security.session.concurrent_session_limit: integer
security.device.trust_enabled: boolean
security.device.new_device_requires_mfa: boolean
security.mfa.required_for_critical_actions: boolean
```

## Profile Visibility Policies
```yaml
profile.public.provider.enabled: boolean
profile.public.organization.enabled: boolean
profile.public.require_review_before_publish: boolean
profile.media.require_review: boolean
profile.contact.show_phone_publicly: boolean
profile.contact.show_email_publicly: boolean
profile.address.precise_public_visibility: hidden|masked|public
profile.statistics.public_visibility: hidden|aggregate|detailed
```

## Verification Policies
```yaml
verification.identity.required_for_provider_activation: boolean
verification.professional_license.required_for_provider_activation: boolean
verification.organization.required_for_company_activation: boolean
verification.document.expiry_warning_days: integer
verification.review.dual_control_required: boolean
verification.badges.auto_issue_on_approval: boolean
```

## Trusted Access Policies
```yaml
trusted_access.enabled: boolean
trusted_access.default_expiry_hours: integer
trusted_access.require_contact_verification: boolean
trusted_access.allow_progress_view: boolean
trusted_access.allow_communications: boolean
trusted_access.allow_completion_view: boolean
trusted_access.auto_revoke_on_order_closed: boolean
trusted_access.max_trusted_persons_per_order: integer
```

## Impersonation & Emergency Policies
```yaml
access.impersonation.enabled: boolean
access.impersonation.max_duration_minutes: integer
access.impersonation.notify_subject: boolean
access.impersonation.requires_approval: boolean
access.emergency.enabled: boolean
access.emergency.max_duration_minutes: integer
access.emergency.post_review_required: boolean
```

## Audit Policies
```yaml
audit.access.log_all_denies: boolean
audit.access.log_sensitive_allows: boolean
audit.role_changes.retention_days: integer
audit.identity_changes.retention_days: integer
audit.emergency_access.retention_days: integer
```
