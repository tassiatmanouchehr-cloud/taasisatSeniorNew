"""
EventRegistry — in-process map of event_type -> handler callables.

Deliberately dependency-free: this module must never import from any
business app (or from apps.notifications) to avoid circular imports.
Handlers register themselves elsewhere (typically from an AppConfig.ready()
hook) and are looked up here purely by event_type string.
"""

import logging
from typing import Callable

logger = logging.getLogger(__name__)

Handler = Callable[..., None]


class EventRegistry:
    """Central, in-memory registry of DomainEvent handlers."""

    _handlers: dict[str, list[Handler]] = {}

    @classmethod
    def register(cls, event_type: str, handler: Handler) -> None:
        """Register `handler` for `event_type`. Idempotent: registering the
        same handler for the same event_type more than once is a no-op."""
        handlers = cls._handlers.setdefault(event_type, [])
        if handler not in handlers:
            handlers.append(handler)
            logger.debug("Registered handler %r for event_type %s", handler, event_type)

    @classmethod
    def unregister(cls, event_type: str, handler: Handler) -> None:
        """Remove `handler` from `event_type`'s registration, if present."""
        handlers = cls._handlers.get(event_type)
        if handlers and handler in handlers:
            handlers.remove(handler)

    @classmethod
    def get_handlers(cls, event_type: str) -> list[Handler]:
        """Return a snapshot list of handlers registered for `event_type`."""
        return list(cls._handlers.get(event_type, []))

    @classmethod
    def clear(cls) -> None:
        """Remove all registrations. Intended for test isolation only."""
        cls._handlers.clear()
