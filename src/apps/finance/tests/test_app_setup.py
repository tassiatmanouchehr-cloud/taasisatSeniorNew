"""Sanity tests: app registration, model registration, migration parity."""

from django.apps import apps as django_apps
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.state import ProjectState
from django.test import TestCase


class FinanceAppSetupTest(TestCase):
    def test_app_is_installed(self):
        self.assertTrue(django_apps.is_installed("apps.finance"))

    def test_models_are_registered(self):
        from apps.finance.models import FinancialDocument, FinancialParty, LedgerEntry

        self.assertEqual(FinancialDocument._meta.app_label, "finance")
        self.assertEqual(FinancialParty._meta.app_label, "finance")
        self.assertEqual(LedgerEntry._meta.app_label, "finance")

    def test_services_import_cleanly(self):
        from apps.finance.services import (  # noqa: F401
            EscrowService,
            FinanceConfiguration,
            FinanceError,
            FinancialDocumentService,
            FinancialPartyService,
            LedgerService,
            ObligationService,
            PaymentService,
            SettlementService,
            WalletService,
        )

    def test_no_missing_migrations_for_finance(self):
        """The finance app's models must be fully represented by its migrations."""
        loader = MigrationLoader(None, ignore_no_migrations=True)
        autodetector = MigrationAutodetector(
            loader.project_state(),
            ProjectState.from_apps(django_apps),
        )
        changes = autodetector.changes(graph=loader.graph)
        self.assertNotIn(
            "finance",
            changes,
            f"Missing migrations detected for apps.finance: {changes.get('finance')}",
        )
