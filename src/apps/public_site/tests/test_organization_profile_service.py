"""OrganizationPublicProfileService — Epic 06 Sprint 2."""

import uuid

from apps.accounts.models.profiles import OrganizationProfile
from apps.accounts.services.supplier_bridge import get_or_create_supplier_for_organization
from apps.kernel.models import Person, UserAccount
from apps.kernel.models.supplier import SupplierStatus

from ..services.organization_profile_service import OrganizationPublicProfileService
from .helpers import PublicSiteTestCase


class OrganizationPublicProfileServiceTest(PublicSiteTestCase):
    def _create_organization_supplier(self, *, name="سازمان نمونه", status="active"):
        admin_person = Person.objects.create(tenant=self.tenant, full_name="مدیر سازمان")
        admin_user = UserAccount.objects.create_user(
            phone=f"0913{uuid.uuid4().hex[:7]}",
            person=admin_person,
            tenant=self.tenant,
        )
        organization = OrganizationProfile.objects.create(
            name=name,
            code=f"org-{uuid.uuid4().hex[:8]}",
            admin_user=admin_user,
            tenant=self.tenant,
            status=status,
        )
        supplier = get_or_create_supplier_for_organization(organization, tenant_id=self.tenant.id)
        supplier.status = SupplierStatus.ACTIVE
        supplier.service_categories = [str(self.category.id)]
        supplier.save(update_fields=["status", "service_categories"])
        return supplier, organization

    def test_returns_none_for_unknown_supplier(self):
        self.assertIsNone(OrganizationPublicProfileService.get_profile(uuid.uuid4(), tenant_id=self.tenant.id))

    def test_returns_none_for_inactive_organization(self):
        supplier, _ = self._create_organization_supplier(status="archived")
        self.assertIsNone(OrganizationPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id))

    def test_returns_none_for_suspended_supplier(self):
        supplier, _ = self._create_organization_supplier()
        supplier.status = SupplierStatus.SUSPENDED
        supplier.save(update_fields=["status"])
        self.assertIsNone(OrganizationPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id))

    def test_full_profile_fields_populated(self):
        supplier, organization = self._create_organization_supplier(name="سازمان مراقبت آفتاب")
        profile = OrganizationPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id)
        self.assertIsNotNone(profile)
        self.assertEqual(profile.name, "سازمان مراقبت آفتاب")
        self.assertIn(self.category.name, profile.service_names)

    def test_tenant_isolation(self):
        from apps.kernel.models import Tenant

        supplier, _ = self._create_organization_supplier()
        other_tenant = Tenant.objects.create(slug="other-org-profile-tenant", name="Other")
        self.assertIsNone(OrganizationPublicProfileService.get_profile(supplier.id, tenant_id=other_tenant.id))

    def test_no_staff_or_internal_fields_leak_into_the_viewmodel(self):
        supplier, _ = self._create_organization_supplier()
        profile = OrganizationPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id)
        field_names = {f.name for f in profile.__dataclass_fields__.values()}
        for forbidden in ("staff", "membership", "document", "admin_user", "phone", "address", "code"):
            self.assertFalse(any(forbidden in name for name in field_names))
