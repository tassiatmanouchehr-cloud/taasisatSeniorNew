# Modules 01–08 Freeze Gate v1.0

A module can be frozen only if all checks pass.

## Genericity

- No domain-specific actor names in core architecture.
- Reference implementation examples are isolated.
- Canonical actor vocabulary is used.

## CES

- All meaningful state changes emit CES events.
- Event names follow `module.entity.action`.
- Event payloads include tenant and actor context where applicable.

## CCS

- All policies are registered as CCS keys.
- Each key has type, default, scope and audit behavior.

## Identity and Access

- Protected operations are defined by modules.
- Authorization is owned by Module 08.
- Permission duplication is removed.

## Communication

- No direct communication delivery outside Module 07.
- Business modules publish events only.

## Audit and Security

- Sensitive data is classified.
- Access to sensitive records is audited.
- Administrative overrides are traceable.

## Dependency

- No circular dependencies.
- Cross-module contracts are explicit.
