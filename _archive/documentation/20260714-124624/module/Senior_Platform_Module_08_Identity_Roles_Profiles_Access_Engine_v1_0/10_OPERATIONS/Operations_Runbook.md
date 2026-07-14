# Operations Runbook

## Common Admin Operations
- Lock account.
- Unlock account.
- Revoke session.
- Revoke device trust.
- Suspend actor.
- Restore actor.
- Invite organization staff.
- Remove organization staff.
- Approve provider affiliation.
- Revoke provider affiliation.
- Approve/reject verification.
- Publish/hide profile.
- Revoke trusted access.

## Incident Runbooks

### Suspected Account Takeover
1. Lock account.
2. Revoke all sessions and tokens.
3. Revoke device trust.
4. Trigger credential reset.
5. Review recent access decisions and sensitive data views.
6. Publish security audit event.

### Cross-Tenant Access Attempt
1. Block request.
2. Log `access.policy_violation_detected`.
3. Capture actor, resource, tenant and correlation IDs.
4. Alert security operations.
5. Review recent role and delegation changes.

### Impersonation Abuse
1. End impersonation session.
2. Suspend impersonating actor if required.
3. Export audit trail.
4. Require post-incident review.
5. Rotate affected credentials if exposed.

### Fake Company Affiliation
1. Suspend affiliation request or membership.
2. Notify organization administrator if configured.
3. Review provider verification status.
4. Revoke organization provider context if needed.

## Observability Metrics
- registration conversion by actor type;
- verification approval/rejection rate;
- affiliation approval latency;
- role changes per tenant;
- denied access decisions by reason;
- suspicious device events;
- trusted access grants created/revoked;
- impersonation/emergency access frequency;
- sensitive data view count.
