# API Contract Conventions

## Mandatory API Metadata
All public API operations must define:
- operation_id
- owning_module
- contract_version
- permission_required
- tenant_scope
- idempotency_behavior
- rate_limit_class
- audit_class
- error_codes
- deprecation_status

## Request Rules
- Commands must be explicit.
- Partial updates must define merge semantics.
- Idempotency keys are mandatory for financial, booking, notification, and reward-affecting operations.
- Tenant ID must be derived from authenticated context or explicitly validated.

## Response Rules
- Responses must not leak internal models.
- Every response must include correlation_id.
- Mutations should return resource reference and lifecycle state.
- Long-running operations must return job or workflow reference.
