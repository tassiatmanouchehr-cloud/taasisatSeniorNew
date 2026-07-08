"""Tests for FinancialPartyService resolution."""

from apps.finance.models import FinancialParty, FinancialPartyType
from apps.finance.services import FinancialPartyService
from apps.kernel.models.supplier import SupplierType

from .helpers import FinanceTestCase


class FinancialPartyServiceTest(FinanceTestCase):
    def test_resolve_party_for_supplier_creates_supplier_party(self):
        party = FinancialPartyService.resolve_party_for_supplier(self.supplier)

        self.assertEqual(party.party_type, FinancialPartyType.SUPPLIER)
        self.assertEqual(party.linked_entity_type, "ServiceSupplier")
        self.assertEqual(party.linked_entity_id, self.supplier.id)

    def test_resolve_party_for_organization_supplier_creates_organization_party(self):
        org_supplier = self._create_supplier(tenant=self.tenant, supplier_type=SupplierType.ORGANIZATION)
        party = FinancialPartyService.resolve_party_for_supplier(org_supplier)

        self.assertEqual(party.party_type, FinancialPartyType.ORGANIZATION)

    def test_resolve_party_for_supplier_is_idempotent(self):
        first = FinancialPartyService.resolve_party_for_supplier(self.supplier)
        second = FinancialPartyService.resolve_party_for_supplier(self.supplier)

        self.assertEqual(first.id, second.id)
        self.assertEqual(FinancialParty.objects.filter(linked_entity_id=self.supplier.id).count(), 1)

    def test_resolve_party_for_customer(self):
        party = FinancialPartyService.resolve_party_for_customer(self.customer_profile)

        self.assertEqual(party.party_type, FinancialPartyType.CUSTOMER)
        self.assertEqual(party.linked_entity_type, "CustomerProfile")
        self.assertEqual(party.tenant_id, self.customer_profile.person.tenant_id)

    def test_resolve_platform_party(self):
        party = FinancialPartyService.resolve_platform_party(self.tenant)

        self.assertEqual(party.party_type, FinancialPartyType.PLATFORM)
        self.assertEqual(party.linked_entity_type, "Tenant")
        self.assertEqual(party.linked_entity_id, self.tenant.id)
