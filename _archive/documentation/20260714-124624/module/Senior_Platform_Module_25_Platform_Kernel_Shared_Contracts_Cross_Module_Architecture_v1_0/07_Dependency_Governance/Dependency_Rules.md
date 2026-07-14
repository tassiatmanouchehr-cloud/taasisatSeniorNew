# Dependency Rules

## Dependency Direction
- Modules 01–24 may depend on Module 25 contracts.
- Module 25 may depend on no business module.
- Business modules may consume public contracts of other modules, not internals.
- Circular dependencies are forbidden.

## Allowed Integration Patterns
- Public API contract
- Command contract
- Domain event consumption
- Projection contract
- Workflow orchestration contract
- Adapter interface contract

## Forbidden Integration Patterns
- Shared mutable database tables across module ownership boundaries
- Direct imports of internal services
- Hidden synchronous calls not documented in dependency map
- Undeclared event consumption
- Configuration keys owned by another module without contract
