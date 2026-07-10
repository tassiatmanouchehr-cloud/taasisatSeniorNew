"""
Tests for the accounts <-> kernel supplier bridge.

Verifies:
- The bridge correctly translates CaregiverProfile/OrganizationProfile into
  generic ServiceSupplier records and back.
- Kernel's ServiceSupplier registry stays generic — no accounts-specific
  (caregiver/organization) references leak into kernel modules.
"""

import ast
import inspect

from django.test import TestCase

from apps.accounts.models.profiles import CaregiverProfile, OrganizationProfile
from apps.accounts.services.supplier_bridge import (
    CAREGIVER_LINKED_TYPE,
    ORGANIZATION_LINKED_TYPE,
    get_or_create_supplier_for_caregiver,
    get_or_create_supplier_for_organization,
    resolve_supplier_entity,
)
from apps.kernel.models import Person, Tenant, UserAccount
from apps.kernel.models.supplier import ServiceSupplier, SupplierType
from apps.kernel.services import supplier_registry, supplier_resolver
from apps.kernel.services.tenant_service import TenantService


def _module_imports_accounts(module) -> bool:
    """True if `module`'s actual import statements reference apps.accounts.

    Uses the AST rather than a text scan so that mentioning "accounts" or
    "CaregiverProfile" in a docstring/comment (e.g. as a warning example)
    never produces a false positive.
    """
    tree = ast.parse(inspect.getsource(module))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name.startswith("apps.accounts") for alias in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("apps.accounts"):
                return True
    return False


class SupplierBridgeTest(TestCase):
    def setUp(self):
        self.tenant = TenantService.get_default_tenant()
        self.person = Person.objects.create(tenant=self.tenant, full_name="Caregiver")
        self.user = UserAccount.objects.create_user(
            phone="09140000001", person=self.person, tenant=self.tenant
        )
        self.caregiver = CaregiverProfile.objects.create(
            user=self.user, person=self.person, phone="09140000001", display_name="Caregiver",
        )
        self.org_admin_person = Person.objects.create(tenant=self.tenant, full_name="Org Admin")
        self.org_admin = UserAccount.objects.create_user(
            phone="09140000002", person=self.org_admin_person, tenant=self.tenant
        )
        self.organization = OrganizationProfile.objects.create(
            name="Test Org", code="ORG-BRIDGE1", admin_user=self.org_admin, tenant=self.tenant,
        )

    def test_creates_supplier_for_caregiver(self):
        supplier = get_or_create_supplier_for_caregiver(self.caregiver)
        self.assertEqual(supplier.linked_entity_id, self.caregiver.id)
        self.assertEqual(supplier.linked_entity_type, CAREGIVER_LINKED_TYPE)
        self.assertEqual(supplier.supplier_type, SupplierType.INDEPENDENT_PROVIDER)
        self.assertEqual(supplier.tenant_id, self.person.tenant_id)

    def test_caregiver_bridge_is_idempotent(self):
        first = get_or_create_supplier_for_caregiver(self.caregiver)
        second = get_or_create_supplier_for_caregiver(self.caregiver)
        self.assertEqual(first.id, second.id)
        self.assertEqual(ServiceSupplier.objects.count(), 1)

    def test_creates_supplier_for_organization(self):
        supplier = get_or_create_supplier_for_organization(self.organization)
        self.assertEqual(supplier.linked_entity_id, self.organization.id)
        self.assertEqual(supplier.linked_entity_type, ORGANIZATION_LINKED_TYPE)
        self.assertEqual(supplier.supplier_type, SupplierType.ORGANIZATION)
        self.assertEqual(supplier.tenant_id, self.organization.tenant_id)

    def test_resolve_supplier_entity_roundtrip_caregiver(self):
        supplier = get_or_create_supplier_for_caregiver(self.caregiver)
        resolved = resolve_supplier_entity(supplier)
        self.assertEqual(resolved, self.caregiver)

    def test_resolve_supplier_entity_roundtrip_organization(self):
        supplier = get_or_create_supplier_for_organization(self.organization)
        resolved = resolve_supplier_entity(supplier)
        self.assertEqual(resolved, self.organization)

    def test_kernel_supplier_module_stays_generic(self):
        """Kernel's ServiceSupplier model/registry/resolver must not import apps.accounts."""
        from apps.kernel.models import supplier as kernel_supplier_module

        self.assertFalse(_module_imports_accounts(kernel_supplier_module))
        self.assertFalse(_module_imports_accounts(supplier_registry))
        self.assertFalse(_module_imports_accounts(supplier_resolver))

    def test_bridge_never_touches_serviceSupplier_objects_directly(self):
        """Accounts must never create/query ServiceSupplier directly — only via SupplierRegistry."""
        from apps.accounts.services import supplier_bridge

        source = inspect.getsource(supplier_bridge)
        self.assertNotIn("ServiceSupplier.objects", source)


class OrganizationProviderActivationTest(TestCase):
    """Epic 04 Sprint 3 (Provider Affiliation Activation)."""

    def setUp(self):
        self.tenant = TenantService.get_default_tenant()
        self.person = Person.objects.create(tenant=self.tenant, full_name="Affiliated Caregiver")
        self.user = UserAccount.objects.create_user(phone="09140000010", person=self.person, tenant=self.tenant)

    def _create_caregiver(self, *, provider_type):
        from apps.accounts.models.profiles import CaregiverProviderType

        return CaregiverProfile.objects.create(
            user=self.user, person=self.person, phone="09140000010", display_name="Affiliated Caregiver",
            provider_type=provider_type,
        )

    def test_independent_caregiver_still_gets_independent_provider_supplier(self):
        from apps.accounts.models.profiles import CaregiverProviderType

        caregiver = self._create_caregiver(provider_type=CaregiverProviderType.INDEPENDENT)
        supplier = get_or_create_supplier_for_caregiver(caregiver)
        self.assertEqual(supplier.supplier_type, SupplierType.INDEPENDENT_PROVIDER)

    def test_organization_affiliated_caregiver_gets_organization_provider_supplier(self):
        from apps.accounts.models.profiles import CaregiverProviderType

        caregiver = self._create_caregiver(provider_type=CaregiverProviderType.ORGANIZATION_AFFILIATED)
        supplier = get_or_create_supplier_for_caregiver(caregiver)
        self.assertEqual(supplier.supplier_type, SupplierType.ORGANIZATION_PROVIDER)

    def test_approve_affiliation_request_produces_organization_provider_supplier(self):
        """End-to-end through the real approval flow, not a direct field set."""
        from apps.accounts.models.profiles import CompanyAffiliationRequest, OrganizationMembership
        from apps.accounts.services.affiliations import approve_affiliation_request
        from apps.accounts.services.organizations import find_organization_by_code_or_name

        caregiver = self._create_caregiver(provider_type="independent")
        org_admin_person = Person.objects.create(tenant=self.tenant, full_name="Org Admin")
        org_admin = UserAccount.objects.create_user(phone="09140000011", person=org_admin_person, tenant=self.tenant)
        organization = OrganizationProfile.objects.create(
            name="Affil Co", code="AFFIL-CO-1", admin_user=org_admin, tenant=self.tenant,
        )
        request = CompanyAffiliationRequest.objects.create(
            caregiver_profile=caregiver, requested_company_name_or_code="AFFIL-CO-1", organization=organization,
        )

        approve_affiliation_request(request_id=request.id, reviewed_by=org_admin)
        caregiver.refresh_from_db()

        supplier = get_or_create_supplier_for_caregiver(caregiver)
        self.assertEqual(supplier.supplier_type, SupplierType.ORGANIZATION_PROVIDER)
        self.assertTrue(
            OrganizationMembership.objects.filter(organization=organization, user=self.user).exists(),
        )


class ReconcileOrganizationProviderSuppliersTest(TestCase):
    def setUp(self):
        from apps.accounts.models.profiles import CaregiverProviderType

        self.tenant = TenantService.get_default_tenant()
        self.person = Person.objects.create(tenant=self.tenant, full_name="Legacy Affiliated Caregiver")
        self.user = UserAccount.objects.create_user(phone="09140000020", person=self.person, tenant=self.tenant)
        # Simulates a caregiver who was already ORGANIZATION_AFFILIATED
        # BEFORE the supplier_bridge branch existed: their supplier was
        # created as INDEPENDENT_PROVIDER and never updated.
        self.caregiver = CaregiverProfile.objects.create(
            user=self.user, person=self.person, phone="09140000020", display_name="Legacy",
            provider_type=CaregiverProviderType.INDEPENDENT,
        )
        self.supplier = get_or_create_supplier_for_caregiver(self.caregiver)
        self.caregiver.provider_type = CaregiverProviderType.ORGANIZATION_AFFILIATED
        self.caregiver.save(update_fields=["provider_type"])

    def test_reconcile_updates_existing_supplier_type(self):
        from django.core.management import call_command

        self.assertEqual(self.supplier.supplier_type, SupplierType.INDEPENDENT_PROVIDER)
        call_command("reconcile_organization_provider_suppliers")

        self.supplier.refresh_from_db()
        self.assertEqual(self.supplier.supplier_type, SupplierType.ORGANIZATION_PROVIDER)

    def test_reconcile_is_idempotent(self):
        from django.core.management import call_command

        call_command("reconcile_organization_provider_suppliers")
        call_command("reconcile_organization_provider_suppliers")

        self.supplier.refresh_from_db()
        self.assertEqual(self.supplier.supplier_type, SupplierType.ORGANIZATION_PROVIDER)
        self.assertEqual(ServiceSupplier.objects.filter(id=self.supplier.id).count(), 1)

    def test_dry_run_writes_nothing(self):
        from django.core.management import call_command

        call_command("reconcile_organization_provider_suppliers", "--dry-run")
        self.supplier.refresh_from_db()
        self.assertEqual(self.supplier.supplier_type, SupplierType.INDEPENDENT_PROVIDER)
