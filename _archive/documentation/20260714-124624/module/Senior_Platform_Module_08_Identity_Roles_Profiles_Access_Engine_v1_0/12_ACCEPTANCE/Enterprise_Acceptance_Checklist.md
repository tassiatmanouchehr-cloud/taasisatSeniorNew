# Module 08 Enterprise Acceptance Checklist

## Generic Architecture
- [ ] No domain-specific actor names exist in core models.
- [ ] Actor types are registry-driven.
- [ ] Permission keys are generic and capability-based.
- [ ] Profile fields are classified by visibility and sensitivity.

## Identity & Authentication
- [ ] Account, identity, credential, session and device are separate concepts.
- [ ] Login state never equals authorization.
- [ ] Session revocation and device revocation are supported.
- [ ] MFA obligations can be returned by access decisions.

## Authorization
- [ ] Deny-by-default is enforced.
- [ ] RBAC supports platform, tenant, organization, department and resource scopes.
- [ ] Custom roles are tenant-bounded.
- [ ] Temporary and delegated permissions include expiry and audit.
- [ ] Cross-tenant access is blocked unless explicitly allowed.

## Organization & Provider Management
- [ ] Organization registration and verification lifecycle exists.
- [ ] Organization staff invitation and role assignment lifecycle exists.
- [ ] Provider independent registration exists.
- [ ] Provider-company affiliation requires company approval unless CCS policy explicitly says otherwise.
- [ ] Provider may remain independent after rejection.

## Customer & Trusted Access
- [ ] Customer private profile is protected.
- [ ] Trusted person access is order-scoped.
- [ ] Trusted person cannot access customer account or financial history.
- [ ] Trusted access is revocable and expirable.

## Profiles & Verification
- [ ] Provider, organization and platform public profiles are supported.
- [ ] Public/private/sensitive fields are separated.
- [ ] Document visibility is restricted.
- [ ] Verification lifecycle supports submit, review, approve, reject, expire and revoke.
- [ ] Badge issuance and revocation are modeled.

## CES Integration
- [ ] All meaningful identity, role, profile, verification and access changes publish CES events.
- [ ] Events include actor, tenant, correlation and causation metadata.
- [ ] Security events are auditable.

## CCS Integration
- [ ] Registration policies are configurable.
- [ ] Affiliation policies are configurable.
- [ ] Role and permission policies are configurable.
- [ ] Session/device/MFA policies are configurable.
- [ ] Profile visibility policies are configurable.
- [ ] Verification policies are configurable.
- [ ] Trusted access policies are configurable.
- [ ] Impersonation/emergency policies are configurable.

## Security
- [ ] Sensitive data access is logged.
- [ ] Impersonation requires reason, permission, MFA and audit.
- [ ] Emergency access is time-bounded and reviewed.
- [ ] UI visibility is not treated as authorization.
