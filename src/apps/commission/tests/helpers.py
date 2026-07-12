"""Shared fixtures for apps.commission tests (not a test module itself)."""

import uuid

from django.test import TestCase

from apps.accounts.models.profiles import (
    AffiliationStatus,
    CaregiverProfile,
    CaregiverProviderType,
    OrganizationMembership,
    OrganizationProfile,
    OrgMembershipRole,
)
from apps.accounts.services.supplier_bridge import (
    get_or_create_supplier_for_caregiver,
    get_or_create_supplier_for_organization,
)
from apps.kernel.models import Person, Tenant, UserAccount
from apps.kernel.models.supplier import (
    AvailabilityStatus,
    ServiceSupplier,
    SupplierStatus,
    SupplierType,
    VerificationLevel,
)
from apps.orders.models import CatalogStatus, Order, OrderSource, OrderStatus, ServiceCategory


class CommissionTestCase(TestCase):
    """Base test case: a tenant, an order, and independent/affiliated/company suppliers."""

    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"comm-{uuid.uuid4().hex[:8]}", name="Commission Test Tenant")
        self.other_tenant = Tenant.objects.create(slug=f"comm-other-{uuid.uuid4().hex[:8]}", name="Other Tenant")
        self.category = ServiceCategory.objects.create(
            tenant=self.tenant,
            name="Home Care",
            slug=f"home-care-{uuid.uuid4().hex[:6]}",
            status=CatalogStatus.ACTIVE,
        )

    def _make_order(self, *, tenant=None):
        tenant = tenant or self.tenant
        customer = self._create_customer(tenant=tenant)
        return Order.objects.create(
            tenant=tenant,
            source=OrderSource.OPERATOR,
            status=OrderStatus.NEW,
            service_category=self.category,
            customer_profile=customer,
            description="Commission test order",
            city="tehran",
            address="Addr",
            phone="09120000000",
        )

    def _create_customer(self, *, tenant):
        from apps.accounts.models.profiles import CustomerProfile

        phone = f"0912{uuid.uuid4().hex[:7]}"
        person = Person.objects.create(tenant=tenant, full_name="Test Customer")
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)
        return CustomerProfile.objects.create(user=user, person=person, phone=phone, display_name="Test Customer")

    def _make_independent_supplier(self, *, tenant=None) -> ServiceSupplier:
        tenant = tenant or self.tenant
        return ServiceSupplier.objects.create(
            tenant_id=tenant.id,
            supplier_type=SupplierType.INDEPENDENT_PROVIDER,
            linked_entity_id=uuid.uuid4(),
            linked_entity_type="TestProfile",
            display_name="Independent Caregiver",
            status=SupplierStatus.ACTIVE,
            availability_status=AvailabilityStatus.AVAILABLE,
            verification_level=VerificationLevel.BASIC,
            service_categories=[str(self.category.id)],
        )

    def _make_company_supplier(self, *, tenant=None) -> ServiceSupplier:
        tenant = tenant or self.tenant
        return ServiceSupplier.objects.create(
            tenant_id=tenant.id,
            supplier_type=SupplierType.ORGANIZATION,
            linked_entity_id=uuid.uuid4(),
            linked_entity_type="TestOrg",
            display_name="Test Company",
            status=SupplierStatus.ACTIVE,
            availability_status=AvailabilityStatus.AVAILABLE,
            verification_level=VerificationLevel.BASIC,
            service_categories=[str(self.category.id)],
        )

    def _make_affiliated_caregiver(self, *, tenant=None):
        """Returns (caregiver_supplier, company_supplier, organization_profile)."""
        tenant = tenant or self.tenant

        org_phone = f"0912{uuid.uuid4().hex[:7]}"
        org_person = Person.objects.create(tenant=tenant, full_name="Test Org Owner")
        org_user = UserAccount.objects.create_user(phone=org_phone, person=org_person, tenant=tenant)
        organization = OrganizationProfile.objects.create(
            name="Test Organization",
            code=f"org-{uuid.uuid4().hex[:8]}",
            admin_user=org_user,
            tenant=tenant,
        )
        organization_supplier = get_or_create_supplier_for_organization(organization, tenant_id=tenant.id)

        cg_phone = f"0912{uuid.uuid4().hex[:7]}"
        cg_person = Person.objects.create(tenant=tenant, full_name="Test Affiliated Caregiver")
        cg_user = UserAccount.objects.create_user(phone=cg_phone, person=cg_person, tenant=tenant)
        caregiver = CaregiverProfile.objects.create(
            user=cg_user,
            person=cg_person,
            phone=cg_phone,
            display_name="Test Affiliated Caregiver",
            provider_type=CaregiverProviderType.ORGANIZATION_AFFILIATED,
        )
        caregiver_supplier = get_or_create_supplier_for_caregiver(caregiver, tenant_id=tenant.id)

        OrganizationMembership.objects.create(
            organization=organization,
            user=cg_user,
            person=cg_person,
            role_type=OrgMembershipRole.CAREGIVER,
            status=AffiliationStatus.APPROVED,
        )

        return caregiver_supplier, organization_supplier, organization
