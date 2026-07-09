"""
Tests for the background jobs foundation — Module 20.

Covers: job creation, due job selection, successful/failed execution, retry
scheduling, max-retry exhaustion, idempotency, tenant-scoped vs global jobs,
unknown handler rejection, the run_due_jobs management command (including
dry-run), registry behavior, and concurrent-claim (locking) behavior.
"""

import io
import uuid

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.jobs.errors import JobsError
from apps.jobs.handlers import DEMO_ALWAYS_FAIL, DEMO_ECHO, DEMO_NO_OP
from apps.jobs.models import JobDefinition, JobRun, JobStatus
from apps.jobs.registry import JobRegistry
from apps.jobs.services.job_service import JobService


class JobCreationTest(TestCase):
    def test_enqueue_creates_a_pending_job(self):
        job = JobService.enqueue(job_type=DEMO_NO_OP, idempotency_key="k1")
        self.assertEqual(job.status, JobStatus.PENDING)
        self.assertEqual(job.retry_count, 0)
        self.assertEqual(job.queue_name, "default")
        self.assertIsNone(job.tenant_id)

    def test_enqueue_rejects_unknown_job_type(self):
        with self.assertRaises(JobsError):
            JobService.enqueue(job_type="no.such.handler", idempotency_key="k1")


class IdempotencyTest(TestCase):
    def test_enqueue_twice_with_same_key_returns_same_job(self):
        job1 = JobService.enqueue(job_type=DEMO_NO_OP, idempotency_key="same-key")
        job2 = JobService.enqueue(job_type=DEMO_NO_OP, idempotency_key="same-key")
        self.assertEqual(job1.id, job2.id)
        self.assertEqual(JobDefinition.objects.filter(job_type=DEMO_NO_OP, idempotency_key="same-key").count(), 1)

    def test_enqueue_with_different_keys_creates_distinct_jobs(self):
        job1 = JobService.enqueue(job_type=DEMO_NO_OP, idempotency_key="key-a")
        job2 = JobService.enqueue(job_type=DEMO_NO_OP, idempotency_key="key-b")
        self.assertNotEqual(job1.id, job2.id)

    def test_same_key_different_tenants_are_distinct_jobs(self):
        tenant_a, tenant_b = uuid.uuid4(), uuid.uuid4()
        job1 = JobService.enqueue(job_type=DEMO_NO_OP, idempotency_key="shared-key", tenant_id=tenant_a)
        job2 = JobService.enqueue(job_type=DEMO_NO_OP, idempotency_key="shared-key", tenant_id=tenant_b)
        self.assertNotEqual(job1.id, job2.id)


class TenantScopingTest(TestCase):
    def test_tenant_scoped_job_carries_tenant_id(self):
        tenant_id = uuid.uuid4()
        job = JobService.enqueue(job_type=DEMO_NO_OP, idempotency_key="t1", tenant_id=tenant_id)
        self.assertEqual(job.tenant_id, tenant_id)

    def test_global_job_has_null_tenant_id(self):
        job = JobService.enqueue(job_type=DEMO_NO_OP, idempotency_key="g1", tenant_id=None)
        self.assertIsNone(job.tenant_id)

    def test_claim_due_jobs_returns_both_tenant_and_global_jobs(self):
        tenant_id = uuid.uuid4()
        JobService.enqueue(job_type=DEMO_NO_OP, idempotency_key="t2", tenant_id=tenant_id)
        JobService.enqueue(job_type=DEMO_NO_OP, idempotency_key="g2", tenant_id=None)
        claimed = JobService.claim_due_jobs(limit=10, locked_by="test")
        self.assertEqual(len(claimed), 2)


class DueJobSelectionTest(TestCase):
    def test_claim_due_jobs_only_returns_pending_and_due(self):
        due = JobService.enqueue(job_type=DEMO_NO_OP, idempotency_key="due")
        future = JobService.enqueue(
            job_type=DEMO_NO_OP, idempotency_key="future", scheduled_for=timezone.now() + timezone.timedelta(hours=1)
        )
        succeeded = JobService.enqueue(job_type=DEMO_NO_OP, idempotency_key="already-done")
        succeeded.mark_succeeded()

        claimed = JobService.claim_due_jobs(limit=10, locked_by="test")
        claimed_ids = {job.id for job in claimed}

        self.assertIn(due.id, claimed_ids)
        self.assertNotIn(future.id, claimed_ids)
        self.assertNotIn(succeeded.id, claimed_ids)

    def test_claim_due_jobs_respects_queue_name(self):
        JobService.enqueue(job_type=DEMO_NO_OP, idempotency_key="q1", queue_name="alerts")
        JobService.enqueue(job_type=DEMO_NO_OP, idempotency_key="q2", queue_name="default")

        claimed = JobService.claim_due_jobs(limit=10, queue_name="alerts", locked_by="test")
        self.assertEqual(len(claimed), 1)
        self.assertEqual(claimed[0].queue_name, "alerts")

    def test_claim_due_jobs_respects_limit(self):
        for i in range(5):
            JobService.enqueue(job_type=DEMO_NO_OP, idempotency_key=f"lim-{i}")
        claimed = JobService.claim_due_jobs(limit=2, locked_by="test")
        self.assertEqual(len(claimed), 2)

    def test_claimed_jobs_transition_to_running(self):
        job = JobService.enqueue(job_type=DEMO_NO_OP, idempotency_key="running")
        claimed = JobService.claim_due_jobs(limit=10, locked_by="test")
        self.assertEqual(claimed[0].status, JobStatus.RUNNING)
        job.refresh_from_db()
        self.assertEqual(job.status, JobStatus.RUNNING)


class SuccessfulExecutionTest(TestCase):
    def test_execute_job_marks_succeeded(self):
        job = JobService.enqueue(job_type=DEMO_NO_OP, idempotency_key="ok")
        job = JobService.execute_job(job)
        self.assertEqual(job.status, JobStatus.SUCCEEDED)
        self.assertEqual(job.retry_count, 0)

    def test_execute_job_creates_job_run_record(self):
        job = JobService.enqueue(job_type=DEMO_ECHO, idempotency_key="echo1", payload={"x": 1})
        JobService.execute_job(job)
        runs = JobRun.objects.filter(job=job)
        self.assertEqual(runs.count(), 1)
        self.assertEqual(runs.first().status, JobStatus.SUCCEEDED)
        self.assertEqual(runs.first().attempt_number, 1)
        self.assertIsNotNone(runs.first().finished_at)


class FailedExecutionTest(TestCase):
    def test_execute_job_marks_failed_and_records_error(self):
        job = JobService.enqueue(job_type=DEMO_ALWAYS_FAIL, idempotency_key="fail1", max_retries=5)
        job = JobService.execute_job(job)
        self.assertEqual(job.status, JobStatus.PENDING)  # rescheduled for retry
        self.assertEqual(job.retry_count, 1)
        self.assertIn("intentional failure", job.last_error)

    def test_failed_execution_creates_failed_job_run(self):
        job = JobService.enqueue(job_type=DEMO_ALWAYS_FAIL, idempotency_key="fail2", max_retries=5)
        JobService.execute_job(job)
        run = JobRun.objects.get(job=job)
        self.assertEqual(run.status, JobStatus.PENDING)  # mirrors job.status at time of failure
        self.assertIn("intentional failure", run.error_message)


class RetrySchedulingTest(TestCase):
    def test_failure_schedules_next_run_in_the_future(self):
        job = JobService.enqueue(job_type=DEMO_ALWAYS_FAIL, idempotency_key="retry1", max_retries=5)
        before = timezone.now()
        job = JobService.execute_job(job)
        self.assertGreater(job.next_run_at, before)

    def test_backoff_grows_with_each_retry(self):
        job = JobService.enqueue(job_type=DEMO_ALWAYS_FAIL, idempotency_key="retry2", max_retries=5)
        job = JobService.execute_job(job)
        first_wait = job.next_run_at - timezone.now()

        job.status = JobStatus.PENDING  # simulate the wait having elapsed
        job.next_run_at = timezone.now()
        job.save(update_fields=["status", "next_run_at"])
        job = JobService.execute_job(job)
        second_wait = job.next_run_at - timezone.now()

        self.assertGreater(second_wait, first_wait)


class MaxRetryExhaustionTest(TestCase):
    def test_job_is_dead_lettered_after_max_retries(self):
        job = JobService.enqueue(job_type=DEMO_ALWAYS_FAIL, idempotency_key="exhaust", max_retries=2)
        job.next_run_at = timezone.now()
        job.save(update_fields=["next_run_at"])

        job = JobService.execute_job(job)
        self.assertEqual(job.status, JobStatus.PENDING)
        self.assertEqual(job.retry_count, 1)

        job = JobService.execute_job(job)
        self.assertEqual(job.status, JobStatus.DEAD_LETTER)
        self.assertEqual(job.retry_count, 2)

    def test_dead_lettered_job_is_never_selected_again(self):
        job = JobService.enqueue(job_type=DEMO_ALWAYS_FAIL, idempotency_key="exhaust2", max_retries=1)
        JobService.execute_job(job)
        job.refresh_from_db()
        self.assertEqual(job.status, JobStatus.DEAD_LETTER)

        claimed = JobService.claim_due_jobs(limit=10, locked_by="test")
        self.assertNotIn(job.id, {j.id for j in claimed})


class UnknownHandlerRejectionTest(TestCase):
    def test_enqueue_rejects_unregistered_job_type(self):
        with self.assertRaises(JobsError):
            JobService.enqueue(job_type="totally.unknown", idempotency_key="u1")

    def test_execute_job_fails_gracefully_if_handler_vanishes(self):
        job = JobService.enqueue(job_type=DEMO_NO_OP, idempotency_key="u2", max_retries=5)
        original_handlers = dict(JobRegistry._handlers)
        try:
            del JobRegistry._handlers[DEMO_NO_OP]
            job = JobService.execute_job(job)
            self.assertIn(job.status, (JobStatus.PENDING, JobStatus.DEAD_LETTER))
            self.assertIn("no handler registered", job.last_error)
        finally:
            JobRegistry._handlers.update(original_handlers)


class RegistryBehaviorTest(TestCase):
    def test_demo_handlers_are_registered_on_app_ready(self):
        self.assertTrue(JobRegistry.is_registered(DEMO_NO_OP))
        self.assertTrue(JobRegistry.is_registered(DEMO_ALWAYS_FAIL))
        self.assertTrue(JobRegistry.is_registered(DEMO_ECHO))

    def test_get_handler_raises_for_unknown_type(self):
        with self.assertRaises(JobsError):
            JobRegistry.get_handler("does.not.exist")

    def test_register_same_handler_twice_is_idempotent(self):
        handler = JobRegistry.get_handler(DEMO_NO_OP)
        JobRegistry.register(DEMO_NO_OP, handler)  # should not raise
        self.assertIs(JobRegistry.get_handler(DEMO_NO_OP), handler)

    def test_register_conflicting_handler_raises(self):
        def other_handler(job):
            pass

        with self.assertRaises(JobsError):
            JobRegistry.register(DEMO_NO_OP, other_handler)


class NoBusinessSideEffectsTest(TestCase):
    """The demo handlers must not touch any real domain model."""

    def test_demo_handlers_do_not_import_business_apps(self):
        import apps.jobs.handlers as handlers_module

        source = io.open(handlers_module.__file__, encoding="utf-8").read()
        for forbidden in ("apps.wallet", "apps.payments", "apps.finance", "apps.notifications", "apps.orders"):
            self.assertNotIn(forbidden, source)

    def test_running_demo_jobs_creates_no_rows_outside_jobs_app(self):
        from apps.wallet.models import Wallet

        before = Wallet.objects.count()
        job = JobService.enqueue(job_type=DEMO_ECHO, idempotency_key="side-effect", payload={"a": 1})
        JobService.execute_job(job)
        after = Wallet.objects.count()
        self.assertEqual(before, after)


class ManagementCommandTest(TestCase):
    def test_run_due_jobs_processes_pending_jobs(self):
        JobService.enqueue(job_type=DEMO_NO_OP, idempotency_key="cmd1")
        out = io.StringIO()
        call_command("run_due_jobs", stdout=out)
        job = JobDefinition.objects.get(idempotency_key="cmd1")
        self.assertEqual(job.status, JobStatus.SUCCEEDED)
        self.assertIn("Processed 1 job(s)", out.getvalue())

    def test_run_due_jobs_respects_limit(self):
        for i in range(3):
            JobService.enqueue(job_type=DEMO_NO_OP, idempotency_key=f"cmd-limit-{i}")
        out = io.StringIO()
        call_command("run_due_jobs", limit=1, stdout=out)
        self.assertEqual(JobDefinition.objects.filter(status=JobStatus.SUCCEEDED).count(), 1)

    def test_run_due_jobs_is_safe_to_run_repeatedly(self):
        JobService.enqueue(job_type=DEMO_NO_OP, idempotency_key="cmd-repeat")
        out = io.StringIO()
        call_command("run_due_jobs", stdout=out)
        call_command("run_due_jobs", stdout=out)  # second run: nothing due, should not error
        self.assertEqual(JobDefinition.objects.filter(status=JobStatus.SUCCEEDED).count(), 1)

    def test_run_due_jobs_handles_failures_without_crashing(self):
        JobService.enqueue(job_type=DEMO_ALWAYS_FAIL, idempotency_key="cmd-fail", max_retries=5)
        out = io.StringIO()
        call_command("run_due_jobs", stdout=out)
        job = JobDefinition.objects.get(idempotency_key="cmd-fail")
        self.assertEqual(job.status, JobStatus.PENDING)
        self.assertEqual(job.retry_count, 1)


class DryRunTest(TestCase):
    def test_dry_run_reports_due_count_without_executing(self):
        JobService.enqueue(job_type=DEMO_NO_OP, idempotency_key="dry1")
        out = io.StringIO()
        call_command("run_due_jobs", **{"dry_run": True}, stdout=out)
        job = JobDefinition.objects.get(idempotency_key="dry1")
        self.assertEqual(job.status, JobStatus.PENDING)
        self.assertIn("1 job(s) due", out.getvalue())

    def test_dry_run_does_not_create_job_runs(self):
        JobService.enqueue(job_type=DEMO_NO_OP, idempotency_key="dry2")
        call_command("run_due_jobs", **{"dry_run": True}, stdout=io.StringIO())
        self.assertEqual(JobRun.objects.count(), 0)


class ConcurrencyLockingTest(TestCase):
    """claim_due_jobs() moves a job out of PENDING, so a second claim (even after
    the first transaction commits) never picks up the same row — the
    select_for_update(skip_locked=True) + status transition together prevent
    double-claiming across concurrent runners."""

    def test_a_claimed_job_is_not_claimable_again(self):
        JobService.enqueue(job_type=DEMO_NO_OP, idempotency_key="lock1")

        first_claim = JobService.claim_due_jobs(limit=10, locked_by="runner-a")
        second_claim = JobService.claim_due_jobs(limit=10, locked_by="runner-b")

        self.assertEqual(len(first_claim), 1)
        self.assertEqual(len(second_claim), 0)
