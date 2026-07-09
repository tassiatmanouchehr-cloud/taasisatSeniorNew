# Event Architecture

Status: current as of Module 18. Two intentionally separate systems exist.
This document exists because the names are easy to confuse — this is the
single place that disambiguates them.

## 1. DomainEvent (Module 09) — in-memory, synchronous

- `apps.kernel.events.base.DomainEvent` — a **frozen dataclass**, not a
  model. Nothing about it is persisted by itself.
- `apps.kernel.events.publisher.publish(event)` — audits the fact of
  publication via `AuditService`, then synchronously calls every handler
  registered for `event.event_type`. One handler raising is caught and
  logged; it never breaks the others or the caller's transaction
  (best-effort fan-out, not a transactional guarantee — see the module's
  own docstring).
- `apps.kernel.events.registry.EventRegistry` — the handler registry.
  `register()` is idempotent.
- `apps.kernel.events.handlers` — the only current consumer: creates
  `Notification` rows (`status=PENDING`, nothing dispatches them).
  Registered from `apps.notifications.apps.NotificationsConfig.ready()`,
  not at `apps.kernel` import time — see `dependency-graph.md` for why
  this doesn't create a circular import.

Use this when: you want an in-process side effect (today: notifications)
that must never block or fail the business transaction that triggered it.

## 2. EventOutbox / CES (Module 25 foundation) — persisted, async

- `apps.kernel.models.event_outbox.EventOutbox` — a real model,
  implementing the transactional outbox pattern. Written in the same DB
  transaction as the business state change.
- `apps.kernel.services.event_publisher.EventPublisher.publish(...)` —
  the **only** code allowed to *create* `EventOutbox` rows. Used
  pervasively: `finance`, `reviews` (moderation), and others publish
  CES-envelope events (`tenant_id`, `source_module`, `correlation_id`,
  `idempotency_key`, `privacy_class`, `audit_class`, `payload`) through
  this.
- `apps.kernel.tasks` (the Celery outbox worker —
  `publish_outbox_events`/`cleanup_dead_letter_events`) is the only code
  that *reads or updates* `EventOutbox` rows (polls `PENDING`, marks
  `PUBLISHED`/`FAILED`/`DEAD_LETTER`). No business module reads or writes
  `EventOutbox` directly — verified by grep: every `EventOutbox.objects`
  call site in the codebase is in one of these two files.
- A Celery task (`kernel.publish_outbox_events`, scheduled every 5s in
  `CELERY_BEAT_SCHEDULE`) is meant to poll and dispatch pending rows to
  external subscribers. **No such subscriber exists yet** — this
  infrastructure is provisioned but not yet load-bearing for any current
  feature.

Use this when: another module (present or future) needs a durable,
replayable record that something happened, independent of whether
anything is listening today.

## They do not interact

- `EventPublisher.publish()` never touches `DomainEvent`/`EventRegistry`.
- `apps.kernel.events.publisher.publish()` never touches `EventOutbox`.
- A business action that needs both (e.g. "notify the user AND emit a
  durable CES event") calls both independently — there's no automatic
  bridging, and none should be added without a real subscriber to justify
  it (see `technical-debt-register.md`).

## Guardrail

`apps/kernel/tests/test_architecture_guardrails.py`
(`EventSystemSeparationTest`) asserts, by source inspection, that no
`EventOutbox.objects` call exists outside
`apps.kernel.services.event_publisher`/`apps.kernel.tasks`, and that
`apps/kernel/events/base.py`/`publisher.py` never import
`apps.kernel.models.event_outbox`.
