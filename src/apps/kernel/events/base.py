"""
DomainEvent — the immutable envelope passed to apps.kernel.events.publish().

Distinct from apps.kernel.models.event_outbox.EventOutbox: that model is
the persisted, async-dispatched CES envelope. DomainEvent is an in-memory,
synchronous value object — nothing about it is written to the database by
itself; only registered handlers decide what (if anything) to persist.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from django.utils import timezone

# Well-known event_type constants for the notification foundation (Module 09).
# Business modules may publish other event_type strings too; these are just
# the ones the notifications app currently has handlers for.
ORDER_CREATED = "OrderCreated"
ORDER_ASSIGNED = "OrderAssigned"
ORDER_STARTED = "OrderStarted"
ORDER_COMPLETED = "OrderCompleted"
INVOICE_ISSUED = "InvoiceIssued"

# Order Share Link events (Customer Experience Phase 1). No notification
# handler is registered for these yet — publishing them still gets an
# AuditLog row for free via publish()'s unconditional audit call, which is
# the whole point: every share-link lifecycle transition is now audited
# even before any handler exists.
SHARE_LINK_CREATED = "ShareLinkCreated"
SHARE_LINK_REVOKED = "ShareLinkRevoked"
SHARE_LINK_ACCESSED = "ShareLinkAccessed"


@dataclass(frozen=True)
class DomainEvent:
    """
    Immutable record of something that already happened in the domain.

    Required:
        event_type: e.g. "OrderCreated" — see constants above for the
            names the notifications app currently handles.
        tenant_id: tenant this event belongs to (mandatory — CES tenant rule).
        aggregate_type: name of the entity type this event is about, e.g. "Order".
        aggregate_id: id of that entity instance.
        payload: domain-specific event data (handlers read what they need from here).

    Optional:
        actor_id: who/what caused this event (Person id), if known.
        id: unique event id, auto-generated.
        occurred_at: when the underlying business fact occurred, defaults to now.

    Immutable after construction: assigning to any field raises
    dataclasses.FrozenInstanceError.
    """

    event_type: str
    tenant_id: uuid.UUID
    aggregate_type: str
    aggregate_id: uuid.UUID
    payload: dict[str, Any] = field(default_factory=dict)
    actor_id: uuid.UUID | None = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    occurred_at: datetime = field(default_factory=timezone.now)

    def __post_init__(self):
        if not self.event_type:
            raise ValueError("DomainEvent requires a non-empty event_type.")
        if not self.tenant_id:
            raise ValueError("DomainEvent requires a tenant_id.")
        if not self.aggregate_type:
            raise ValueError("DomainEvent requires a non-empty aggregate_type.")
        if not self.aggregate_id:
            raise ValueError("DomainEvent requires an aggregate_id.")
