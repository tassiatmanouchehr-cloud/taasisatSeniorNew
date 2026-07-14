# CES Event Naming Standard v1.0

## Format

`module.entity.action`

Examples:

- `request.created`
- `request.approved`
- `matching.run.started`
- `matching.candidate.generated`
- `booking.assignment.created`
- `booking.assignment.revoked`
- `execution.session.started`
- `execution.session.completed`
- `financial.invoice.issued`
- `financial.payment.received`
- `trust.case.opened`
- `trust.enforcement.recommended`
- `communication.message.sent`
- `identity.user.created`
- `identity.role_assigned`

## Rules

1. Events describe facts that already happened.
2. Events are immutable.
3. Events must include tenant context when tenant-scoped.
4. Events must include actor context when caused by an actor.
5. Events must not contain sensitive document payloads.
6. Events must be stable integration contracts, not UI notifications.
7. Communication dispatch is never an event producer responsibility except inside Module 07.
