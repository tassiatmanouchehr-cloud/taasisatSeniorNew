"""
Payment-deadline expiry job — Financial Core PR-A.
Objection-period auto-approve job — Financial Core PR-B.

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
OBJECTION_PERIOD_AUTO_APPROVE = "commission.objection_period.auto_approve"


def _expire_payment_deadline(job) -> None:
    """Raises on failure (uncaught) so JobService.execute_job() records it
    as a failed JobRun and reschedules via the standard backoff/dead-letter
    path — this function must not swallow exceptions itself."""
    from .services.deadline_service import PaymentDeadlineService

    payment_deadline_id = job.payload["payment_deadline_id"]
    PaymentDeadlineService.expire_due(deadline_id=payment_deadline_id)


def _auto_approve_objection_period(job) -> None:
    """Financial Core PR-B: the objection-period auto-approve job handler.
    ObjectionPeriodService.auto_approve_if_due() is itself the safety
    gate/idempotency guard — see that method's own docstring — so this
    handler body stays a thin, uncaught-exceptions-propagate wrapper,
    matching _expire_payment_deadline's own contract above."""
    from .services.objection_service import ObjectionPeriodService

    objection_period_id = job.payload["objection_period_id"]
    ObjectionPeriodService.auto_approve_if_due(objection_period_id=objection_period_id)


def register_handlers() -> None:
    """Idempotently register this app's job handlers."""
    JobRegistry.register(PAYMENT_DEADLINE_EXPIRE, _expire_payment_deadline)
    JobRegistry.register(OBJECTION_PERIOD_AUTO_APPROVE, _auto_approve_objection_period)
