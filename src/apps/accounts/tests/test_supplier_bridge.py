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
