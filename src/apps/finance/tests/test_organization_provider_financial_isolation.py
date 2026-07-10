"""
Financial isolation regression — Epic 04 Sprint 3 (Enterprise Organization
Isolation, Provider Affiliation Activation).

Proves the fixed financial policy holds: an ORGANIZATION_PROVIDER-typed
supplier (an organization-affiliated caregiver, activated this Epic) still
resolves to its own FinancialPartyType.SUPPLIER party — never
FinancialPartyType.ORGANIZATION — exactly like an INDEPENDENT_PROVIDER
supplier. FinancialPartyService.resolve_party_for_supplier() is untouched
by this Epic; this test is the evidence that it stays behaving as before.
"""

import uuid

from django.test import TestCase

from apps.finance.models import FinancialPartyType
from apps.finance.services.party_service import FinancialPartyService
from apps.kernel.models import Tenant
from apps.kernel.models.supplier import (
    AvailabilityStatus,
    ServiceSupplier,
    SupplierStatus,
    SupplierType,
    VerificationLevel,
)


class OrganizationProviderFinancialIsolationTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"finiso-{uuid.uuid4().hex[:8]}", name="Financial Isolation Tenant")

    def _create_supplier(self, *, supplier_type) -> ServiceSupplier:
        return ServiceSupplier.objects.create(
            tenant_id=self.tenant.id, supplier_type=supplier_type,
            linked_entity_id=uuid.uuid4(), linked_entity_type="TestProfile", display_name="Test Supplier",
            status=SupplierStatus.ACTIVE, availability_status=AvailabilityStatus.AVAILABLE,
            verification_level=VerificationLevel.BASIC, service_categories=[],
        )

    def test_organization_provider_supplier_resolves_to_supplier_party_not_organization(self):
        supplier = self._create_supplier(supplier_type=SupplierType.ORGANIZATION_PROVIDER)
        party = FinancialPartyService.resolve_party_for_supplier(supplier)
        self.assertEqual(party.party_type, FinancialPartyType.SUPPLIER)

    def test_independent_provider_supplier_resolves_to_supplier_party(self):
        supplier = self._create_supplier(supplier_type=SupplierType.INDEPENDENT_PROVIDER)
        party = FinancialPartyService.resolve_party_for_supplier(supplier)
        self.assertEqual(party.party_type, FinancialPartyType.SUPPLIER)

    def test_organization_provider_and_independent_provider_get_distinct_parties(self):
        """Each individual — independent or affiliated — keeps their own
        wallet; affiliation never merges/redirects a caregiver's financial
        identity into the organization's."""
        affiliated_supplier = self._create_supplier(supplier_type=SupplierType.ORGANIZATION_PROVIDER)
        independent_supplier = self._create_supplier(supplier_type=SupplierType.INDEPENDENT_PROVIDER)

        affiliated_party = FinancialPartyService.resolve_party_for_supplier(affiliated_supplier)
        independent_party = FinancialPartyService.resolve_party_for_supplier(independent_supplier)

        self.assertNotEqual(affiliated_party.id, independent_party.id)

    def test_only_organization_typed_supplier_resolves_to_organization_party(self):
        org_supplier = self._create_supplier(supplier_type=SupplierType.ORGANIZATION)
        party = FinancialPartyService.resolve_party_for_supplier(org_supplier)
        self.assertEqual(party.party_type, FinancialPartyType.ORGANIZATION)
