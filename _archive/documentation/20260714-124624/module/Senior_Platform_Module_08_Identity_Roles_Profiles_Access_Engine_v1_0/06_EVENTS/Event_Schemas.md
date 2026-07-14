# Representative Event Payload Schemas

## provider.affiliation_requested
```yaml
event_type: provider.affiliation_requested
payload:
  provider_actor_id: uuid
  organization_id: uuid
  requested_identifier: string
  request_id: uuid
  status: pending_approval
```

## provider.affiliation_approved
```yaml
event_type: provider.affiliation_approved
payload:
  provider_actor_id: uuid
  organization_id: uuid
  membership_id: uuid
  approved_by_actor_id: uuid
  effective_actor_context: ORGANIZATION_PROVIDER
```

## role_assignment.created
```yaml
event_type: role_assignment.created
payload:
  assignment_id: uuid
  actor_id: uuid
  role_id: uuid
  scope_type: string
  scope_id: uuid|null
  assigned_by_actor_id: uuid
  expires_at: datetime|null
```

## trusted_access.activated
```yaml
event_type: trusted_access.activated
payload:
  grant_id: uuid
  customer_actor_id: uuid
  trusted_actor_id: uuid
  resource_type: order
  resource_id: uuid
  permissions:
    - order.progress.view
    - order.communication.receive
    - order.completion.view
  expires_at: datetime|null
```

## access.decision_logged
```yaml
event_type: access.decision_logged
payload:
  decision_id: uuid
  actor_id: uuid
  action: string
  resource_type: string
  resource_id: uuid|null
  scope_type: string
  scope_id: uuid|null
  result: allow|deny
  reason_code: string
  obligations: list[string]
```

## verification.approved
```yaml
event_type: verification.approved
payload:
  verification_id: uuid
  subject_actor_id: uuid
  verification_type: string
  decided_by_actor_id: uuid
  approved_until: datetime|null
  issued_badges: list[uuid]
```
