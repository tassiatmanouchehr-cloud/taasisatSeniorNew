"""Sanity tests: app registration, model registration, service imports."""

from django.apps import apps as django_apps
from django.test import TestCase


class WalletAppSetupTest(TestCase):
    def test_app_is_installed(self):
        self.assertTrue(django_apps.is_installed("apps.wallet"))

    def test_models_are_registered(self):
        from apps.wallet.models import Wallet, WalletBalanceSnapshot, WalletTransaction

        self.assertEqual(Wallet._meta.app_label, "wallet")
        self.assertEqual(WalletTransaction._meta.app_label, "wallet")
        self.assertEqual(WalletBalanceSnapshot._meta.app_label, "wallet")

    def test_services_import_cleanly(self):
        from apps.wallet.services import (  # noqa: F401
            WalletConfiguration,
            WalletError,
            WalletService,
            WalletTransactionService,
        )
