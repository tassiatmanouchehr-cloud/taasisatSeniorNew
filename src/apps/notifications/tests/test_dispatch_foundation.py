"""
Tests for the notification dispatch foundation — Module 21.

Covers: pending selection, successful/failed dispatch, retry scheduling,
max-retry/dead-letter, provider registry, unsupported channel, idempotent
dispatch, apps.jobs handler integration, management command behavior
(including dry-run), no direct sending from DomainEvent handlers, tenant
isolation, fake provider success/failure, and delivery attempt audit trail.
"""

import io
import uuid

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.jobs.registry import JobRegistry
from apps.kernel.events.base import ORDER_CREATED, DomainEvent
from apps.kernel.events.handlers import handle_order_created
from apps.kernel.models import Tenant
from apps.notifications.errors import NotificationsError
from apps.notifications.jobs import DISPATCH_PENDING
from apps.notifications.models import (
    Notification,
    NotificationChannel,
    NotificationDeliveryAttempt,
    NotificationStatus,
)
from apps.notifications.providers.fake import FakeSmsProvider
from apps.notifications.providers.registry import NotificationProviderRegistry
from apps.notifications.services.dispatch_service import NotificationDispatchService


def _make_notification(tenant, *, channel=NotificationChannel.SMS, **kwargs):
    return Notification.objects.create(
        tenant=tenant, recipient=uuid.uuid4(), channel=channel,
        subject="Test", body="Test body", **kwargs,
    )


class PendingSelectionTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"t-{uuid.uuid4().hex[:8]}", name="T")

    def test_dispatch_pending_only_selects_due_pending_notifications(self):
        due = _make_notification(self.tenant)
        future = _make_notification(self.tenant, next_attempt_at=timezone.now() + timezone.timedelta(hours=1))
        already_sent = _make_notification(self.tenant, status=NotificationStatus.SENT)

        processed = NotificationDispatchService.dispatch_pending(limit=10)
        processed_ids = {n.id for n in processed}

        self.assertIn(due.id, processed_ids)
        self.assertNotIn(future.id, processed_ids)
        self.assertNotIn(already_sent.id, processed_ids)

    def test_dispatch_pending_respects_limit(self):
        for _ in range(5):
            _make_notification(self.tenant)
        processed = NotificationDispatchService.dispatch_pending(limit=2)
        self.assertEqual(len(processed), 2)


class SuccessfulDispatchTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"t-{uuid.uuid4().hex[:8]}", name="T")

    def test_dispatch_marks_notification_sent(self):
        notification = _make_notification(self.tenant, channel=NotificationChannel.SMS)
        NotificationDispatchService.dispatch_pending(limit=10)
        notification.refresh_from_db()
        self.assertEqual(notification.status, NotificationStatus.SENT)
        self.assertIsNotNone(notification.sent_at)

    def test_dispatch_creates_delivery_attempt_record(self):
        notification = _make_notification(self.tenant, channel=NotificationChannel.EMAIL)
        NotificationDispatchService.dispatch_pending(limit=10)
        attempts = NotificationDeliveryAttempt.objects.filter(notification=notification)
        self.assertEqual(attempts.count(), 1)
        attempt = attempts.first()
        self.assertEqual(attempt.status, NotificationStatus.SENT)
        self.assertEqual(attempt.attempt_number, 1)
        self.assertTrue(attempt.provider_name)


class FailedDispatchTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"t-{uuid.uuid4().hex[:8]}", name="T")
        self.original_provider = NotificationProviderRegistry._providers.get(NotificationChannel.SMS)
        NotificationProviderRegistry.register(NotificationChannel.SMS, FakeSmsProvider(always_fail=True))

    def tearDown(self):
        NotificationProviderRegistry.register(NotificationChannel.SMS, self.original_provider)

    def test_dispatch_marks_notification_failed_and_records_reason(self):
        notification = _make_notification(self.tenant, channel=NotificationChannel.SMS, max_retries=5)
        NotificationDispatchService.dispatch_pending(limit=10)
        notification.refresh_from_db()
        self.assertEqual(notification.status, NotificationStatus.PENDING)  # rescheduled
        self.assertEqual(notification.retry_count, 1)
        self.assertIn("simulated delivery failure", notification.failure_reason)

    def test_failed_dispatch_creates_failed_attempt_record(self):
        notification = _make_notification(self.tenant, channel=NotificationChannel.SMS, max_retries=5)
        NotificationDispatchService.dispatch_pending(limit=10)
        attempt = NotificationDeliveryAttempt.objects.get(notification=notification)
        self.assertEqual(attempt.status, NotificationStatus.PENDING)
        self.assertIn("simulated delivery failure", attempt.error_message)


class RetrySchedulingTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"t-{uuid.uuid4().hex[:8]}", name="T")
        self.original_provider = NotificationProviderRegistry._providers.get(NotificationChannel.SMS)
        NotificationProviderRegistry.register(NotificationChannel.SMS, FakeSmsProvider(always_fail=True))

    def tearDown(self):
        NotificationProviderRegistry.register(NotificationChannel.SMS, self.original_provider)

    def test_failure_schedules_next_attempt_in_the_future(self):
        notification = _make_notification(self.tenant, channel=NotificationChannel.SMS, max_retries=5)
        before = timezone.now()
        NotificationDispatchService.dispatch_pending(limit=10)
        notification.refresh_from_db()
        self.assertGreater(notification.next_attempt_at, before)


class MaxRetryDeadLetterTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"t-{uuid.uuid4().hex[:8]}", name="T")
        self.original_provider = NotificationProviderRegistry._providers.get(NotificationChannel.SMS)
        NotificationProviderRegistry.register(NotificationChannel.SMS, FakeSmsProvider(always_fail=True))

    def tearDown(self):
        NotificationProviderRegistry.register(NotificationChannel.SMS, self.original_provider)

    def test_dead_lettered_after_max_retries(self):
        notification = _make_notification(self.tenant, channel=NotificationChannel.SMS, max_retries=2)

        NotificationDispatchService.dispatch_pending(limit=10)
        notification.refresh_from_db()
        self.assertEqual(notification.status, NotificationStatus.PENDING)
        self.assertEqual(notification.retry_count, 1)

        notification.next_attempt_at = timezone.now()
        notification.save(update_fields=["next_attempt_at"])
        NotificationDispatchService.dispatch_pending(limit=10)
        notification.refresh_from_db()
        self.assertEqual(notification.status, NotificationStatus.DEAD_LETTER)
        self.assertEqual(notification.retry_count, 2)

    def test_dead_lettered_notification_is_never_selected_again(self):
        notification = _make_notification(self.tenant, channel=NotificationChannel.SMS, max_retries=1)
        NotificationDispatchService.dispatch_pending(limit=10)
        notification.refresh_from_db()
        self.assertEqual(notification.status, NotificationStatus.DEAD_LETTER)

        processed = NotificationDispatchService.dispatch_pending(limit=10)
        self.assertNotIn(notification.id, {n.id for n in processed})


class ProviderRegistryTest(TestCase):
    def test_default_channels_have_registered_providers(self):
        for channel in (NotificationChannel.SMS, NotificationChannel.EMAIL, NotificationChannel.PUSH, NotificationChannel.IN_APP):
            self.assertTrue(NotificationProviderRegistry.is_registered(channel))

    def test_get_provider_raises_for_unknown_channel(self):
        with self.assertRaises(NotificationsError):
            NotificationProviderRegistry.get_provider("CARRIER_PIGEON")

    def test_register_overrides_existing_provider(self):
        original = NotificationProviderRegistry.get_provider(NotificationChannel.SMS)
        try:
            replacement = FakeSmsProvider()
            NotificationProviderRegistry.register(NotificationChannel.SMS, replacement)
            self.assertIs(NotificationProviderRegistry.get_provider(NotificationChannel.SMS), replacement)
        finally:
            NotificationProviderRegistry.register(NotificationChannel.SMS, original)


class UnsupportedChannelTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"t-{uuid.uuid4().hex[:8]}", name="T")

    def test_dispatch_fails_gracefully_when_no_provider_registered(self):
        notification = _make_notification(self.tenant, channel=NotificationChannel.PUSH, max_retries=5)
        original = NotificationProviderRegistry._providers.pop(NotificationChannel.PUSH, None)
        try:
            NotificationDispatchService.dispatch_pending(limit=10)
            notification.refresh_from_db()
            self.assertIn(notification.status, (NotificationStatus.PENDING, NotificationStatus.DEAD_LETTER))
            self.assertIn("no provider registered", notification.failure_reason)
        finally:
            if original is not None:
                NotificationProviderRegistry.register(NotificationChannel.PUSH, original)


class IdempotentDispatchTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"t-{uuid.uuid4().hex[:8]}", name="T")

    def test_dispatching_twice_does_not_double_send(self):
        notification = _make_notification(self.tenant)
        NotificationDispatchService.dispatch_pending(limit=10)
        NotificationDispatchService.dispatch_pending(limit=10)  # second run: nothing due

        notification.refresh_from_db()
        self.assertEqual(notification.status, NotificationStatus.SENT)
        self.assertEqual(NotificationDeliveryAttempt.objects.filter(notification=notification).count(), 1)

    def test_already_sent_notification_is_not_reselected(self):
        notification = _make_notification(self.tenant, status=NotificationStatus.SENT)
        processed = NotificationDispatchService.dispatch_pending(limit=10)
        self.assertNotIn(notification.id, {n.id for n in processed})


class JobHandlerIntegrationTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"t-{uuid.uuid4().hex[:8]}", name="T")

    def test_dispatch_pending_job_type_is_registered(self):
        self.assertTrue(JobRegistry.is_registered(DISPATCH_PENDING))

    def test_running_the_job_dispatches_pending_notifications(self):
        from apps.jobs.services.job_service import JobService

        notification = _make_notification(self.tenant)
        job = JobService.enqueue(job_type=DISPATCH_PENDING, idempotency_key="dispatch-test-1")
        JobService.execute_job(job)

        notification.refresh_from_db()
        self.assertEqual(notification.status, NotificationStatus.SENT)

    def test_job_respects_tenant_scoping(self):
        from apps.jobs.services.job_service import JobService

        other_tenant = Tenant.objects.create(slug=f"t-other-{uuid.uuid4().hex[:8]}", name="Other")
        mine = _make_notification(self.tenant)
        other = _make_notification(other_tenant)

        job = JobService.enqueue(job_type=DISPATCH_PENDING, idempotency_key="dispatch-test-2", tenant_id=self.tenant.id)
        JobService.execute_job(job)

        mine.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(mine.status, NotificationStatus.SENT)
        self.assertEqual(other.status, NotificationStatus.PENDING)


class ManagementCommandTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"t-{uuid.uuid4().hex[:8]}", name="T")

    def test_command_dispatches_pending_notifications(self):
        notification = _make_notification(self.tenant)
        out = io.StringIO()
        call_command("dispatch_notifications", stdout=out)
        notification.refresh_from_db()
        self.assertEqual(notification.status, NotificationStatus.SENT)
        self.assertIn("Processed 1 notification(s)", out.getvalue())

    def test_command_respects_limit(self):
        for _ in range(3):
            _make_notification(self.tenant)
        out = io.StringIO()
        call_command("dispatch_notifications", limit=1, stdout=out)
        self.assertEqual(Notification.objects.filter(status=NotificationStatus.SENT).count(), 1)

    def test_command_is_safe_to_run_repeatedly(self):
        notification = _make_notification(self.tenant)
        out = io.StringIO()
        call_command("dispatch_notifications", stdout=out)
        call_command("dispatch_notifications", stdout=out)
        self.assertEqual(Notification.objects.filter(status=NotificationStatus.SENT).count(), 1)

    def test_command_respects_tenant_id_filter(self):
        other_tenant = Tenant.objects.create(slug=f"t-other-{uuid.uuid4().hex[:8]}", name="Other")
        mine = _make_notification(self.tenant)
        other = _make_notification(other_tenant)

        call_command("dispatch_notifications", **{"tenant_id": str(self.tenant.id)}, stdout=io.StringIO())

        mine.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(mine.status, NotificationStatus.SENT)
        self.assertEqual(other.status, NotificationStatus.PENDING)


class DryRunTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"t-{uuid.uuid4().hex[:8]}", name="T")

    def test_dry_run_reports_due_count_without_dispatching(self):
        notification = _make_notification(self.tenant)
        out = io.StringIO()
        call_command("dispatch_notifications", **{"dry_run": True}, stdout=out)
        notification.refresh_from_db()
        self.assertEqual(notification.status, NotificationStatus.PENDING)
        self.assertIn("1 notification(s) due", out.getvalue())

    def test_dry_run_creates_no_delivery_attempts(self):
        _make_notification(self.tenant)
        call_command("dispatch_notifications", **{"dry_run": True}, stdout=io.StringIO())
        self.assertEqual(NotificationDeliveryAttempt.objects.count(), 0)


class NoDirectSendingFromDomainEventHandlersTest(TestCase):
    """DomainEvent handlers must only create PENDING rows — never dispatch."""

    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"t-{uuid.uuid4().hex[:8]}", name="T")

    def test_handle_order_created_leaves_notification_pending(self):
        event = DomainEvent(
            event_type=ORDER_CREATED, tenant_id=self.tenant.id,
            aggregate_type="Order", aggregate_id=uuid.uuid4(),
            payload={"recipient_id": str(uuid.uuid4())},
        )
        handle_order_created(event)

        notification = Notification.objects.get(tenant=self.tenant)
        self.assertEqual(notification.status, NotificationStatus.PENDING)
        self.assertEqual(NotificationDeliveryAttempt.objects.filter(notification=notification).count(), 0)

    def test_handlers_module_does_not_import_dispatch_service(self):
        import apps.kernel.events.handlers as handlers_module

        source = io.open(handlers_module.__file__, encoding="utf-8").read()
        self.assertNotIn("dispatch_service", source)
        self.assertNotIn("NotificationDispatchService", source)


class TenantIsolationTest(TestCase):
    def setUp(self):
        self.tenant_a = Tenant.objects.create(slug=f"t-a-{uuid.uuid4().hex[:8]}", name="A")
        self.tenant_b = Tenant.objects.create(slug=f"t-b-{uuid.uuid4().hex[:8]}", name="B")

    def test_dispatch_pending_with_tenant_filter_only_touches_that_tenant(self):
        notif_a = _make_notification(self.tenant_a)
        notif_b = _make_notification(self.tenant_b)

        NotificationDispatchService.dispatch_pending(tenant_id=self.tenant_a.id, limit=10)

        notif_a.refresh_from_db()
        notif_b.refresh_from_db()
        self.assertEqual(notif_a.status, NotificationStatus.SENT)
        self.assertEqual(notif_b.status, NotificationStatus.PENDING)

    def test_dispatch_pending_without_tenant_filter_touches_all_tenants(self):
        notif_a = _make_notification(self.tenant_a)
        notif_b = _make_notification(self.tenant_b)

        NotificationDispatchService.dispatch_pending(limit=10)

        notif_a.refresh_from_db()
        notif_b.refresh_from_db()
        self.assertEqual(notif_a.status, NotificationStatus.SENT)
        self.assertEqual(notif_b.status, NotificationStatus.SENT)


class FakeProviderBehaviorTest(TestCase):
    def test_fake_provider_default_success(self):
        provider = FakeSmsProvider()
        result = provider.send(notification=None)
        self.assertTrue(result.success)
        self.assertEqual(result.provider_name, "fake-sms")
        self.assertIsNotNone(result.external_id)

    def test_fake_provider_always_fail(self):
        provider = FakeSmsProvider(always_fail=True)
        result = provider.send(notification=None)
        self.assertFalse(result.success)
        self.assertEqual(result.provider_name, "fake-sms")


class DeliveryAttemptAuditTrailTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"t-{uuid.uuid4().hex[:8]}", name="T")

    def test_multiple_attempts_are_all_recorded(self):
        original_provider = NotificationProviderRegistry._providers.get(NotificationChannel.SMS)
        NotificationProviderRegistry.register(NotificationChannel.SMS, FakeSmsProvider(always_fail=True))
        try:
            notification = _make_notification(self.tenant, channel=NotificationChannel.SMS, max_retries=5)
            NotificationDispatchService.dispatch_pending(limit=10)

            notification.refresh_from_db()
            notification.next_attempt_at = timezone.now()
            notification.save(update_fields=["next_attempt_at"])
        finally:
            NotificationProviderRegistry.register(NotificationChannel.SMS, FakeSmsProvider())

        NotificationDispatchService.dispatch_pending(limit=10)

        attempts = NotificationDeliveryAttempt.objects.filter(notification=notification).order_by("attempt_number")
        self.assertEqual(attempts.count(), 2)
        self.assertEqual(attempts[0].attempt_number, 1)
        self.assertEqual(attempts[1].attempt_number, 2)
        self.assertEqual(attempts[1].status, NotificationStatus.SENT)
