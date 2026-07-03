# Versioning & Migration Rules

## Semantic Versioning
- Major: breaking contract change.
- Minor: backward-compatible capability addition.
- Patch: clarification or non-contractual correction.

## Frozen Contract Rule
A frozen v1.0 contract may be extended with optional fields but not mutated incompatibly.

## Migration Requirements
Every breaking change requires:
- New version
- Compatibility matrix update
- Migration notes
- Consumer impact list
- Rollback plan
- Deprecation timeline
- Acceptance tests

## Deprecation States
- active
- deprecated
- sunset_scheduled
- retired
- blocked
