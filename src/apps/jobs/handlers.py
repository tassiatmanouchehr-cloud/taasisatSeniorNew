"""
Demo/no-op job handlers — Module 20 foundation only.

These exist solely to exercise the job execution infrastructure (success,
failure, retry, dead-letter) end to end. They have no business side effects
and must never be pointed at real domain state. Real handlers (outbox
processing, payment-intent expiry, wallet reconciliation, etc.) are
explicitly deferred to future modules.
"""

import logging

from apps.jobs.errors import JobsError
from apps.jobs.registry import JobRegistry

logger = logging.getLogger(__name__)

DEMO_NO_OP = "demo.no_op"
DEMO_ALWAYS_FAIL = "demo.always_fail"
DEMO_ECHO = "demo.echo"


def _no_op(job) -> None:
    """Always succeeds; does nothing."""


def _always_fail(job) -> None:
    """Always raises; used to exercise retry/dead-letter behavior in tests."""
    raise JobsError(f"demo.always_fail: intentional failure for job {job.id}")


def _echo(job) -> None:
    """Always succeeds; logs its payload so tests can assert it ran."""
    logger.info("demo.echo job %s payload=%r", job.id, job.payload)


def register_handlers() -> None:
    JobRegistry.register(DEMO_NO_OP, _no_op)
    JobRegistry.register(DEMO_ALWAYS_FAIL, _always_fail)
    JobRegistry.register(DEMO_ECHO, _echo)
