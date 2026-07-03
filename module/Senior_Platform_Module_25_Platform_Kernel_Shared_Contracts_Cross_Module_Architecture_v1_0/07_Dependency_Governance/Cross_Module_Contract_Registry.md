# Cross-Module Contract Registry

## Registry Fields
Each contract must declare:
- contract_id
- owning_module
- contract_type: api|event|command|projection|configuration|adapter|permission|error
- version
- stability: experimental|stable|deprecated|retired
- consumers
- compatibility_policy
- deprecation_policy
- test_coverage_required

## Review Requirements
A contract cannot be frozen unless:
- Ownership is clear.
- Schema is documented.
- Error behavior is documented.
- Tenant boundary is documented.
- Audit class is documented.
- Compatibility rules are documented.
