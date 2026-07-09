"""Shared fixtures for admin portal tests (not a test module itself)."""

import uuid

from django.test import TestCase

from apps.accounts.models.profiles import CustomerProfile
from apps.kernel.models import Person, Tenant, UserAccount
from apps.kernel.models.supplier import (
    AvailabilityStatus,
    ServiceSupplier,
    SupplierStatus,
    SupplierType,
    VerificationLevel,
)
from apps.kernel.tests.rbac_helpers import grant_permissions
from apps.orders.models import CatalogStatus, Order, OrderSource, OrderStatus, ServiceCategory


class AdminPortalTestCase(TestCase):
    """Base test case: a tenant, an order, a supplier, and an actor with no permissions yet."""

    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"admin-{uuid.uuid4().hex[:8]}", name="Admin Portal Test Tenant")
        self.other_tenant = Tenant.objects.create(slug=f"admin-other-{uuid.uuid4().hex[:8]}", name="Other Tenant")

        self.category = ServiceCategory.objects.create(
            tenant=self.tenant, name="Home Care", slug="home-care", status=CatalogStatus.ACTIVE,
        )
        self.customer_profile = self._create_customer(tenant=self.tenant)
        self.supplier = self._create_supplier(tenant=self.tenant)
        self.order = Order.objects.create(
            tenant=self.tenant, source=OrderSource.OPERATOR, status=OrderStatus.NEW,
            service_category=self.category, customer_profile=self.customer_profile,
            description="Need home care", city="tehran", address="Some address", phone="09120000000",
        )

        self.actor = self._create_actor(tenant=self.tenant)

    def _create_customer(self, *, tenant, display_name="Test Customer", phone=None) -> CustomerProfile:
        phone = phone or f"0912{uuid.uuid4().hex[:7]}"
        person = Person.objects.create(tenant=tenant, full_name=display_name)
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)
        return CustomerProfile.objects.create(
            user=user, person=person, phone=phone, display_name=display_name,
        )

    def _create_supplier(self, *, tenant, **kwargs) -> ServiceSupplier:
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

    def _create_actor(self, *, tenant, phone=None, full_name="Admin Portal Test Actor") -> UserAccount:
        phone = phone or f"0912{uuid.uuid4().hex[:7]}"
        person = Person.objects.create(tenant=tenant, full_name=full_name)
        return UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)

    def _grant(self, user, tenant, permission_keys):
        return grant_permissions(tenant, user, permission_keys)
