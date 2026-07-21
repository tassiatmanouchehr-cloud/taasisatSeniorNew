"""Sanity tests: app registration, model registration, migration parity."""

from django.apps import apps as django_apps
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.state import ProjectState
from django.test import TestCase


class ExecutionAppSetupTest(TestCase):
    def test_app_is_installed(self):
        self.assertTrue(django_apps.is_installed("apps.execution"))

    def test_models_are_registered(self):
        from apps.execution.models import ExecutionSession

        self.assertEqual(ExecutionSession._meta.app_label, "execution")

    def test_services_import_cleanly(self):
        from apps.execution.services import ExecutionError, ExecutionService  # noqa: F401

    def test_no_missing_migrations_for_execution(self):
        """The execution app's models must be fully represented by its migrations."""
        loader = MigrationLoader(None, ignore_no_migrations=True)
        autodetector = MigrationAutodetector(
            loader.project_state(),
            ProjectState.from_apps(django_apps),
        )
        changes = autodetector.changes(graph=loader.graph)
        self.assertNotIn(
            "execution",
            changes,
            f"Missing migrations detected for apps.execution: {changes.get('execution')}",
        )
