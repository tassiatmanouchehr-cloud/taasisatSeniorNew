"""Shared fixtures for wallet tests (not a test module itself)."""

import uuid

from django.test import TestCase

from apps.accounts.models.profiles import CustomerProfile
from apps.finance.services import FinancialPartyService
from apps.kernel.models import Person, Tenant, UserAccount
from apps.wallet.services import WalletService


class WalletTestCase(TestCase):
    """Base test case: a tenant, a customer FinancialParty, and a wallet."""

    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"wallet-{uuid.uuid4().hex[:8]}", name="Wallet Test Tenant")
        self.other_tenant = Tenant.objects.create(slug=f"wallet-other-{uuid.uuid4().hex[:8]}", name="Other Tenant")

        self.customer_profile = self._create_customer(tenant=self.tenant)
        self.party = FinancialPartyService.resolve_party_for_customer(self.customer_profile)
        self.wallet = WalletService.create_wallet(party=self.party)

    def _create_customer(self, *, tenant, display_name="Test Customer", phone=None) -> CustomerProfile:
        phone = phone or f"0912{uuid.uuid4().hex[:7]}"
        person = Person.objects.create(tenant=tenant, full_name=display_name)
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)
        return CustomerProfile.objects.create(
            user=user, person=person, phone=phone, display_name=display_name,
        )
