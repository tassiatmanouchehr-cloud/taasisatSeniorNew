# Shared Error Model

## Error Envelope
```json
{
  "error_code": "KERNEL.CONFLICT.VERSION_MISMATCH",
  "message": "Human-readable safe message",
  "category": "validation|permission|conflict|not_found|rate_limit|provider|system",
  "severity": "info|warning|error|critical",
  "retryable": false,
  "correlation_id": "...",
  "tenant_id": "...",
  "details": {}
}
```

## Error Code Families
- KERNEL.VALIDATION
- KERNEL.PERMISSION
- KERNEL.TENANT_BOUNDARY
- KERNEL.CONFLICT
- KERNEL.NOT_FOUND
- KERNEL.RATE_LIMIT
- KERNEL.IDEMPOTENCY
- KERNEL.PROVIDER
- KERNEL.SYSTEM
- KERNEL.DEPRECATION

## Rules
- Error codes are stable public contracts.
- Internal exception names must not be exposed.
- Permission failures must not reveal existence of inaccessible resources.
- Retryable errors must identify safe retry behavior.
