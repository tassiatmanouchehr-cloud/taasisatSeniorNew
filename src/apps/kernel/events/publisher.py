"""
Domain event publisher — Module 09 foundation.

publish(event) audits the fact that the event was published, then invokes
every handler registered for event.event_type. Handlers are isolated from
each other: one handler raising never prevents the others from running,
and never propagates out of publish() — this is a best-effort, in-process
notification fan-out, not a transactional guarantee. It must never break
the business transaction that published the event.
"""

import logging

from apps.kernel.services.audit_service import AuditService
from apps.kernel.models.audit import AuditClassification

from .base import DomainEvent
from .registry import EventRegistry

logger = logging.getLogger(__name__)

SOURCE_MODULE = "M09"


def publish(event: DomainEvent) -> None:
    """Audit and dispatch `event` to every handler registered for its event_type."""
    AuditService.log(
        tenant_id=event.tenant_id,
        action=f"domain_event.{event.event_type}",
        resource_type=event.aggregate_type,
        resource_id=event.aggregate_id,
        module_id=SOURCE_MODULE,
        actor_id=event.actor_id,
        audit_class=AuditClassification.STANDARD,
        after={"event_id": str(event.id), "payload": event.payload},
    )

    handlers = EventRegistry.get_handlers(event.event_type)

    for handler in handlers:
        try:
            handler(event)
        except Exception:
            logger.exception(
                "Domain event handler %r failed for event_type=%s (event_id=%s); "
                "continuing with remaining handlers.",
                handler, event.event_type, event.id,
            )
