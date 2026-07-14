# Tenant Boundary Standard

## Tenant Isolation Requirements
- Every business record must belong to exactly one tenant unless marked platform-global.
- Platform-global records must be immutable or centrally governed.
- Cross-tenant access must require explicit platform-level permission and audit classification.
- Tenant data must not be mixed in projections without isolation markers.

## Scope Resolution Order
1. Request context
2. Authenticated actor tenant
3. Resource owner tenant
4. Explicit platform override
5. Deny if ambiguous

## Cross-Tenant Operations
Allowed only through:
- Platform administration contract
- Aggregated analytics with anonymization
- Explicit marketplace federation contract
- Legal/compliance export workflow
