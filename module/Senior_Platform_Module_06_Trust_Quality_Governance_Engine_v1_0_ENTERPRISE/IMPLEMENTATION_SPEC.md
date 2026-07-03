# Module 06 — Implementation Specification v1.0

This document binds the implementation layer:
- Permission Matrix
- Cross-Module Contracts
- Error Catalog
- Reporting Model
- API Contracts
- ADR

## Implementation Principle

No new feature is added here. This layer makes the module implementable and freeze-ready.

## Mandatory Implementation Constraints

1. Use TrustCase as governance aggregate.
2. Keep Signal, Case, Decision and Enforcement separate.
3. Require CaseDecision before Enforcement.
4. Delegate financial execution to Module 05.
5. Use CES for events.
6. Use CCS for configuration.
7. Preserve lineage over mutation.
8. Enforce tenant and organization boundaries.
9. Preserve Generic Service Marketplace mapping only as reference implementation.
