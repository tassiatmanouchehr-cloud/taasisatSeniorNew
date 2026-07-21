"""
Celery tasks for the Platform Kernel (Module 25).

Tasks:
- publish_outbox_events: Polls pending events from outbox and dispatches
- dispatch_single_event: Processes a single event (called by publisher)
- cleanup_dead_letter_events: Archives/reports dead-letter events (daily)
- refresh_config_cache: Invalidates stale config cache entries (periodic)

These tasks form the backbone of the CES event-driven architecture.
Business modules never call these directly — they use EventPublisher.publish()
which writes to the outbox; these tasks handle async dispatch.

References:
- ADR-001.14 (Business modules emit CES events only)
- Phase 1 Implementation Plan: Sprint 2 — Celery Tasks
"""

import logging

from celery import shared_task
from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    name="kernel.publish_outbox_events",
    bind=True,
    max_retries=0,
    ignore_result=True,
)
def publish_outbox_events(self, batch_size=100):
    """
    Poll pending events from the outbox and dispatch them.

    This is the primary outbox publisher task. It runs periodically
    (every 2-5 seconds via Celery Beat) and processes pending events
    in batches.

    Events that are in 'failed' status with next_retry_at <= now are
    also picked up for retry.

    Args:
        batch_size: Maximum number of events to process per run.
    """
    from apps.kernel.models.event_outbox import EventOutbox, EventStatus

    now = timezone.now()

    # Get pending events + failed events ready for retry
    events = EventOutbox.objects.filter(
        Q(status=EventStatus.PENDING) | Q(status=EventStatus.FAILED, next_retry_at__lte=now)
    ).order_by("created_at")[:batch_size]

    if not events:
        return

    processed = 0
    failed = 0

    for event in events:
        try:
            # Dispatch the event to consumers
            dispatch_single_event.delay(str(event.id))
            processed += 1
        except Exception as e:
            logger.error(
                "Failed to queue event %s for dispatch: %s",
                event.id,
                str(e),
            )
            failed += 1

    logger.info(
        "Outbox publisher: queued %d events, %d failures (batch=%d)",
        processed,
        failed,
        batch_size,
    )


@shared_task(
    name="kernel.dispatch_single_event",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    ignore_result=True,
)
def dispatch_single_event(self, event_id: str):
    """
    Process a single event from the outbox.

    This task handles the actual dispatch of an event to its consumers.
    In the current implementation (Phase 1), consumers are internal
    Django signal handlers or direct service calls. In production,
    this would publish to a message broker (Redis Pub/Sub, RabbitMQ, etc.).

    On success: marks the event as published.
    On failure: marks as failed with exponential backoff.

    Args:
        event_id: UUID string of the EventOutbox record.
    """
    from apps.kernel.models.event_outbox import EventOutbox, EventStatus

    try:
        event = EventOutbox.objects.get(id=event_id)
    except EventOutbox.DoesNotExist:
        logger.error("Event not found in outbox: %s", event_id)
        return

    if event.status == EventStatus.PUBLISHED:
        logger.debug("Event already published: %s", event_id)
        return

    try:
        # --- Event Dispatch Logic ---
        # Phase 1: Log the event (consumers will be registered in later phases)
        # Future: Publish to Redis Pub/Sub, Kafka, or internal event bus
        _dispatch_to_consumers(event)

        # Mark as published
        event.mark_published()

        logger.debug(
            "Event dispatched: %s (type=%s, tenant=%s)",
            event.id,
            event.event_type,
            event.tenant_id,
        )

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        event.mark_failed(error_msg)

        logger.warning(
            "Event dispatch failed: %s (type=%s, attempt=%d/%d, error=%s)",
            event.id,
            event.event_type,
            event.retry_count,
            event.max_retries,
            error_msg,
        )

        # Re-raise for Celery retry if not dead-lettered
        if event.status != EventStatus.DEAD_LETTER:
            raise self.retry(exc=e, countdown=2**event.retry_count)


@shared_task(
    name="kernel.cleanup_dead_letter_events",
    ignore_result=True,
)
def cleanup_dead_letter_events(days_old=30):
    """
    Archive or report dead-letter events.

    Runs daily. Events in dead_letter status older than `days_old`
    are logged for investigation and optionally archived.

    Args:
        days_old: Age threshold for dead-letter events to report.
    """
    from apps.kernel.models.event_outbox import EventOutbox, EventStatus

    cutoff = timezone.now() - timezone.timedelta(days=days_old)

    dead_letters = EventOutbox.objects.filter(
        status=EventStatus.DEAD_LETTER,
        created_at__lt=cutoff,
    )

    count = dead_letters.count()
    if count > 0:
        logger.warning(
            "Dead letter cleanup: %d events older than %d days found. Review required before archival.",
            count,
            days_old,
        )
        # Future: Archive to cold storage, notify ops team
        # For now: just log for visibility


@shared_task(
    name="kernel.refresh_config_cache",
    ignore_result=True,
)
def refresh_config_cache():
    """
    Periodic task to ensure config cache doesn't become stale.

    In practice, cache invalidation happens on config change (via
    ConfigResolver.invalidate()). This task is a safety net that
    prevents indefinite staleness if an invalidation was missed.

    Runs every 5 minutes via Celery Beat.
    """

    # The Django cache backend handles TTL-based expiry automatically.
    # This task exists as a placeholder for future cache warming
    # or consistency checks.
    logger.debug("Config cache refresh check completed.")


def _dispatch_to_consumers(event):
    """
    Internal: Dispatch an event to registered consumers.

    Phase 1: No external consumers registered yet. Events are logged.
    Phase 5+: Module 07 (Communication), Module 17 (Analytics), etc.
    will register as consumers.

    Future implementation options:
    - Django signals (in-process)
    - Redis Pub/Sub (cross-process)
    - Celery task routing (dedicated consumer workers)
    - Kafka/RabbitMQ (enterprise scale)
    """
    # Phase 1: No-op dispatch (consumers don't exist yet)
    # The event is marked as published — it was successfully processed
    # by the outbox system even without downstream consumers.
    logger.debug(
        "Event dispatched (no consumers registered): %s [%s]",
        event.event_type,
        event.id,
    )
