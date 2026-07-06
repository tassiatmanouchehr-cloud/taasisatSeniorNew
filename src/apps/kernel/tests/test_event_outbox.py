"""
Tests for CES Event Outbox model and EventPublisher service.

Covers:
- Event creation with full CES envelope
- EventPublisher.publish() validates required fields
- EventPublisher.publish_batch() creates multiple events
- mark_published() transitions to published state
- mark_failed() increments retry and applies backoff
- Dead-letter after max retries
"""

import uuid

from django.test import TestCase
from django.utils import timezone

from apps.kernel.models.event_outbox import EventOutbox, EventStatus, PrivacyClass
from apps.kernel.services.event_publisher import EventPublisher


class EventOutboxModelTest(TestCase):
    """Test EventOutbox model behavior."""

    def setUp(self):
        self.tenant_id = uuid.uuid4()

    def test_create_event_with_defaults(self):
        event = EventOutbox.objects.create(
            tenant_id=self.tenant_id,
            event_type="Test.Created.v1",
            occurred_at=timezone.now(),
            source_module="M99",
            correlation_id=uuid.uuid4(),
            payload={"test": True},
        )
        self.assertEqual(event.status, EventStatus.PENDING)
        self.assertEqual(event.retry_count, 0)
        self.assertEqual(event.max_retries, 5)
        self.assertEqual(event.privacy_class, PrivacyClass.INTERNAL)
        self.assertIsNone(event.published_at)

    def test_mark_published(self):
        event = EventOutbox.objects.create(
            tenant_id=self.tenant_id,
            event_type="Test.Created.v1",
            occurred_at=timezone.now(),
            source_module="M99",
            correlation_id=uuid.uuid4(),
            payload={},
        )
        event.mark_published()
        event.refresh_from_db()
        self.assertEqual(event.status, EventStatus.PUBLISHED)
        self.assertIsNotNone(event.published_at)

    def test_mark_failed_increments_retry(self):
        event = EventOutbox.objects.create(
            tenant_id=self.tenant_id,
            event_type="Test.Created.v1",
            occurred_at=timezone.now(),
            source_module="M99",
            correlation_id=uuid.uuid4(),
            payload={},
        )
        event.mark_failed("Connection timeout")
        event.refresh_from_db()
        self.assertEqual(event.status, EventStatus.FAILED)
        self.assertEqual(event.retry_count, 1)
        self.assertIn("Connection timeout", event.error_message)
        self.assertIsNotNone(event.next_retry_at)

    def test_dead_letter_after_max_retries(self):
        event = EventOutbox.objects.create(
            tenant_id=self.tenant_id,
            event_type="Test.Created.v1",
            occurred_at=timezone.now(),
            source_module="M99",
            correlation_id=uuid.uuid4(),
            payload={},
            retry_count=4,  # One more failure → dead letter
            max_retries=5,
        )
        event.mark_failed("Final failure")
        event.refresh_from_db()
        self.assertEqual(event.status, EventStatus.DEAD_LETTER)
        self.assertEqual(event.retry_count, 5)


class EventPublisherTest(TestCase):
    """Test EventPublisher service."""

    def setUp(self):
        self.tenant_id = uuid.uuid4()

    def test_publish_creates_event(self):
        event = EventPublisher.publish(
            tenant_id=self.tenant_id,
            event_type="Request.Created.v1",
            source_module="M01",
            payload={"request_id": str(uuid.uuid4())},
        )
        self.assertIsNotNone(event.id)
        self.assertEqual(event.event_type, "Request.Created.v1")
        self.assertEqual(event.source_module, "M01")
        self.assertEqual(event.status, EventStatus.PENDING)
        self.assertIsNotNone(event.correlation_id)

    def test_publish_requires_tenant_id(self):
        with self.assertRaises(ValueError):
            EventPublisher.publish(
                tenant_id=None,
                event_type="Test.v1",
                source_module="M99",
                payload={},
            )

    def test_publish_requires_event_type(self):
        with self.assertRaises(ValueError):
            EventPublisher.publish(
                tenant_id=self.tenant_id,
                event_type="",
                source_module="M99",
                payload={},
            )

    def test_publish_batch(self):
        events_data = [
            {
                "tenant_id": self.tenant_id,
                "event_type": f"Test.Event{i}.v1",
                "source_module": "M99",
                "payload": {"index": i},
            }
            for i in range(5)
        ]
        created = EventPublisher.publish_batch(events=events_data)
        self.assertEqual(len(created), 5)
        self.assertEqual(EventOutbox.objects.filter(tenant_id=self.tenant_id).count(), 5)

    def test_publish_preserves_correlation_id(self):
        corr_id = uuid.uuid4()
        event = EventPublisher.publish(
            tenant_id=self.tenant_id,
            event_type="Test.v1",
            source_module="M99",
            payload={},
            correlation_id=corr_id,
        )
        self.assertEqual(event.correlation_id, corr_id)
