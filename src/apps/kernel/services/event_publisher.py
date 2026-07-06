"""
CES Event Publisher service.

Provides the API for business modules to emit events to the outbox.
All event emission goes through this service — modules never write to
EventOutbox directly.

Usage:
    from apps.kernel.services import EventPublisher

    EventPublisher.publish(
        tenant_id=request.tenant.id,
        event_type="Request.Created.v1",
        source_module="M01",
        source_entity_id=request_obj.id,
        source_entity_type="ServiceRequest",
        payload={"request_id": str(request_obj.id), "status": "draft"},
        actor_id=request.user.person_id,
        correlation_id=request.correlation_id,
    )

The event is written in the same database transaction as the calling code.
A background worker (Celery task) will poll and dispatch pending events.

References:
- ADR-001.14 (Business modules emit CES events only)
- Module 25: CES_Kernel_Envelope.md
- Phase 1 Implementation Plan: Sprint 2 — Event Outbox
"""

import logging
import uuid
from typing import Any

from django.utils import timezone

from apps.kernel.models.event_outbox import AuditClass, EventOutbox, PrivacyClass

logger = logging.getLogger(__name__)


class EventPublisher:
    """
    Central service for publishing CES-envelope-compatible events.

    All business modules use this service to emit events into the outbox.
    Events are written within the current database transaction, ensuring
    atomicity with the business state change (outbox pattern).
    """

    @staticmethod
    def publish(
        *,
        tenant_id: uuid.UUID,
        event_type: str,
        source_module: str,
        payload: dict[str, Any],
        source_entity_id: uuid.UUID | None = None,
        source_entity_type: str = "",
        actor_id: uuid.UUID | None = None,
        actor_type: str = "",
        correlation_id: uuid.UUID | None = None,
        causation_id: uuid.UUID | None = None,
        idempotency_key: str = "",
        event_version: str = "1.0",
        privacy_class: str = PrivacyClass.INTERNAL,
        audit_class: str = AuditClass.STANDARD,
        schema_ref: str = "",
    ) -> EventOutbox:
        """
        Publish an event to the outbox.

        This creates an EventOutbox record within the current database transaction.
        The event will be dispatched asynchronously by the outbox publisher worker.

        Args:
            tenant_id: Tenant that owns this event.
            event_type: Fully qualified event name, e.g., "Request.Created.v1".
            source_module: Module code, e.g., "M01".
            payload: Domain-specific event data.
            source_entity_id: ID of the entity that changed.
            source_entity_type: Type name of the entity.
            actor_id: Person/system that caused the event.
            actor_type: Type of actor ('person', 'system', 'integration').
            correlation_id: Request chain correlation ID. Generated if not provided.
            causation_id: ID of the causing event (for event chains).
            idempotency_key: Prevents duplicate processing.
            event_version: Schema version of this event type.
            privacy_class: Privacy classification.
            audit_class: Audit classification.
            schema_ref: Reference to payload JSON schema.

        Returns:
            The created EventOutbox instance.

        Raises:
            ValueError: If required fields are missing or invalid.
        """
        if not tenant_id:
            raise ValueError("tenant_id is required for event publishing")
        if not event_type:
            raise ValueError("event_type is required for event publishing")
        if not source_module:
            raise ValueError("source_module is required for event publishing")

        # Generate correlation_id if not provided
        if not correlation_id:
            correlation_id = uuid.uuid4()

        event = EventOutbox.objects.create(
            tenant_id=tenant_id,
            event_type=event_type,
            event_version=event_version,
            occurred_at=timezone.now(),
            source_module=source_module,
            source_entity_id=source_entity_id,
            source_entity_type=source_entity_type,
            actor_id=actor_id,
            actor_type=actor_type,
            correlation_id=correlation_id,
            causation_id=causation_id,
            idempotency_key=idempotency_key,
            privacy_class=privacy_class,
            audit_class=audit_class,
            schema_ref=schema_ref,
            payload=payload,
        )

        logger.debug(
            "Event published to outbox: %s (id=%s, correlation=%s)",
            event_type,
            event.id,
            correlation_id,
        )

        return event

    @staticmethod
    def publish_batch(
        *,
        events: list[dict[str, Any]],
    ) -> list[EventOutbox]:
        """
        Publish multiple events in a single database operation.

        Each dict in `events` must contain the same kwargs as `publish()`.
        All events are created within the current transaction.

        Args:
            events: List of event kwargs dicts.

        Returns:
            List of created EventOutbox instances.
        """
        outbox_records = []
        now = timezone.now()

        for event_data in events:
            if not event_data.get("correlation_id"):
                event_data["correlation_id"] = uuid.uuid4()

            outbox_records.append(
                EventOutbox(
                    tenant_id=event_data["tenant_id"],
                    event_type=event_data["event_type"],
                    event_version=event_data.get("event_version", "1.0"),
                    occurred_at=now,
                    source_module=event_data["source_module"],
                    source_entity_id=event_data.get("source_entity_id"),
                    source_entity_type=event_data.get("source_entity_type", ""),
                    actor_id=event_data.get("actor_id"),
                    actor_type=event_data.get("actor_type", ""),
                    correlation_id=event_data["correlation_id"],
                    causation_id=event_data.get("causation_id"),
                    idempotency_key=event_data.get("idempotency_key", ""),
                    privacy_class=event_data.get("privacy_class", PrivacyClass.INTERNAL),
                    audit_class=event_data.get("audit_class", AuditClass.STANDARD),
                    schema_ref=event_data.get("schema_ref", ""),
                    payload=event_data.get("payload", {}),
                )
            )

        created = EventOutbox.objects.bulk_create(outbox_records)

        logger.debug("Batch published %d events to outbox", len(created))

        return created
