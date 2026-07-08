import json

from django.test import RequestFactory, TestCase

from apps.api.views.base import ApiView
from apps.discovery.services import DiscoveryError
from apps.payments.services import PaymentError
from apps.pricing.services import PricingError
from apps.reviews.services import ReviewError
from apps.wallet.services import WalletError


class _RaisingView(ApiView):
    exception_to_raise = None

    def get(self, request):
        raise self.exception_to_raise


class DomainErrorMappingTest(TestCase):
    """Module 17B extension: per-module XError classes map to 400 domain_error, not 500."""

    def setUp(self):
        self.factory = RequestFactory()

    def _dispatch(self, exc):
        view = _RaisingView.as_view(exception_to_raise=exc)
        return view(self.factory.get("/")).render()

    def test_discovery_error_maps_to_domain_error(self):
        response = self._dispatch(DiscoveryError("bad query"))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content)["error"]["code"], "domain_error")

    def test_pricing_error_maps_to_domain_error(self):
        response = self._dispatch(PricingError("no rule"))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content)["error"]["code"], "domain_error")

    def test_review_error_maps_to_domain_error(self):
        response = self._dispatch(ReviewError("not completed"))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content)["error"]["code"], "domain_error")

    def test_wallet_error_maps_to_domain_error(self):
        response = self._dispatch(WalletError("insufficient funds"))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content)["error"]["code"], "domain_error")

    def test_payment_error_maps_to_domain_error(self):
        response = self._dispatch(PaymentError("mismatch"))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content)["error"]["code"], "domain_error")

    def test_domain_error_message_is_preserved_safely(self):
        response = self._dispatch(WalletError("Wallet has insufficient balance for this debit."))
        body = json.loads(response.content)
        self.assertEqual(body["error"]["message"], "Wallet has insufficient balance for this debit.")
