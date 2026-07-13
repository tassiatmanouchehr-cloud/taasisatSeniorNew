"""Shared fixtures for apps.commission tests (not a test module itself)."""

import uuid

from django.test import TestCase

from apps.accounts.models.profiles import (
    CaregiverProfile,
    CaregiverProviderType,
    OrganizationMembership,
    OrganizationProfile,
    OrgMembershipRole,
    OrgMembershipStatus,
)
from apps.accounts.services.supplier_bridge import (
    get_or_create_supplier_for_caregiver,
    get_or_create_supplier_for_organization,
)
from apps.kernel.models import Person, Tenant, UserAccount
from apps.kernel.models.configuration import ConfigurationKey, ConfigurationValue, ScopeLevel, ValueType
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

    def _enable_deadline_activation(self, *, tenant=None):
        """Remediation 6 (System Architect Review of PR #44): the deadline
        activation gate defaults to DISABLED for every tenant. Tests that
        exercise the actual expiry mechanism (job scheduling, expire_due()
        cascading to AssignmentService.expire(), extension rescheduling)
        must explicitly enable it — mirrors the established
        booking.reassignment.enabled / booking.assignment.auto_accept_enabled
        test pattern (apps.booking.tests.test_replace_cancel /
        test_assignment_service)."""
        from apps.commission.services.configuration import DEADLINE_ACTIVATION_ENABLED_KEY

        tenant = tenant or self.tenant
        config_key, _ = ConfigurationKey.objects.get_or_create(
            key=DEADLINE_ACTIVATION_ENABLED_KEY,
            defaults={
                "owner_module": "M05",
                "scope_level": ScopeLevel.TENANT,
                "value_type": ValueType.BOOLEAN,
                "default_value": False,
            },
        )
        ConfigurationValue.objects.update_or_create(
            tenant_id=tenant.id,
            config_key=config_key,
            scope_type=ScopeLevel.TENANT,
            defaults={"value": True, "is_active": True},
        )

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

    def _make_affiliated_caregiver(self, *, tenant=None, membership_status=OrgMembershipStatus.ACTIVE):
        """Returns (caregiver_supplier, company_supplier, organization_profile, caregiver_user)."""
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
            status=membership_status,
        )

        return caregiver_supplier, organization_supplier, organization, cg_user
