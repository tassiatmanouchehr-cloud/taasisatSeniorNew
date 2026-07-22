# EVENTS, JOBS, AND INTEGRATIONS

**Last verified HEAD:** a5dbaf28703142edaa1d770ea8f3c2a45a12640f
**Last verified date:** 2026-07-14

---

## Event System

### Two Event Channels

1. **CES (Customer Event System)** — `EventPublisher.publish()` writes to `EventOutbox` table, polled by Celery task `kernel.publish_outbox_events`. Events dispatched by `kernel.dispatch_single_event`.

2. **Domain Events** — `DomainEvent` objects published via `transaction.on_commit()`. In-memory event envelope pattern.

### Event Registry

`apps/kernel/events/registry.py` — `EventRegistry` maps event types to handler callables.

### Event Types (~270+)

Key event types include: ORDER_CREATED, ORDER_ASSIGNED, ORDER_STARTED, ORDER_COMPLETED, BOOKING_ASSIGNMENT_CREATED, BOOKING_ASSIGNMENT_EXPIRED, MATCHING_RUN_STARTED, MATCHING_RUN_COMPLETED, EXECUTION_SESSION_CREATED, DISPUTE_OPENED, DISPUTE_RESOLVED, FINANCIAL ESCROW_* events, and many more.

### Event Outbox

`EventOutbox` model stores pending events. Celery task polls and dispatches. Dead-letter cleanup via `kernel.cleanup_dead_letter_events`.

## Celery Tasks (4)

| Task | Purpose |
|------|---------|
| `kernel.publish_outbox_events` | Poll pending events from outbox |
| `kernel.dispatch_single_event` | Process a single outbox event |
| `kernel.cleanup_dead_letter_events` | Archive dead-letter events |
| `kernel.refresh_config_cache` | Safety-net config cache refresh |

## Background Jobs

`JobDefinition` + `JobRun` model in `apps.jobs`. Job types registered via `JobRegistry`:

| Job Type | Purpose | Status |
|----------|---------|--------|
| `commission.payment_deadline.expire` | Expire payment deadlines | IMPLEMENTED (gated) |
| `commission.objection_period.auto_approve` | Auto-approve objection periods | IMPLEMENTED |
| `notifications.dispatch_pending` | Dispatch pending notifications | IMPLEMENTED (fake providers) |
| `payments.settlement.retry` | Retry failed settlement | IMPLEMENTED |
| `demo.no_op` | Demo handler | TEST ONLY |
| `demo.always_fail` | Demo handler | TEST ONLY |
| `demo.echo` | Demo handler | TEST ONLY |

Management command: `run_due_jobs` — sweeps and executes due jobs.

## External Integrations

| Integration | Status | Provider |
|-------------|--------|----------|
| Payment PSP | MOCKED | `FakePaymentProviderAdapter` |
| SMS | MOCKED | `FakeSmsProvider` |
| Email | MOCKED | `FakeEmailProvider` |
| Push | MOCKED | `FakePushProvider` |
| In-App | MOCKED | `FakeInAppProvider` |
| CI/CD | NEVER RUN | `.github/workflows/ci.yml` exists |
| Docker | CONFIG EXISTS | `docker-compose.yml` exists |

All real external integrations are explicitly documented as deferred to separate epics.
