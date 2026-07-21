"""
/api/v1/ routing — Module 17A foundation, extended in Module 17B.

The single canonical entrypoint for all versioned API routes. Reuses the
existing (Module 05-era) HealthCheckView rather than duplicating it.
"""

from django.urls import path

from apps.kernel.api.health import HealthCheckView

from .views import (
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

app_name = "api"

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health-check"),
    path("sample/order-counts/", OrderCountsSampleView.as_view(), name="sample-order-counts"),
    path("sample/providers/", ProviderReportsSampleView.as_view(), name="sample-providers"),
    # Discovery
    path("discovery/suppliers/", SupplierDiscoveryListView.as_view(), name="discovery-suppliers"),
    # Pricing
    path("pricing/quotes/", QuoteCreateView.as_view(), name="pricing-quotes-create"),
    # Reviews
    path("reviews/", ReviewSubmitView.as_view(), name="reviews-submit"),
    path("suppliers/<uuid:supplier_id>/reputation/", SupplierReputationView.as_view(), name="supplier-reputation"),
    # Wallet
    path("wallet/balance/", WalletBalanceView.as_view(), name="wallet-balance"),
    path("wallet/transactions/", WalletTransactionListView.as_view(), name="wallet-transactions"),
    # Payments
    path("payments/intents/", PaymentIntentCreateView.as_view(), name="payments-intents-create"),
    path(
        "payments/intents/<uuid:intent_id>/attempts/",
        PaymentAttemptCreateView.as_view(),
        name="payments-attempts-create",
    ),
    path("payments/callbacks/fake/", FakeProviderCallbackView.as_view(), name="payments-callbacks-fake"),
]
