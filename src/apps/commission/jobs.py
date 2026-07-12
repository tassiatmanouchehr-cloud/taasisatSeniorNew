"""
Payment-deadline expiry job — Financial Core PR-A.

Mirrors apps.payments.jobs's pattern exactly (a durable, apps.jobs-backed
handler rather than a lazy page-view check — Business Model Section 2:
"The expiry must be enforced by a real scheduled job, not only by a lazy
page view check"). JobService.enqueue() schedules this for exactly the
deadline's due timestamp (scheduled_for=deadline_at); the standard
run_due_jobs sweep (apps.jobs) picks it up once due.
"""

import logging

from apps.jobs.registry import JobRegistry

logger = logging.getLogger(__name__)

PAYMENT_DEADLINE_EXPIRE = "commission.payment_deadline.expire"


def _expire_payment_deadline(job) -> None:
    """Raises on failure (uncaught) so JobService.execute_job() records it
    as a failed JobRun and reschedules via the standard backoff/dead-letter
    path — this function must not swallow exceptions itself."""
    from .services.deadline_service import PaymentDeadlineService

    payment_deadline_id = job.payload["payment_deadline_id"]
    PaymentDeadlineService.expire_due(deadline_id=payment_deadline_id)


def register_handlers() -> None:
    """Idempotently register this app's job handlers."""
    JobRegistry.register(PAYMENT_DEADLINE_EXPIRE, _expire_payment_deadline)
