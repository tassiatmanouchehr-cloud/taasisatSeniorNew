"""Tests for EventRegistry — Module 09 foundation."""

from django.test import TestCase

from apps.kernel.events.registry import EventRegistry

EVENT_TYPE = "TestRegistryEvent"
OTHER_EVENT_TYPE = "OtherTestRegistryEvent"


def _handler_a(event):
    pass


def _handler_b(event):
    pass


class EventRegistryTest(TestCase):
    def tearDown(self):
        EventRegistry.unregister(EVENT_TYPE, _handler_a)
        EventRegistry.unregister(EVENT_TYPE, _handler_b)
        EventRegistry.unregister(OTHER_EVENT_TYPE, _handler_a)

    def test_get_handlers_empty_for_unknown_event_type(self):
        self.assertEqual(EventRegistry.get_handlers("NeverRegistered"), [])

    def test_register_single_handler(self):
        EventRegistry.register(EVENT_TYPE, _handler_a)
        self.assertEqual(EventRegistry.get_handlers(EVENT_TYPE), [_handler_a])

    def test_register_multiple_handlers_for_same_event_type(self):
        EventRegistry.register(EVENT_TYPE, _handler_a)
        EventRegistry.register(EVENT_TYPE, _handler_b)
        self.assertEqual(EventRegistry.get_handlers(EVENT_TYPE), [_handler_a, _handler_b])

    def test_registration_is_idempotent(self):
        EventRegistry.register(EVENT_TYPE, _handler_a)
        EventRegistry.register(EVENT_TYPE, _handler_a)
        EventRegistry.register(EVENT_TYPE, _handler_a)
        self.assertEqual(EventRegistry.get_handlers(EVENT_TYPE), [_handler_a])

    def test_handlers_do_not_cross_contaminate_event_types(self):
        EventRegistry.register(EVENT_TYPE, _handler_a)
        EventRegistry.register(OTHER_EVENT_TYPE, _handler_b)
        self.assertEqual(EventRegistry.get_handlers(EVENT_TYPE), [_handler_a])
        self.assertEqual(EventRegistry.get_handlers(OTHER_EVENT_TYPE), [_handler_b])

    def test_unregister_removes_handler(self):
        EventRegistry.register(EVENT_TYPE, _handler_a)
        EventRegistry.unregister(EVENT_TYPE, _handler_a)
        self.assertEqual(EventRegistry.get_handlers(EVENT_TYPE), [])

    def test_unregister_unknown_handler_is_a_noop(self):
        EventRegistry.unregister(EVENT_TYPE, _handler_a)  # must not raise

    def test_get_handlers_returns_a_snapshot_copy(self):
        EventRegistry.register(EVENT_TYPE, _handler_a)
        snapshot = EventRegistry.get_handlers(EVENT_TYPE)
        snapshot.append(_handler_b)
        self.assertEqual(EventRegistry.get_handlers(EVENT_TYPE), [_handler_a])
