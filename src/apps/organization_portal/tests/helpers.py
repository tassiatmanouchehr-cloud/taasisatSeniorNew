"""Shared fixtures for organization portal tests (not a test module itself)."""

import uuid

from django.test import TestCase

from apps.accounts.models.profiles import (
    CaregiverProfile,
    OrganizationMembership,
    OrganizationProfile,
    OrgMembershipRole,
    OrgMembershipStatus,
)
from apps.kernel.models import Person, Tenant, UserAccount
from apps.orders.models import CatalogStatus, ServiceCategory
from apps.orders.services.order_creation import create_public_order


class OrganizationPortalTestCase(TestCase):
    """Base test case: a tenant, an org, an admin, and one active caregiver staff member."""

    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"orgportal-{uuid.uuid4().hex[:8]}", name="Organization Portal Tenant")
        self.other_tenant = Tenant.objects.create(slug=f"orgportal-other-{uuid.uuid4().hex[:8]}", name="Other Tenant")

        self.category = ServiceCategory.objects.create(
            tenant=self.tenant, name="Home Care", slug="home-care", status=CatalogStatus.ACTIVE,
        )

        self.admin_user = self._create_user(tenant=self.tenant, phone="09121110001")
        self.organization = OrganizationProfile.objects.create(
            name="Care Co", code=f"care-{uuid.uuid4().hex[:8]}", admin_user=self.admin_user, tenant=self.tenant,
        )
        OrganizationMembership.objects.create(
            organization=self.organization, user=self.admin_user,
            role_type=OrgMembershipRole.ADMIN, status=OrgMembershipStatus.ACTIVE,
        )

        self.caregiver_user = self._create_user(tenant=self.tenant, phone="09121110002")
        CaregiverProfile.objects.create(
            user=self.caregiver_user, person=self.caregiver_user.person,
            phone="09121110002", display_name="Staff Caregiver",
        )
        self.staff_membership = OrganizationMembership.objects.create(
            organization=self.organization, user=self.caregiver_user,
            role_type=OrgMembershipRole.CAREGIVER, status=OrgMembershipStatus.ACTIVE,
        )

        self.non_admin_user = self._create_user(tenant=self.tenant, phone="09121110003")

        self.customer_user = self._create_user(tenant=self.tenant, phone="09121110004")
        from apps.accounts.models.profiles import CustomerProfile

        self.customer = CustomerProfile.objects.create(
            user=self.customer_user, person=self.customer_user.person, phone="09121110004", display_name="Customer",
        )
        from apps.accounts.services.care_recipients import CareRecipientService

        self.care_recipient = CareRecipientService.create(customer_profile=self.customer, full_name="مادر بزرگ")
        self.order = create_public_order(
            service_category_id=self.category.id, description="x", phone="0912",
            address="addr", city="tehran", customer_profile=self.customer,
            elder_profile=self.care_recipient, created_by=self.customer_user, tenant_id=self.tenant.id,
        )

    def _create_user(self, *, tenant, phone) -> UserAccount:
        person = Person.objects.create(tenant=tenant, full_name="Person")
        return UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)

    def login_as_admin(self):
        self.client.force_login(self.admin_user)
