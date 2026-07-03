# Threat Model & Security Controls

## Primary Threats
- Account takeover.
- Privilege escalation.
- Cross-tenant data leakage.
- Unauthorized staff access.
- Fake provider/company affiliation.
- Public exposure of private profile fields.
- Sensitive document leakage.
- Abuse of trusted-person invitations.
- Silent impersonation abuse.
- Emergency access misuse.
- Session/token theft.
- Device spoofing.

## Required Controls
1. MFA for critical actions.
2. Re-authentication for role changes, impersonation, emergency access and sensitive document viewing.
3. Tenant-scoped authorization on every protected resource.
4. Immutable audit for identity, profile, permission and verification changes.
5. Explicit approval for provider-company affiliation.
6. Deny-by-default policy engine.
7. Token scope minimization and expiry.
8. Device trust policy and suspicious-device detection.
9. Field-level profile visibility enforcement.
10. Document access isolation and signed temporary document URLs where documents are stored externally.
11. Rate limits on registration, affiliation and trusted-person invitations.
12. Automatic revocation on account lock, membership revocation, order closure or governance restriction.

## Critical Audit Events
- Role assignment or revocation.
- Custom role creation/update.
- Permission delegation.
- Temporary permission grant.
- Sensitive data viewing.
- Verification approval/rejection.
- Trusted access activation.
- Impersonation start/end.
- Emergency access start/end.
- Cross-tenant access attempt.

## Security Invariant
A user interface must never be treated as a security boundary. All access decisions must be enforced server-side through Module 08 decisions or equivalent policy enforcement integration.
