"""
run_due_jobs — the management-command job runner for the Module 20 foundation.

Selects due PENDING jobs (next_run_at <= now), claims them safely under
select_for_update(skip_locked=True) so concurrent invocations never double-run
a job, executes the registered handler, and records the outcome. Safe to run
repeatedly (e.g. from cron) — a run with nothing due is a no-op.

Usage:
    python manage.py run_due_jobs
    python manage.py run_due_jobs --limit=50
    python manage.py run_due_jobs --queue=default
    python manage.py run_due_jobs --dry-run
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.jobs.models import JobDefinition, JobStatus
from apps.jobs.services.job_service import JobService


class Command(BaseCommand):
    help = "Run due background jobs (Module 20 foundation runner)."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100, help="Maximum number of jobs to process (default: 100).")
        parser.add_argument("--queue", type=str, default=None, help="Only process jobs on this queue name.")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report how many jobs are due without claiming or executing them.",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        queue_name = options["queue"]
        dry_run = options["dry_run"]

        if dry_run:
            qs = JobDefinition.objects.filter(status=JobStatus.PENDING, next_run_at__lte=timezone.now())
            if queue_name:
                qs = qs.filter(queue_name=queue_name)
            due_count = qs.count()
            self.stdout.write(f"[dry-run] {due_count} job(s) due (limit={limit})")
            return

        locked_by = f"run_due_jobs:{timezone.now().isoformat()}"
        claimed = JobService.claim_due_jobs(limit=limit, queue_name=queue_name, locked_by=locked_by)

        succeeded = failed = dead_letter = 0
        for job in claimed:
            job = JobService.execute_job(job)
            if job.status == JobStatus.SUCCEEDED:
                succeeded += 1
            elif job.status == JobStatus.DEAD_LETTER:
                dead_letter += 1
            else:
                failed += 1

        self.stdout.write(
            f"Processed {len(claimed)} job(s): {succeeded} succeeded, {failed} failed (will retry), "
            f"{dead_letter} dead-lettered."
        )
