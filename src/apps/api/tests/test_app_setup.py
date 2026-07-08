from django.apps import apps as django_apps
from django.test import TestCase


class ApiAppSetupTest(TestCase):
    def test_app_is_installed(self):
        self.assertTrue(django_apps.is_installed("apps.api"))

    def test_core_modules_import_cleanly(self):
        from apps.api.errors import ApiError  # noqa: F401
        from apps.api.exception_handler import api_exception_handler  # noqa: F401
        from apps.api.pagination import Page, paginate, parse_pagination_params  # noqa: F401
        from apps.api.permissions import require_authenticated, require_permission, resolve_tenant_id  # noqa: F401
        from apps.api.serializers import (  # noqa: F401
            OrderCountsReportSerializer,
            ProviderPerformanceReportSerializer,
        )
        from apps.api.views import ApiView, OrderCountsSampleView, ProviderReportsSampleView  # noqa: F401

    def test_rest_framework_is_installed(self):
        self.assertTrue(django_apps.is_installed("rest_framework"))
