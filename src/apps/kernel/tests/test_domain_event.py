"""Tests for DomainEvent — Module 09 foundation."""

import dataclasses
import uuid

from django.test import TestCase

from apps.kernel.events.base import DomainEvent


class DomainEventTest(TestCase):
    def _make(self, **overrides):
        defaults = dict(
            event_type="OrderCreated",
            tenant_id=uuid.uuid4(),
            aggregate_type="Order",
            aggregate_id=uuid.uuid4(),
            payload={"order_number": "ORD-1"},
        )
        defaults.update(overrides)
        return DomainEvent(**defaults)

    def test_creation_succeeds_with_required_fields(self):
        event = self._make()
        self.assertEqual(event.event_type, "OrderCreated")
        self.assertEqual(event.aggregate_type, "Order")
        self.assertEqual(event.payload, {"order_number": "ORD-1"})

    def test_id_is_auto_generated_and_unique(self):
        first = self._make()
        second = self._make()
        self.assertIsInstance(first.id, uuid.UUID)
        self.assertNotEqual(first.id, second.id)

    def test_occurred_at_defaults_to_now(self):
        event = self._make()
        self.assertIsNotNone(event.occurred_at)

    def test_actor_id_defaults_to_none(self):
        event = self._make()
        self.assertIsNone(event.actor_id)

    def test_payload_defaults_to_empty_dict_when_omitted(self):
        event = DomainEvent(
            event_type="OrderCreated", tenant_id=uuid.uuid4(),
            aggregate_type="Order", aggregate_id=uuid.uuid4(),
        )
        self.assertEqual(event.payload, {})

    def test_immutable_event_type(self):
        event = self._make()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            event.event_type = "Tampered"

    def test_immutable_payload_reference(self):
        event = self._make()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            event.payload = {"tampered": True}

    def test_immutable_tenant_id(self):
        event = self._make()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            event.tenant_id = uuid.uuid4()

    def test_requires_event_type(self):
        with self.assertRaises(ValueError):
            self._make(event_type="")

    def test_requires_tenant_id(self):
        with self.assertRaises(ValueError):
            self._make(tenant_id=None)

    def test_requires_aggregate_type(self):
        with self.assertRaises(ValueError):
            self._make(aggregate_type="")

    def test_requires_aggregate_id(self):
        with self.assertRaises(ValueError):
            self._make(aggregate_id=None)
