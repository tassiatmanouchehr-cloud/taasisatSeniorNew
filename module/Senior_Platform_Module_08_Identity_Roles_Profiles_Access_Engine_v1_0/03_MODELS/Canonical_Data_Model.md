# Canonical Data Model

## Identity Aggregate
```yaml
Identity:
  identity_id: uuid
  identity_type: human|organization|system
  legal_name: string
  display_name: string
  verification_state: unverified|pending|verified|rejected|expired|suspended
  risk_state: normal|watchlisted|restricted|locked
  created_at: datetime
  updated_at: datetime
```

## Account Aggregate
```yaml
Account:
  account_id: uuid
  identity_id: uuid
  status: pending|active|restricted|locked|closed
  primary_email_id: uuid|null
  primary_phone_id: uuid|null
  login_enabled: boolean
  mfa_state: not_enabled|optional|required|enabled|locked
```

## Credential
```yaml
Credential:
  credential_id: uuid
  account_id: uuid
  credential_type: password|passkey|oauth|sso|otp_only|api_key
  status: active|rotated|revoked|compromised
  last_used_at: datetime|null
```

## Actor
```yaml
Actor:
  actor_id: uuid
  account_id: uuid|null
  identity_id: uuid
  actor_type: enum_from_actor_registry
  tenant_id: uuid|null
  status: pending|active|suspended|revoked|archived
  default_profile_id: uuid|null
```

## Organization
```yaml
Organization:
  organization_id: uuid
  identity_id: uuid
  tenant_id: uuid
  legal_name: string
  public_name: string
  status: onboarding|active|restricted|suspended|closed
  verification_state: unverified|pending|verified|rejected|expired
```

## Department
```yaml
Department:
  department_id: uuid
  organization_id: uuid
  parent_department_id: uuid|null
  name: string
  status: active|archived
```

## Membership
```yaml
Membership:
  membership_id: uuid
  organization_id: uuid
  actor_id: uuid
  membership_type: staff|provider|owner|external_delegate
  status: invited|pending_approval|active|rejected|suspended|revoked|expired
  starts_at: datetime|null
  ends_at: datetime|null
```

## Role Assignment
```yaml
RoleAssignment:
  assignment_id: uuid
  actor_id: uuid
  role_id: uuid
  scope_type: platform|tenant|organization|department|resource|order
  scope_id: uuid|null
  status: active|suspended|revoked|expired
  assigned_by_actor_id: uuid
  expires_at: datetime|null
```

## Permission
```yaml
Permission:
  permission_key: string
  category: string
  description: string
  risk_level: low|medium|high|critical
  requires_audit: boolean
```

## Profile
```yaml
Profile:
  profile_id: uuid
  actor_id: uuid
  profile_type: provider|organization|platform|customer_private|staff_private
  publication_state: draft|pending_review|published|hidden|suspended|archived
  visibility_policy_id: uuid
```

## Profile Field
```yaml
ProfileField:
  field_id: uuid
  profile_id: uuid
  field_key: string
  value_ref: string
  classification: public|private|sensitive|restricted
  visibility: public|authenticated|same_tenant|owner_only|role_based|hidden
  review_state: not_required|pending|approved|rejected
```

## Verification Request
```yaml
VerificationRequest:
  verification_id: uuid
  subject_actor_id: uuid
  verification_type: identity|professional_license|organization|document|address|contact
  status: draft|submitted|in_review|approved|rejected|expired|revoked
  submitted_at: datetime|null
  decided_at: datetime|null
  decided_by_actor_id: uuid|null
```

## Trusted Access Grant
```yaml
TrustedAccessGrant:
  grant_id: uuid
  customer_actor_id: uuid
  trusted_actor_id: uuid
  resource_type: order
  resource_id: uuid
  permissions: list[string]
  status: invited|active|revoked|expired
  expires_at: datetime|null
```
