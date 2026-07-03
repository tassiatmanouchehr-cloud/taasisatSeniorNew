# Impersonation & Emergency Access Policy

## Impersonation
Impersonation allows a highly privileged platform actor to view or operate as another actor for support or compliance purposes.

### Requirements
- Explicit permission: `access.impersonation.start`.
- MFA or re-authentication.
- Mandatory reason code and free-text justification.
- Time-limited session.
- Visible audit trail.
- Optional customer/tenant notification according to CCS.
- Prohibited for financial secrets, credentials and sensitive documents unless separately authorized.

## Emergency Access
Emergency access is a break-glass flow for critical operational incidents.

### Requirements
- Critical permission: `access.emergency.start`.
- Short maximum duration.
- Post-action review.
- Elevated alerting.
- Immutable audit.
- Automatic revocation.

## Prohibited Use
- Convenience access.
- Silent privilege escalation.
- Bypassing sanctions without formal override.
- Viewing private documents unrelated to the emergency scope.
- Modifying financial settlement records without Module 05 authority.
