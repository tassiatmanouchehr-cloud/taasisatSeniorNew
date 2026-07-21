"""
Tests for Sprint 3A tenant isolation across the catalog and order models.

Covers:
- ServiceCategory/ServiceType uniqueness is tenant-scoped, not global.
- Catalog validation during order creation is tenant-scoped (cross-tenant
  category/type ids are rejected as if they did not exist).
- OrderStatusHistory inherits and is queryable by its order's tenant.
"""

from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.kernel.models import Tenant
from apps.orders.models import CatalogStatus, OrderStatusHistory, ServiceCategory, ServiceType
from apps.orders.services.order_creation import OrderValidationError, create_public_order


class TenantIsolationTest(TestCase):
    def setUp(self):
        self.tenant_a = Tenant.objects.create(slug="tenant-a", name="Tenant A")
        self.tenant_b = Tenant.objects.create(slug="tenant-b", name="Tenant B")

        self.cat_a = ServiceCategory.objects.create(
            tenant_id=self.tenant_a.id,
            name="Care A",
            slug="care",
            status=CatalogStatus.ACTIVE,
        )
        self.cat_b = ServiceCategory.objects.create(
            tenant_id=self.tenant_b.id,
            name="Care B",
            slug="care",
            status=CatalogStatus.ACTIVE,
        )

    def _order_kwargs(self, **overrides):
        defaults = dict(
            service_category_id=self.cat_a.id,
            description="Test order",
            phone="09121111111",
            address="Test address",
            tenant_id=self.tenant_a.id,
        )
        defaults.update(overrides)
        return defaults

    def test_same_slug_allowed_across_tenants(self):
        # Both categories use slug="care" but belong to different tenants — no clash.
        self.assertEqual(ServiceCategory.objects.filter(slug="care").count(), 2)

    def test_duplicate_slug_same_tenant_rejected(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            ServiceCategory.objects.create(
                tenant_id=self.tenant_a.id,
                name="Dup",
                slug="care",
                status=CatalogStatus.ACTIVE,
            )

    def test_order_creation_scopes_to_requested_tenant(self):
        order = create_public_order(**self._order_kwargs())
        self.assertEqual(order.tenant_id, self.tenant_a.id)

    def test_cross_tenant_category_rejected(self):
        with self.assertRaises(OrderValidationError):
            create_public_order(**self._order_kwargs(service_category_id=self.cat_b.id))

    def test_cross_tenant_service_type_rejected(self):
        type_b = ServiceType.objects.create(
            tenant_id=self.tenant_b.id,
            category=self.cat_b,
            name="T",
            slug="t",
            status=CatalogStatus.ACTIVE,
        )
        with self.assertRaises(OrderValidationError):
            create_public_order(**self._order_kwargs(service_type_id=type_b.id))

    def test_order_status_history_inherits_tenant(self):
        order = create_public_order(**self._order_kwargs())
        history = OrderStatusHistory.objects.get(order=order)
        self.assertEqual(history.tenant_id, self.tenant_a.id)

    def test_order_status_history_for_tenant_scoping(self):
        order_a = create_public_order(**self._order_kwargs())
        order_b = create_public_order(
            **self._order_kwargs(service_category_id=self.cat_b.id, tenant_id=self.tenant_b.id)
        )
        history_a_order_ids = set(
            OrderStatusHistory.objects.for_tenant(self.tenant_a.id).values_list("order_id", flat=True)
        )
        self.assertIn(order_a.id, history_a_order_ids)
        self.assertNotIn(order_b.id, history_a_order_ids)
