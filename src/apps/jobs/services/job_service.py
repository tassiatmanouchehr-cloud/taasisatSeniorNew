"""
JobService — Module 20 foundation.

Two responsibilities, kept together because they share the same model:
  - enqueue(): idempotent creation of a JobDefinition.
  - claim_due_jobs()/execute_job(): the selection + execution logic used by
    the run_due_jobs management command (and directly by tests).

Locking: claim_due_jobs() uses select_for_update(skip_locked=True) inside a
transaction so that two concurrent runners never execute the same job twice.
"""

import logging

from django.db import transaction
from django.utils import timezone

from apps.jobs.errors import JobsError
from apps.jobs.registry import JobRegistry

logger = logging.getLogger(__name__)


class JobService:
    """Creates and executes JobDefinition rows."""

    @classmethod
    @transaction.atomic
    def enqueue(
        cls,
        *,
        job_type: str,
        idempotency_key: str,
        tenant_id=None,
        payload: dict | None = None,
        queue_name: str = "default",
        scheduled_for=None,
        max_retries: int = 3,
    ):
        """Create a JobDefinition, or return the existing one for the same
        (tenant_id, job_type, idempotency_key) if it already exists."""
        from apps.jobs.models import JobDefinition

        if not JobRegistry.is_registered(job_type):
            raise JobsError(f"cannot enqueue unknown job_type {job_type!r} — no handler registered")

        scheduled_for = scheduled_for or timezone.now()
        job, created = JobDefinition.objects.get_or_create(
            tenant_id=tenant_id,
            job_type=job_type,
            idempotency_key=idempotency_key,
            defaults={
                "payload": payload or {},
                "queue_name": queue_name,
                "scheduled_for": scheduled_for,
                "next_run_at": scheduled_for,
                "max_retries": max_retries,
            },
        )
        if created:
            logger.debug("Enqueued job %s (job_type=%s)", job.id, job_type)
        return job

    @classmethod
    def claim_due_jobs(cls, *, limit: int, queue_name: str | None = None, locked_by: str):
        """Atomically claim up to `limit` due PENDING jobs, marking them RUNNING.
        Returns the list of claimed JobDefinition instances."""
        from apps.jobs.models import JobDefinition, JobStatus

        claimed = []
        with transaction.atomic():
            qs = JobDefinition.objects.select_for_update(skip_locked=True).filter(
                status=JobStatus.PENDING,
                next_run_at__lte=timezone.now(),
            )
            if queue_name:
                qs = qs.filter(queue_name=queue_name)
            for job in qs.order_by("next_run_at")[:limit]:
                job.mark_running(locked_by=locked_by)
                claimed.append(job)
        return claimed

    @classmethod
    def execute_job(cls, job):
        """Run the registered handler for `job`, recording a JobRun and
        updating the job's status. Never raises — failures are captured and
        recorded on the job/run instead."""
        from apps.jobs.models import JobRun, JobStatus

        run = JobRun.objects.create(
            job=job,
            attempt_number=job.retry_count + 1,
            status=JobStatus.RUNNING,
        )
        try:
            handler = JobRegistry.get_handler(job.job_type)
        except JobsError as exc:
            job.mark_failed(str(exc))
            run.mark_finished(status=JobStatus.FAILED, error_message=str(exc))
            return job

        try:
            handler(job)
        except Exception as exc:  # noqa: BLE001 — handler failures are data, not crashes
            job.mark_failed(str(exc))
            run.mark_finished(status=job.status, error_message=str(exc))
        else:
            job.mark_succeeded()
            run.mark_finished(status=JobStatus.SUCCEEDED)
        return job
