# Audit Envelope Standard

## Audit Envelope
```json
{
  "audit_id": "aud_...",
  "occurred_at": "ISO-8601",
  "tenant_id": "...",
  "actor": {},
  "action": "contract.publish",
  "resource": {},
  "before_hash": "optional",
  "after_hash": "optional",
  "reason": "optional",
  "correlation_id": "...",
  "ip_context": "optional",
  "device_context": "optional",
  "audit_class": "standard|financial|security|compliance",
  "retention_policy": "..."
}
```

## Rules
- Audit records are append-only.
- Material changes to contracts, policies, permissions, configuration, and compatibility rules must be audited.
- Audit records must preserve actor and impersonation context.
- Sensitive values should be hashed, redacted, or referenced securely.
