"""Shared fixtures for matching engine tests (not a test module itself)."""

import uuid

from django.test import TestCase

from apps.kernel.models import Tenant
from apps.kernel.models.supplier import (
    AvailabilityStatus,
    ServiceSupplier,
    SupplierStatus,
    SupplierType,
    VerificationLevel,
)
from apps.orders.models import CatalogStatus, Order, OrderSource, OrderStatus, ServiceCategory


class MatchingTestCase(TestCase):
    """Base test case providing a tenant, a second tenant, a category, an order, and a supplier factory."""

    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"matching-{uuid.uuid4().hex[:8]}", name="Matching Test Tenant")
        self.other_tenant = Tenant.objects.create(slug=f"matching-other-{uuid.uuid4().hex[:8]}", name="Other Tenant")

        self.category = ServiceCategory.objects.create(
            tenant=self.tenant,
            name="Home Care",
            slug="home-care",
            status=CatalogStatus.ACTIVE,
        )
        self.other_category = ServiceCategory.objects.create(
            tenant=self.tenant,
            name="Physiotherapy",
            slug="physio",
            status=CatalogStatus.ACTIVE,
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

    def _create_supplier(
        self,
        *,
        tenant=None,
        supplier_type=SupplierType.INDEPENDENT_PROVIDER,
        status=SupplierStatus.ACTIVE,
        availability_status=AvailabilityStatus.AVAILABLE,
        verification_level=VerificationLevel.BASIC,
        service_categories=None,
        **kwargs,
    ) -> ServiceSupplier:
        tenant = tenant or self.tenant
        defaults = {
            "tenant_id": tenant.id,
            "supplier_type": supplier_type,
            "linked_entity_id": uuid.uuid4(),
            "linked_entity_type": "TestProfile",
            "display_name": "Test Supplier",
            "status": status,
            "availability_status": availability_status,
            "verification_level": verification_level,
            "service_categories": service_categories if service_categories is not None else [str(self.category.id)],
        }
        defaults.update(kwargs)
        return ServiceSupplier.objects.create(**defaults)
