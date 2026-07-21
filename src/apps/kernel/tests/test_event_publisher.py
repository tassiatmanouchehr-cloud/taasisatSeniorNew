"""Tests for apps.kernel.events.publish() — Module 09 foundation."""

import uuid

from django.test import TestCase

from apps.kernel.events.base import DomainEvent
from apps.kernel.events.publisher import publish
from apps.kernel.events.registry import EventRegistry
from apps.kernel.models import Tenant
from apps.kernel.models.audit import AuditLog

EVENT_TYPE = "TestPublisherEvent"


class EventPublisherTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"pub-{uuid.uuid4().hex[:8]}", name="Publisher Test Tenant")
        self.calls = []

    def tearDown(self):
        EventRegistry._handlers.pop(EVENT_TYPE, None)

    def _event(self, **overrides):
        defaults = dict(
            event_type=EVENT_TYPE,
            tenant_id=self.tenant.id,
            aggregate_type="TestAggregate",
            aggregate_id=uuid.uuid4(),
            payload={"foo": "bar"},
        )
        defaults.update(overrides)
        return DomainEvent(**defaults)

    def _recording_handler(self, name):
        def handler(event):
            self.calls.append(name)

        return handler

    def test_publish_dispatches_to_single_registered_handler(self):
        EventRegistry.register(EVENT_TYPE, self._recording_handler("a"))
        publish(self._event())
        self.assertEqual(self.calls, ["a"])

    def test_publish_dispatches_to_all_registered_handlers(self):
        EventRegistry.register(EVENT_TYPE, self._recording_handler("a"))
        EventRegistry.register(EVENT_TYPE, self._recording_handler("b"))
        publish(self._event())
        self.assertEqual(self.calls, ["a", "b"])

    def test_publish_with_no_registered_handlers_is_a_noop(self):
        publish(self._event())  # must not raise
        self.assertEqual(self.calls, [])

    def test_handler_failure_does_not_prevent_other_handlers_from_running(self):
        def failing_handler(event):
            self.calls.append("failing")
            raise RuntimeError("boom")

        EventRegistry.register(EVENT_TYPE, failing_handler)
        EventRegistry.register(EVENT_TYPE, self._recording_handler("survivor"))

        publish(self._event())  # must not raise

        self.assertEqual(self.calls, ["failing", "survivor"])

    def test_handler_exception_never_propagates_out_of_publish(self):
        def failing_handler(event):
            raise RuntimeError("boom")

        EventRegistry.register(EVENT_TYPE, failing_handler)
        publish(self._event())  # must not raise

    def test_publish_creates_an_audit_log_entry(self):
        publish(self._event())

        self.assertTrue(
            AuditLog.objects.filter(
                tenant_id=self.tenant.id,
                action=f"domain_event.{EVENT_TYPE}",
            ).exists(),
        )

    def test_audit_log_entry_carries_correct_context(self):
        actor_id = uuid.uuid4()
        aggregate_id = uuid.uuid4()
        publish(self._event(actor_id=actor_id, aggregate_id=aggregate_id))

        entry = AuditLog.objects.get(tenant_id=self.tenant.id, action=f"domain_event.{EVENT_TYPE}")
        self.assertEqual(entry.actor_id, actor_id)
        self.assertEqual(entry.resource_type, "TestAggregate")
        self.assertEqual(entry.resource_id, aggregate_id)
        self.assertEqual(entry.module_id, "M09")

    def test_publish_audits_even_when_no_handlers_registered(self):
        publish(self._event())
        self.assertTrue(
            AuditLog.objects.filter(tenant_id=self.tenant.id, action=f"domain_event.{EVENT_TYPE}").exists(),
        )

    def test_publish_audits_even_when_a_handler_fails(self):
        def failing_handler(event):
            raise RuntimeError("boom")

        EventRegistry.register(EVENT_TYPE, failing_handler)
        publish(self._event())

        self.assertTrue(
            AuditLog.objects.filter(tenant_id=self.tenant.id, action=f"domain_event.{EVENT_TYPE}").exists(),
        )

    def test_multiple_publishes_create_multiple_audit_entries(self):
        publish(self._event())
        publish(self._event())

        self.assertEqual(
            AuditLog.objects.filter(tenant_id=self.tenant.id, action=f"domain_event.{EVENT_TYPE}").count(),
            2,
        )

    def test_publish_is_tenant_scoped_in_audit(self):
        other_tenant = Tenant.objects.create(slug=f"pub-other-{uuid.uuid4().hex[:8]}", name="Other Tenant")
        publish(self._event(tenant_id=other_tenant.id))

        self.assertFalse(
            AuditLog.objects.filter(tenant_id=self.tenant.id, action=f"domain_event.{EVENT_TYPE}").exists(),
        )
        self.assertTrue(
            AuditLog.objects.filter(tenant_id=other_tenant.id, action=f"domain_event.{EVENT_TYPE}").exists(),
        )
