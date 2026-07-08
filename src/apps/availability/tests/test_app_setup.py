"""Sanity tests: app registration, model registration, migration parity."""

from django.apps import apps as django_apps
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.state import ProjectState
from django.test import TestCase


class AvailabilityAppSetupTest(TestCase):
    def test_app_is_installed(self):
        self.assertTrue(django_apps.is_installed("apps.availability"))

    def test_models_are_registered(self):
        from apps.availability.models import AvailabilityBlockedPeriod, CapacityRule, ProviderWorkingWindow

        self.assertEqual(ProviderWorkingWindow._meta.app_label, "availability")
        self.assertEqual(AvailabilityBlockedPeriod._meta.app_label, "availability")
        self.assertEqual(CapacityRule._meta.app_label, "availability")

    def test_services_import_cleanly(self):
        from apps.availability.services import (  # noqa: F401
            AvailabilityConfiguration,
            AvailabilityError,
            AvailabilityMutationService,
            AvailabilityQueryService,
            CapacityService,
        )

    def test_no_missing_migrations_for_availability(self):
        loader = MigrationLoader(None, ignore_no_migrations=True)
        autodetector = MigrationAutodetector(
            loader.project_state(),
            ProjectState.from_apps(django_apps),
        )
        changes = autodetector.changes(graph=loader.graph)
        self.assertNotIn(
            "availability", changes,
            f"Missing migrations detected for apps.availability: {changes.get('availability')}",
        )
