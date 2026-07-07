"""
Tests establishing ServiceSupplier (assigned_supplier) as the single source
of truth for Order assignment.

Covers:
- Order has no writable assigned_provider/assigned_organization DB fields.
- assigned_provider/assigned_organization are read-only computed properties.
- assign_supplier/remove_supplier/replace_supplier operate on assigned_supplier only.
"""

from django.test import TestCase

from apps.accounts.models.profiles import CaregiverProfile, OrganizationProfile
from apps.accounts.services.supplier_bridge import (
    get_or_create_supplier_for_caregiver,
    get_or_create_supplier_for_organization,
)
from apps.kernel.models import Person, UserAccount
from apps.kernel.services.tenant_service import TenantService
from apps.orders.models import CatalogStatus, Order, ServiceCategory
from apps.orders.services.order_creation import create_operator_order
from apps.orders.services.status_machine import assign_supplier, remove_supplier, replace_supplier


class SupplierAssignmentTest(TestCase):
    def setUp(self):
        self.tenant = TenantService.get_default_tenant()
        self.category = ServiceCategory.objects.create(
            tenant_id=self.tenant.id, name="Cat", slug="supplier-assign-cat", status=CatalogStatus.ACTIVE,
        )

        person = Person.objects.create(tenant=self.tenant, full_name="CG")
        user = UserAccount.objects.create_user(phone="09150000001", person=person, tenant=self.tenant)
        self.caregiver = CaregiverProfile.objects.create(
            user=user, person=person, phone="09150000001", display_name="CG",
        )
        self.supplier = get_or_create_supplier_for_caregiver(self.caregiver, tenant_id=self.tenant.id)

        admin_person = Person.objects.create(tenant=self.tenant, full_name="Org Admin")
        admin_user = UserAccount.objects.create_user(
            phone="09150000002", person=admin_person, tenant=self.tenant,
        )
        self.organization = OrganizationProfile.objects.create(
            name="Org", code="ORG-SUPP1", admin_user=admin_user, tenant=self.tenant,
        )
        self.org_supplier = get_or_create_supplier_for_organization(self.organization, tenant_id=self.tenant.id)

    def _make_order(self, **overrides):
        defaults = dict(
            service_category_id=self.category.id, description="x", phone="09121111111",
            address="addr", tenant_id=self.tenant.id,
        )
        defaults.update(overrides)
        return create_operator_order(**defaults)

    def test_order_has_no_writable_legacy_assignment_fields(self):
        field_names = {f.name for f in Order._meta.get_fields()}
        self.assertNotIn("assigned_provider", field_names)
        self.assertNotIn("assigned_organization", field_names)
        self.assertIn("assigned_supplier", field_names)

    def test_assigned_provider_and_organization_are_properties(self):
        self.assertIsInstance(Order.assigned_provider, property)
        self.assertIsInstance(Order.assigned_organization, property)

    def test_assign_supplier_sets_assigned_supplier(self):
        order = self._make_order()
        order = assign_supplier(order_id=order.id, supplier=self.supplier)
        order.refresh_from_db()
        self.assertEqual(order.assigned_supplier_id, self.supplier.id)

    def test_assigned_provider_property_resolves_caregiver(self):
        order = self._make_order(assigned_supplier=self.supplier)
        self.assertEqual(order.assigned_provider, self.caregiver)
        self.assertIsNone(order.assigned_organization)

    def test_assigned_organization_property_resolves_organization(self):
        order = self._make_order(assigned_supplier=self.org_supplier)
        self.assertEqual(order.assigned_organization, self.organization)
        self.assertIsNone(order.assigned_provider)

    def test_remove_supplier_clears_assignment(self):
        order = self._make_order(assigned_supplier=self.supplier)
        order = remove_supplier(order_id=order.id)
        self.assertIsNone(order.assigned_supplier)
        self.assertIsNone(order.assigned_provider)

    def test_replace_supplier_switches_assignment(self):
        order = self._make_order(assigned_supplier=self.supplier)
        order = replace_supplier(order_id=order.id, new_supplier=self.org_supplier)
        self.assertEqual(order.assigned_supplier_id, self.org_supplier.id)
        self.assertEqual(order.assigned_organization, self.organization)
