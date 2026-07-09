"""Shared fixtures for customer portal tests (not a test module itself)."""

import uuid

from django.test import TestCase

from apps.accounts.models import CustomerProfile
from apps.accounts.services.care_recipients import CareRecipientService
from apps.kernel.models import Person, Tenant, UserAccount
from apps.orders.models import CatalogStatus, ServiceCategory


class PortalTestCase(TestCase):
    """Base test case: a tenant, a logged-in customer, and an active service category."""

    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"portal-{uuid.uuid4().hex[:8]}", name="Portal Test Tenant")
        self.other_tenant = Tenant.objects.create(slug=f"portal-other-{uuid.uuid4().hex[:8]}", name="Other Tenant")

        self.category = ServiceCategory.objects.create(
            tenant=self.tenant, name="Home Care", slug="home-care", status=CatalogStatus.ACTIVE,
        )
        self.customer = self._create_customer(tenant=self.tenant, display_name="Test Customer")
        self.other_customer = self._create_customer(tenant=self.other_tenant, display_name="Other Customer")

        self.care_recipient = CareRecipientService.create(
            customer_profile=self.customer, full_name="مادر بزرگ",
        )

    def _create_customer(self, *, tenant, display_name="Test Customer", phone=None) -> CustomerProfile:
        phone = phone or f"0912{uuid.uuid4().hex[:7]}"
        person = Person.objects.create(tenant=tenant, full_name=display_name)
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)
        return CustomerProfile.objects.create(
            user=user, person=person, phone=phone, display_name=display_name,
        )

    def login_as_customer(self):
        self.client.force_login(self.customer.user)
