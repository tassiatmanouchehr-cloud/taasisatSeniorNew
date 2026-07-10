"""Order-history filter tabs — Customer Experience Phase 2 (Epic 02)."""

import uuid

from apps.kernel.models.supplier import AvailabilityStatus, ServiceSupplier, SupplierStatus, SupplierType, VerificationLevel
from apps.orders.services.order_creation import create_public_order
from apps.orders.services.status_machine import approve_public_order, complete_order, start_order

from .helpers import PortalTestCase


class RequestsListFilterTest(PortalTestCase):
    def setUp(self):
        super().setUp()
        self.login_as_customer()

        self.active_order = create_public_order(
            service_category_id=self.category.id, description="active", phone="0912",
            address="addr", city="tehran", customer_profile=self.customer,
            elder_profile=self.care_recipient, created_by=self.customer.user, tenant_id=self.tenant.id,
        )

        supplier = ServiceSupplier.objects.create(
            tenant_id=self.tenant.id, supplier_type=SupplierType.INDEPENDENT_PROVIDER,
            linked_entity_id=uuid.uuid4(), linked_entity_type="TestProfile", display_name="Supplier",
            status=SupplierStatus.ACTIVE, availability_status=AvailabilityStatus.AVAILABLE,
            verification_level=VerificationLevel.BASIC, service_categories=[str(self.category.id)],
        )
        completed = create_public_order(
            service_category_id=self.category.id, description="completed", phone="0912",
            address="addr", city="tehran", customer_profile=self.customer,
            elder_profile=self.care_recipient, created_by=self.customer.user, tenant_id=self.tenant.id,
        )
        approve_public_order(order_id=completed.id, reviewed_by=self.customer.user, assigned_supplier=supplier)
        start_order(order_id=completed.id, changed_by=self.customer.user)
        self.completed_order = complete_order(order_id=completed.id, changed_by=self.customer.user)

    def test_all_shows_every_order(self):
        response = self.client.get("/portal/requests/")
        self.assertEqual(len(response.context["orders"]), 2)

    def test_active_filter_excludes_completed(self):
        response = self.client.get("/portal/requests/?filter=active")
        orders = list(response.context["orders"])
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0].id, self.active_order.id)

    def test_completed_filter_only_shows_completed(self):
        response = self.client.get("/portal/requests/?filter=completed")
        orders = list(response.context["orders"])
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0].id, self.completed_order.id)

    def test_unknown_filter_value_falls_back_to_all(self):
        response = self.client.get("/portal/requests/?filter=bogus")
        self.assertEqual(len(response.context["orders"]), 2)
