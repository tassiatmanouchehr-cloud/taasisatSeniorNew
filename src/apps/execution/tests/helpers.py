"""Shared fixtures for execution engine tests (not a test module itself)."""

import uuid

from django.test import TestCase

from apps.booking.services.assignment_service import AssignmentService
from apps.kernel.models import Tenant
from apps.kernel.models.supplier import (
    AvailabilityStatus,
    ServiceSupplier,
    SupplierStatus,
    SupplierType,
    VerificationLevel,
)
from apps.orders.models import CatalogStatus, Order, OrderSource, OrderStatus, ServiceCategory


class ExecutionTestCase(TestCase):
    """Base test case providing a tenant, order, supplier, and a confirmed SupplierAssignment."""

    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"execution-{uuid.uuid4().hex[:8]}", name="Execution Test Tenant")
        self.other_tenant = Tenant.objects.create(slug=f"execution-other-{uuid.uuid4().hex[:8]}", name="Other Tenant")

        self.category = ServiceCategory.objects.create(
            tenant=self.tenant, name="Home Care", slug="home-care", status=CatalogStatus.ACTIVE,
        )

        self.order = Order.objects.create(
            tenant=self.tenant,
            source=OrderSource.OPERATOR,
            status=OrderStatus.NEW,
            service_category=self.category,
            description="Need home care",
            city="tehran",
            address="Some address",
            phone="09120000000",
        )

        self.supplier = self._create_supplier()
        # assign() transitions Order -> waiting_service and returns a SupplierAssignment
        # whose status is ASSIGNED (auto_accept defaults to False).
        self.supplier_assignment = AssignmentService.assign(order_id=self.order.id, supplier=self.supplier)

    def _create_supplier(self, *, tenant=None, **kwargs) -> ServiceSupplier:
        tenant = tenant or self.tenant
        defaults = {
            "tenant_id": tenant.id,
            "supplier_type": SupplierType.INDEPENDENT_PROVIDER,
            "linked_entity_id": uuid.uuid4(),
            "linked_entity_type": "TestProfile",
            "display_name": "Test Supplier",
            "status": SupplierStatus.ACTIVE,
            "availability_status": AvailabilityStatus.AVAILABLE,
            "verification_level": VerificationLevel.BASIC,
            "service_categories": [str(self.category.id)],
        }
        defaults.update(kwargs)
        return ServiceSupplier.objects.create(**defaults)
