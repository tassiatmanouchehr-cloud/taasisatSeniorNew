from decimal import Decimal

from apps.api.permission_keys import WALLET_READ
from apps.finance.services import FinancialPartyService
from apps.wallet.models import Wallet
from apps.wallet.services import WalletService, WalletTransactionService

from .helpers import ApiTestCase


class WalletBalanceEndpointTest(ApiTestCase):
    def test_unauthenticated_request_is_rejected(self):
        response = self.client.get("/api/v1/wallet/balance/")
        self.assertEqual(response.status_code, 401)

    def test_authenticated_without_permission_is_forbidden(self):
        self.client.force_login(self.customer_profile.user)
        response = self.client.get("/api/v1/wallet/balance/")
        self.assertEqual(response.status_code, 403)

    def test_returns_zero_balance_without_creating_a_wallet(self):
        self._grant(self.customer_profile.user, self.tenant, [WALLET_READ])
        self.client.force_login(self.customer_profile.user)

        response = self.client.get("/api/v1/wallet/balance/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Decimal(response.json()["balance"]), Decimal("0.00"))
        self.assertEqual(Wallet.objects.count(), 0)

    def test_returns_actual_balance(self):
        self._grant(self.customer_profile.user, self.tenant, [WALLET_READ])
        party = FinancialPartyService.resolve_party_for_customer(self.customer_profile)
        wallet = WalletService.create_wallet(party=party)
        WalletTransactionService.credit(wallet_id=wallet.id, amount=Decimal("50000"))

        self.client.force_login(self.customer_profile.user)
        response = self.client.get("/api/v1/wallet/balance/")

        self.assertEqual(Decimal(response.json()["balance"]), Decimal("50000.00"))

    def test_only_sees_own_wallet_not_other_customers(self):
        self._grant(self.customer_profile.user, self.tenant, [WALLET_READ])

        other_customer = self._create_customer(tenant=self.tenant, display_name="Other Customer")
        other_party = FinancialPartyService.resolve_party_for_customer(other_customer)
        other_wallet = WalletService.create_wallet(party=other_party)
        WalletTransactionService.credit(wallet_id=other_wallet.id, amount=Decimal("999999"))

        self.client.force_login(self.customer_profile.user)
        response = self.client.get("/api/v1/wallet/balance/")

        self.assertEqual(Decimal(response.json()["balance"]), Decimal("0.00"))


class WalletTransactionListEndpointTest(ApiTestCase):
    def test_unauthenticated_request_is_rejected(self):
        response = self.client.get("/api/v1/wallet/transactions/")
        self.assertEqual(response.status_code, 401)

    def test_empty_when_no_wallet_exists(self):
        self._grant(self.customer_profile.user, self.tenant, [WALLET_READ])
        self.client.force_login(self.customer_profile.user)

        response = self.client.get("/api/v1/wallet/transactions/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"], [])
        self.assertEqual(response.json()["total_count"], 0)

    def test_returns_paginated_transaction_history(self):
        self._grant(self.customer_profile.user, self.tenant, [WALLET_READ])
        party = FinancialPartyService.resolve_party_for_customer(self.customer_profile)
        wallet = WalletService.create_wallet(party=party)
        WalletTransactionService.credit(wallet_id=wallet.id, amount=Decimal("1000"))
        WalletTransactionService.credit(wallet_id=wallet.id, amount=Decimal("2000"))

        self.client.force_login(self.customer_profile.user)
        response = self.client.get("/api/v1/wallet/transactions/?limit=1")

        body = response.json()
        self.assertEqual(len(body["results"]), 1)
        self.assertEqual(body["total_count"], 2)
        self.assertTrue(body["has_more"])

    def test_no_mutation_endpoints_exist(self):
        self._grant(self.customer_profile.user, self.tenant, [WALLET_READ])
        self.client.force_login(self.customer_profile.user)

        response = self.client.post("/api/v1/wallet/balance/", {}, content_type="application/json")
        self.assertEqual(response.status_code, 405)

        response = self.client.post("/api/v1/wallet/transactions/", {}, content_type="application/json")
        self.assertEqual(response.status_code, 405)
