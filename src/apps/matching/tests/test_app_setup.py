"""Sanity tests: app registration, model registration, migration parity."""

from django.apps import apps as django_apps
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.state import ProjectState
from django.test import TestCase


class MatchingAppSetupTest(TestCase):
    def test_app_is_installed(self):
        self.assertTrue(django_apps.is_installed("apps.matching"))

    def test_models_are_registered(self):
        from apps.matching.models import MatchCandidate, MatchRound

        self.assertEqual(MatchRound._meta.app_label, "matching")
        self.assertEqual(MatchCandidate._meta.app_label, "matching")

    def test_services_import_cleanly(self):
        from apps.matching.services import (  # noqa: F401
            EligibilityService,
            MatchingConfiguration,
            MatchOrchestrator,
            RankingService,
            SimpleRankingStrategy,
        )

    def test_no_missing_migrations_for_matching(self):
        """The matching app's models must be fully represented by its migrations."""
        loader = MigrationLoader(None, ignore_no_migrations=True)
        autodetector = MigrationAutodetector(
            loader.project_state(),
            ProjectState.from_apps(django_apps),
        )
        changes = autodetector.changes(graph=loader.graph)
        self.assertNotIn(
            "matching",
            changes,
            f"Missing migrations detected for apps.matching: {changes.get('matching')}",
        )
