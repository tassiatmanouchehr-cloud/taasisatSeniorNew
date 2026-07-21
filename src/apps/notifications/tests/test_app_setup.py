"""Sanity tests: app registration, model registration, migration parity."""

from django.apps import apps as django_apps
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.state import ProjectState
from django.test import TestCase

from apps.kernel.events.registry import EventRegistry


class NotificationsAppSetupTest(TestCase):
    def test_app_is_installed(self):
        self.assertTrue(django_apps.is_installed("apps.notifications"))

    def test_model_is_registered(self):
        from apps.notifications.models import Notification

        self.assertEqual(Notification._meta.app_label, "notifications")

    def test_no_missing_migrations_for_notifications(self):
        """The notifications app's models must be fully represented by its migrations."""
        loader = MigrationLoader(None, ignore_no_migrations=True)
        autodetector = MigrationAutodetector(
            loader.project_state(),
            ProjectState.from_apps(django_apps),
        )
        changes = autodetector.changes(graph=loader.graph)
        self.assertNotIn(
            "notifications",
            changes,
            f"Missing migrations detected for apps.notifications: {changes.get('notifications')}",
        )

    def test_handlers_are_registered_on_app_ready(self):
        """AppConfig.ready() must have wired all 5 notification handlers exactly once."""
        from apps.kernel.events.base import (
            INVOICE_ISSUED,
            ORDER_ASSIGNED,
            ORDER_COMPLETED,
            ORDER_CREATED,
            ORDER_STARTED,
        )

        for event_type in (ORDER_CREATED, ORDER_ASSIGNED, ORDER_STARTED, ORDER_COMPLETED, INVOICE_ISSUED):
            self.assertEqual(
                len(EventRegistry.get_handlers(event_type)),
                1,
                f"expected exactly one handler registered for {event_type}",
            )
