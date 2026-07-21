"""
JobRegistry — in-process map of job_type -> handler callable.

Mirrors apps.kernel.events.registry.EventRegistry's shape, adapted for jobs:
exactly one handler per job_type (a job either has a handler or it doesn't —
unlike DomainEvent's fan-out to multiple listeners). Handlers register
themselves from apps.jobs.handlers.register_handlers(), called from
JobsConfig.ready().

Deliberately dependency-free: this module must never import from any
business app to avoid circular imports.
"""

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from apps.jobs.errors import JobsError

if TYPE_CHECKING:
    from apps.jobs.models import JobDefinition

logger = logging.getLogger(__name__)

JobHandler = Callable[["JobDefinition"], None]


class JobRegistry:
    """Central, in-memory registry of job_type -> handler."""

    _handlers: dict[str, JobHandler] = {}

    @classmethod
    def register(cls, job_type: str, handler: JobHandler) -> None:
        """Register `handler` for `job_type`. Idempotent: re-registering the
        same handler for the same job_type is a no-op."""
        existing = cls._handlers.get(job_type)
        if existing is not None and existing is not handler:
            raise JobsError(f"job_type {job_type!r} is already registered to a different handler")
        cls._handlers[job_type] = handler
        logger.debug("Registered handler %r for job_type %s", handler, job_type)

    @classmethod
    def get_handler(cls, job_type: str) -> JobHandler:
        """Return the handler registered for `job_type`, raising JobsError if none exists."""
        handler = cls._handlers.get(job_type)
        if handler is None:
            raise JobsError(f"no handler registered for job_type {job_type!r}")
        return handler

    @classmethod
    def is_registered(cls, job_type: str) -> bool:
        return job_type in cls._handlers

    @classmethod
    def clear(cls) -> None:
        """Remove all registrations. Intended for test isolation only."""
        cls._handlers.clear()
