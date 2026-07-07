"""Sanity tests: app registration, model registration, migration parity."""

from django.apps import apps as django_apps
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.state import ProjectState
from django.test import TestCase


class BookingAppSetupTest(TestCase):
    def test_app_is_installed(self):
        self.assertTrue(django_apps.is_installed("apps.booking"))

    def test_models_are_registered(self):
        from apps.booking.models import SupplierAssignment

        self.assertEqual(SupplierAssignment._meta.app_label, "booking")

    def test_services_import_cleanly(self):
        from apps.booking.services import AssignmentError, AssignmentService, BookingConfiguration  # noqa: F401

    def test_no_missing_migrations_for_booking(self):
        """The booking app's models must be fully represented by its migrations."""
        loader = MigrationLoader(None, ignore_no_migrations=True)
        autodetector = MigrationAutodetector(
            loader.project_state(),
            ProjectState.from_apps(django_apps),
        )
        changes = autodetector.changes(graph=loader.graph)
        self.assertNotIn(
            "booking", changes,
            f"Missing migrations detected for apps.booking: {changes.get('booking')}",
        )
