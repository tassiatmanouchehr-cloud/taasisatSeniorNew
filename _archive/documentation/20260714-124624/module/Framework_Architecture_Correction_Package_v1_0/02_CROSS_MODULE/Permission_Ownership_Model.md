# Permission Ownership Model v1.0

Module 08 owns permission evaluation. Other modules define protected operations only.

## Pattern

Each business module must publish a Protected Operations Catalog:

- operation key
- owning module
- resource type
- required context
- default roles allowed
- escalation path
- audit requirement

Example:

`booking.assignment.create` is evaluated by Module 08 using tenant, actor, organization membership, assignment policy and resource context.

## Rule

A module may reject an action for domain-state reasons, but it must not independently decide whether an actor is authorized. Authorization decisions are delegated to Module 08.
