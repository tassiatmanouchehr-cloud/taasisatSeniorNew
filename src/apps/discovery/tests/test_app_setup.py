"""Sanity tests: app registration, no models/migrations, services import cleanly."""

from django.apps import apps as django_apps
from django.test import TestCase


class DiscoveryAppSetupTest(TestCase):
    def test_app_is_installed(self):
        self.assertTrue(django_apps.is_installed("apps.discovery"))

    def test_app_has_no_models(self):
        """Module 12 is service-layer only, by design — zero models, zero migrations."""
        self.assertEqual(list(django_apps.get_app_config("discovery").get_models()), [])

    def test_services_import_cleanly(self):
        from apps.discovery.services import (  # noqa: F401
            DiscoveryConfiguration,
            DiscoveryError,
            DiscoveryRankingService,
            DiscoveryService,
            SearchQuery,
            SearchResultItem,
            SearchResultPage,
            SupplierSearchService,
            normalize_query,
        )
