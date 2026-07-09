"""
Background jobs foundation — Module 20.

JobDefinition is the durable record of "what to run and when"; JobRun is an
append-only audit trail of each execution attempt. The retry/backoff shape
mirrors apps.kernel.models.event_outbox.EventOutbox (exponential backoff,
dead-letter after max_retries) but this is a distinct, general-purpose job
system — not the CES event outbox, and not read/written by it.

tenant_id is nullable: null means a global/system job (not scoped to any
single tenant). Non-null means the job is tenant-scoped and only concerns
that tenant's data.
"""

import uuid

from django.db import models
from django.utils import timezone


class JobStatus(models.TextChoices):
    """Background job processing states."""

    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"
    DEAD_LETTER = "dead_letter", "Dead Letter"


class JobDefinition(models.Model):
    """
    A single scheduled job instance — not a reusable template.

    Despite the name, each row is one concrete unit of work (a specific
    job_type + payload + idempotency_key), not a definition that spawns
    multiple runs. "Definition" here mirrors EventOutbox's terminology
    (the durable record of what to do), not a template/schedule concept —
    there is no separate "JobTemplate" this row is instantiated from.
    Re-running the same logical work is done by enqueuing a new instance
    (or reusing one via idempotency_key), not by re-triggering this row.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(null=True, blank=True, db_index=True, help_text="Null means a global/system job.")

    job_type = models.CharField(max_length=200, db_index=True, help_text="Registry key looked up to find the handler.")
    queue_name = models.CharField(max_length=100, default="default", db_index=True)
    payload = models.JSONField(default=dict, blank=True)

    idempotency_key = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Enqueuing with an existing (tenant_id, job_type, idempotency_key) reuses the existing job.",
    )

    status = models.CharField(max_length=20, choices=JobStatus.choices, default=JobStatus.PENDING, db_index=True)

    scheduled_for = models.DateTimeField(default=timezone.now, help_text="Earliest time this job may first run.")
    next_run_at = models.DateTimeField(default=timezone.now, db_index=True, help_text="Next time the runner should attempt this job.")

    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    last_error = models.TextField(blank=True)

    locked_at = models.DateTimeField(null=True, blank=True)
    locked_by = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jobs_job_definition"
        verbose_name = "Job Definition"
        verbose_name_plural = "Job Definitions"
        ordering = ["next_run_at"]
        indexes = [
            models.Index(fields=["status", "next_run_at"], name="idx_job_due"),
            models.Index(fields=["tenant_id", "job_type", "created_at"], name="idx_job_tenant_type"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "job_type", "idempotency_key"],
                name="uq_job_tenant_type_idempotency",
            ),
        ]

    def __str__(self):
        return f"{self.job_type} [{self.status}] ({self.id})"

    def mark_running(self, *, locked_by: str):
        self.status = JobStatus.RUNNING
        self.locked_at = timezone.now()
        self.locked_by = locked_by
        self.save(update_fields=["status", "locked_at", "locked_by", "updated_at"])

    def mark_succeeded(self):
        self.status = JobStatus.SUCCEEDED
        self.locked_at = None
        self.locked_by = ""
        self.save(update_fields=["status", "locked_at", "locked_by", "updated_at"])

    def mark_failed(self, error: str):
        """Mark this attempt as failed; schedule retry or dead-letter."""
        self.retry_count += 1
        self.last_error = error[:2000]
        self.locked_at = None
        self.locked_by = ""
        if self.retry_count >= self.max_retries:
            self.status = JobStatus.DEAD_LETTER
        else:
            self.status = JobStatus.PENDING
            backoff_seconds = 2**self.retry_count
            self.next_run_at = timezone.now() + timezone.timedelta(seconds=backoff_seconds)
        self.save(
            update_fields=["status", "retry_count", "last_error", "next_run_at", "locked_at", "locked_by", "updated_at"]
        )


class JobRun(models.Model):
    """Append-only audit trail: one row per execution attempt of a JobDefinition."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(JobDefinition, on_delete=models.CASCADE, related_name="runs")
    attempt_number = models.IntegerField()
    status = models.CharField(max_length=20, choices=JobStatus.choices, db_index=True)

    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = "jobs_job_run"
        verbose_name = "Job Run"
        verbose_name_plural = "Job Runs"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["job", "started_at"], name="idx_job_run_job_started"),
        ]

    def __str__(self):
        return f"{self.job_id} attempt {self.attempt_number} [{self.status}]"

    def mark_finished(self, *, status: str, error_message: str = ""):
        self.status = status
        self.finished_at = timezone.now()
        self.error_message = error_message[:2000]
        self.save(update_fields=["status", "finished_at", "error_message"])
