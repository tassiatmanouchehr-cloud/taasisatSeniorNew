from django.apps import apps as django_apps
from django.test import TestCase


class ApiAppSetupTest(TestCase):
    def test_app_is_installed(self):
        self.assertTrue(django_apps.is_installed("apps.api"))

    def test_core_modules_import_cleanly(self):
        from apps.api.errors import ApiError  # noqa: F401
        from apps.api.exception_handler import api_exception_handler  # noqa: F401
        from apps.api.pagination import Page, paginate, parse_pagination_params  # noqa: F401
        from apps.api.permission_keys import (  # noqa: F401
            DISCOVERY_SUPPLIERS_READ,
            PAYMENTS_ATTEMPTS_CREATE,
            PAYMENTS_INTENTS_CREATE,
            PRICING_QUOTES_CREATE,
            REVIEWS_READ,
            REVIEWS_SUBMIT,
            WALLET_READ,
        )
        from apps.api.permissions import (  # noqa: F401
            require_authenticated,
            require_permission,
            resolve_customer_profile,
            resolve_tenant_id,
        )
        from apps.api.serializers import (  # noqa: F401
            FakeCallbackSerializer,
            OrderCountsReportSerializer,
            PaymentAttemptSerializer,
            PaymentIntentCreateSerializer,
            PaymentIntentSerializer,
            ProviderPerformanceReportSerializer,
            QuoteRequestSerializer,
            QuoteSerializer,
            ReputationSummarySerializer,
            ReviewSerializer,
            ReviewSubmitSerializer,
            SearchResultItemSerializer,
            WalletBalanceSerializer,
            WalletTransactionSerializer,
        )
        from apps.api.views import (  # noqa: F401
            ApiView,
            FakeProviderCallbackView,
            OrderCountsSampleView,
            PaymentAttemptCreateView,
            PaymentIntentCreateView,
            ProviderReportsSampleView,
            QuoteCreateView,
            ReviewSubmitView,
            SupplierDiscoveryListView,
            SupplierReputationView,
            WalletBalanceView,
            WalletTransactionListView,
        )

    def test_rest_framework_is_installed(self):
        self.assertTrue(django_apps.is_installed("rest_framework"))
