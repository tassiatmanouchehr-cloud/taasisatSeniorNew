# Public API Contracts

## Access Decision API
```http
POST /identity-access/v1/decisions
```
Request:
```json
{
  "actor_id": "uuid",
  "actor_context_id": "uuid|null",
  "action": "profile.private.read",
  "resource": {"type": "profile", "id": "uuid"},
  "scope": {"type": "tenant", "id": "uuid"},
  "context": {"session_id": "uuid", "device_id": "uuid"}
}
```
Response:
```json
{
  "result": "allow|deny",
  "reason_code": "string",
  "obligations": ["mfa_required", "mask_phone"],
  "decision_id": "uuid"
}
```

## Actor Lookup API
```http
GET /identity-access/v1/actors/{actor_id}
```
Returns actor type, status, tenant contexts and safe display metadata.

## Profile Visibility API
```http
POST /identity-access/v1/profiles/{profile_id}/resolve-visibility
```
Returns only fields visible to the requesting actor under current policy.

## Provider Affiliation API
```http
POST /identity-access/v1/provider-affiliations
POST /identity-access/v1/provider-affiliations/{request_id}/approve
POST /identity-access/v1/provider-affiliations/{request_id}/reject
POST /identity-access/v1/provider-affiliations/{membership_id}/revoke
```

## Trusted Access API
```http
POST /identity-access/v1/trusted-access/invitations
POST /identity-access/v1/trusted-access/{grant_id}/accept
POST /identity-access/v1/trusted-access/{grant_id}/revoke
GET  /identity-access/v1/trusted-access/resources/{resource_type}/{resource_id}
```

## Verification API
```http
POST /identity-access/v1/verifications
POST /identity-access/v1/verifications/{verification_id}/submit
POST /identity-access/v1/verifications/{verification_id}/approve
POST /identity-access/v1/verifications/{verification_id}/reject
```

## Role API
```http
POST /identity-access/v1/roles
POST /identity-access/v1/role-assignments
DELETE /identity-access/v1/role-assignments/{assignment_id}
POST /identity-access/v1/delegations
DELETE /identity-access/v1/delegations/{delegation_id}
```
