"""
Domain Event infrastructure — Module 09 foundation.

A lightweight, synchronous, in-process publish/subscribe mechanism.
Business modules publish a DomainEvent describing something that already
happened; registered handlers (e.g. the notifications app) react to it by
creating side-effect rows (Notification, ...). This is deliberately
separate from the CES EventOutbox (apps.kernel.services.event_publisher) —
that system is the async, persisted, cross-module event bus; this one is
synchronous, in-memory, and scoped to in-process fan-out such as
notification handlers.

Public surface:
    from apps.kernel.events import DomainEvent, EventRegistry, publish
"""

from .base import DomainEvent
from .publisher import publish
from .registry import EventRegistry

__all__ = [
    "DomainEvent",
    "EventRegistry",
    "publish",
]
