"""Sanity tests: app registration, service imports."""

from django.apps import apps as django_apps
from django.test import TestCase


class ReportingAppSetupTest(TestCase):
    def test_app_is_installed(self):
        self.assertTrue(django_apps.is_installed("apps.reporting"))

    def test_services_import_cleanly(self):
        from apps.reporting.services import (  # noqa: F401
            FinancialReportService,
            MarketplaceReportService,
            OperationalReportService,
            ProviderReportService,
            ReportingConfiguration,
            ReportingError,
            ReportingService,
        )

    def test_dto_import_cleanly(self):
        from apps.reporting.dto import (  # noqa: F401
            FinancialSummaryReport,
            MarketplaceStatsReport,
            OrderCountsReport,
            ProviderPerformanceReport,
        )
