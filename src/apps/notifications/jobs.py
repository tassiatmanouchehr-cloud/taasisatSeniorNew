"""
apps.jobs integration — Module 21 foundation.

Registers job_type "notifications.dispatch_pending" in apps.jobs'
JobRegistry. This is the one deliberate exception to the usual dependency
direction (apps.notifications, a lower-numbered app, importing
apps.jobs, a higher one) — apps.jobs is reusable execution infrastructure
that business apps plug into, the same role apps.kernel.events plays for
domain events. apps.jobs never imports apps.notifications; the coupling
only exists once apps.notifications chooses to wire itself in here, from
NotificationsConfig.ready().

The handler itself does no dispatch logic — it delegates entirely to
NotificationDispatchService.dispatch_pending(), the same method the
dispatch_notifications management command calls directly.
"""

from apps.jobs.registry import JobRegistry

DISPATCH_PENDING = "notifications.dispatch_pending"


def _dispatch_pending_job(job) -> None:
    from apps.notifications.services.dispatch_service import NotificationDispatchService

    limit = job.payload.get("limit", 100)
    NotificationDispatchService.dispatch_pending(tenant_id=job.tenant_id, limit=limit)


def register_job_handlers() -> None:
    JobRegistry.register(DISPATCH_PENDING, _dispatch_pending_job)
