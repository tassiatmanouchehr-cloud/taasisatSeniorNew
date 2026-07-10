"""Shared fixtures for provider portal tests (not a test module itself)."""

import uuid

from django.test import TestCase

from apps.accounts.models.profiles import CaregiverProfile, CustomerProfile
from apps.accounts.services.care_recipients import CareRecipientService
from apps.accounts.services.provider_identity import resolve_supplier_for_user
from apps.kernel.models import Person, Tenant, UserAccount
from apps.orders.models import CatalogStatus, ServiceCategory
from apps.orders.services.order_creation import create_public_order


class ProviderPortalTestCase(TestCase):
    """Base test case: a tenant, a logged-in provider, a customer, and an order."""

    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"provportal-{uuid.uuid4().hex[:8]}", name="Provider Portal Tenant")
        self.other_tenant = Tenant.objects.create(slug=f"provportal-other-{uuid.uuid4().hex[:8]}", name="Other Tenant")

        self.category = ServiceCategory.objects.create(
            tenant=self.tenant, name="Home Care", slug="home-care", status=CatalogStatus.ACTIVE,
        )

        self.provider_user, self.supplier = self._create_provider(tenant=self.tenant)
        self.other_provider_user, self.other_supplier = self._create_provider(
            tenant=self.tenant, phone="09129990001",
        )

        self.customer = self._create_customer(tenant=self.tenant)
        self.care_recipient = CareRecipientService.create(customer_profile=self.customer, full_name="مادر بزرگ")

        self.order = create_public_order(
            service_category_id=self.category.id, description="x", phone="0912",
            address="addr", city="tehran", customer_profile=self.customer,
            elder_profile=self.care_recipient, created_by=self.customer.user, tenant_id=self.tenant.id,
        )

    def _create_provider(self, *, tenant, phone=None):
        phone = phone or f"0912{uuid.uuid4().hex[:7]}"
        person = Person.objects.create(tenant=tenant, full_name="Provider")
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)
        CaregiverProfile.objects.create(user=user, person=person, phone=phone, display_name="Test Provider")
        supplier = resolve_supplier_for_user(user)
        return user, supplier

    def _create_customer(self, *, tenant, phone=None) -> CustomerProfile:
        phone = phone or f"0912{uuid.uuid4().hex[:7]}"
        person = Person.objects.create(tenant=tenant, full_name="Customer")
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)
        return CustomerProfile.objects.create(user=user, person=person, phone=phone, display_name="Customer")

    def login_as_provider(self):
        self.client.force_login(self.provider_user)

    def assign_order_to_supplier(self):
        from apps.booking.services.assignment_service import AssignmentService

        return AssignmentService.assign(order_id=self.order.id, supplier=self.supplier)
