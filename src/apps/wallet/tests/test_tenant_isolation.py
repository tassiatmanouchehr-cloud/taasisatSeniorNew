from decimal import Decimal

from apps.finance.services import FinancialPartyService
from apps.wallet.models import Wallet, WalletTransaction
from apps.wallet.services import WalletService, WalletTransactionService

from .helpers import WalletTestCase


class WalletTenantIsolationTest(WalletTestCase):
    def setUp(self):
        super().setUp()

        self.other_customer = self._create_customer(tenant=self.other_tenant, display_name="Other Customer")
        self.other_party = FinancialPartyService.resolve_party_for_customer(self.other_customer)
        self.other_wallet = WalletService.create_wallet(party=self.other_party)

        WalletTransactionService.credit(wallet_id=self.wallet.id, amount=Decimal("100"))
        WalletTransactionService.credit(wallet_id=self.other_wallet.id, amount=Decimal("200"))

    def test_for_tenant_scopes_wallets(self):
        tenant_wallets = Wallet.objects.for_tenant(self.tenant.id)
        other_tenant_wallets = Wallet.objects.for_tenant(self.other_tenant.id)

        self.assertIn(self.wallet, tenant_wallets)
        self.assertNotIn(self.other_wallet, tenant_wallets)
        self.assertIn(self.other_wallet, other_tenant_wallets)
        self.assertNotIn(self.wallet, other_tenant_wallets)

    def test_for_tenant_scopes_transactions(self):
        tenant_txns = WalletTransaction.objects.for_tenant(self.tenant.id)
        other_tenant_txns = WalletTransaction.objects.for_tenant(self.other_tenant.id)

        self.assertTrue(all(t.tenant_id == self.tenant.id for t in tenant_txns))
        self.assertTrue(all(t.tenant_id == self.other_tenant.id for t in other_tenant_txns))

    def test_balances_do_not_leak_across_tenants(self):
        self.wallet.refresh_from_db()
        self.other_wallet.refresh_from_db()

        self.assertEqual(self.wallet.balance, Decimal("100.00"))
        self.assertEqual(self.other_wallet.balance, Decimal("200.00"))

    def test_overdraft_config_is_tenant_scoped(self):
        from apps.kernel.models.configuration import ConfigurationKey, ConfigurationValue, ScopeLevel, ValueType

        config_key, _ = ConfigurationKey.objects.get_or_create(
            key="wallet.overdraft.enabled",
            defaults={"owner_module": "M14", "value_type": ValueType.BOOLEAN, "scope_level": ScopeLevel.TENANT},
        )
        ConfigurationValue.objects.update_or_create(
            tenant_id=self.tenant.id,
            config_key=config_key,
            scope_type=ScopeLevel.TENANT,
            defaults={"value": True, "is_active": True},
        )

        # Overdraft enabled for self.tenant only.
        WalletTransactionService.debit(wallet_id=self.wallet.id, amount=Decimal("500"))

        from apps.wallet.services import WalletError

        with self.assertRaises(WalletError):
            WalletTransactionService.debit(wallet_id=self.other_wallet.id, amount=Decimal("500"))
