"""OrganizationPublicProfileService — Epic 06 Sprint 2.

Phase 3 Sprint 3.2 (Company Professional Profile and Public Presence)
remediation: `_create_organization_supplier()` now defaults
`verification_status="verified"` and `admin_is_active=True` — a real,
publicly-visible organization must satisfy the same canonical
`common.is_publicly_visible_attrs()` rule the caregiver public-profile
fixtures already assume by default (see
`apps.public_site.tests.helpers.PublicSiteTestCase._create_caregiver_supplier()`'s
own `verification_status="verified"` default). Before this remediation,
`get_profile()` only checked `profile_status`, so every test below
happened to pass against an UNVERIFIED fixture — masking the fact that an
unverified (or admin-deactivated) organization was incorrectly public."""

import io
import uuid

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.accounts.models.profiles import OrganizationProfile, VerificationStatus
from apps.accounts.services.supplier_bridge import get_or_create_supplier_for_organization
from apps.kernel.models import Person, UserAccount
from apps.kernel.models.supplier import SupplierStatus

from ..services.organization_profile_service import OrganizationPublicProfileService
from .helpers import PublicSiteTestCase


def _png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (1, 1), color=(0, 255, 0)).save(buffer, format="PNG")
    return buffer.getvalue()


_PNG_BYTES = _png_bytes()


class OrganizationPublicProfileServiceTest(PublicSiteTestCase):
    def _create_organization_supplier(
        self,
        *,
        name="سازمان نمونه",
        status="active",
        verification_status=VerificationStatus.VERIFIED,
        admin_is_active=True,
    ):
        admin_person = Person.objects.create(tenant=self.tenant, full_name="مدیر سازمان")
        admin_user = UserAccount.objects.create_user(
            phone=f"0913{uuid.uuid4().hex[:7]}",
            person=admin_person,
            tenant=self.tenant,
        )
        if not admin_is_active:
            admin_user.is_active = False
            admin_user.save(update_fields=["is_active"])
        organization = OrganizationProfile.objects.create(
            name=name,
            code=f"org-{uuid.uuid4().hex[:8]}",
            admin_user=admin_user,
            tenant=self.tenant,
            status=status,
            verification_status=verification_status,
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

    def test_returns_none_for_unverified_organization(self):
        """PR canonical-visibility-policy fix: an ACTIVE but UNVERIFIED
        organization must not be publicly visible, matching the
        caregiver page's own established rule."""
        supplier, _ = self._create_organization_supplier(verification_status=VerificationStatus.UNVERIFIED)
        self.assertIsNone(OrganizationPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id))

    def test_returns_none_for_pending_verification_organization(self):
        supplier, _ = self._create_organization_supplier(verification_status=VerificationStatus.PENDING)
        self.assertIsNone(OrganizationPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id))

    def test_returns_none_when_admin_account_deactivated(self):
        """PR canonical-visibility-policy fix: a deactivated admin
        account must exclude the organization from public visibility,
        matching BG-022's own account_active rule for caregivers."""
        supplier, _ = self._create_organization_supplier(admin_is_active=False)
        self.assertIsNone(OrganizationPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id))

    def test_full_profile_fields_populated(self):
        supplier, organization = self._create_organization_supplier(name="سازمان مراقبت آفتاب")
        profile = OrganizationPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id)
        self.assertIsNotNone(profile)
        self.assertEqual(profile.name, "سازمان مراقبت آفتاب")
        self.assertIn(self.category.name, profile.service_names)

    def test_headline_included_when_set(self):
        supplier, organization = self._create_organization_supplier()
        organization.headline = "بیش از ۱۰ سال تجربه در مراقبت سالمندان"
        organization.save(update_fields=["headline"])
        profile = OrganizationPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id)
        self.assertEqual(profile.headline, "بیش از ۱۰ سال تجربه در مراقبت سالمندان")

    def test_logo_url_exposed_when_logo_present(self):
        """PR #13 remediation: a publicly eligible organization's existing
        logo is exposed through the public ViewModel via the field's own
        storage-URL abstraction — never a filesystem path."""
        supplier, organization = self._create_organization_supplier()
        organization.logo.save(
            "logo.png", SimpleUploadedFile("logo.png", _PNG_BYTES, content_type="image/png"), save=True
        )
        profile = OrganizationPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id)
        self.assertIsNotNone(profile)
        self.assertTrue(profile.logo_url)
        self.assertEqual(profile.logo_url, organization.logo.url)
        self.assertNotEqual(profile.logo_url, organization.logo.path)
        self.assertNotIn(str(organization.pk), profile.logo_url)

    def test_logo_url_empty_when_no_logo(self):
        """No logo uploaded — logo_url is empty, template falls back to
        the initials avatar via the component's own existing fallback
        condition (no special-casing needed here)."""
        supplier, organization = self._create_organization_supplier()
        self.assertFalse(organization.logo)
        profile = OrganizationPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id)
        self.assertIsNotNone(profile)
        self.assertEqual(profile.logo_url, "")

    def test_logo_does_not_bypass_visibility_policy_when_unverified(self):
        """A logo must never make an otherwise-ineligible organization
        publicly retrievable."""
        supplier, organization = self._create_organization_supplier(verification_status=VerificationStatus.UNVERIFIED)
        organization.logo.save(
            "logo.png", SimpleUploadedFile("logo.png", _PNG_BYTES, content_type="image/png"), save=True
        )
        self.assertIsNone(OrganizationPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id))

    def test_logo_does_not_bypass_visibility_policy_when_admin_deactivated(self):
        supplier, organization = self._create_organization_supplier(admin_is_active=False)
        organization.logo.save(
            "logo.png", SimpleUploadedFile("logo.png", _PNG_BYTES, content_type="image/png"), save=True
        )
        self.assertIsNone(OrganizationPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id))

    def test_tenant_isolation(self):
        from apps.kernel.models import Tenant

        supplier, _ = self._create_organization_supplier()
        other_tenant = Tenant.objects.create(slug="other-org-profile-tenant", name="Other")
        self.assertIsNone(OrganizationPublicProfileService.get_profile(supplier.id, tenant_id=other_tenant.id))

    def test_no_staff_or_internal_fields_leak_into_the_viewmodel(self):
        supplier, _ = self._create_organization_supplier()
        profile = OrganizationPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id)
        field_names = {f.name for f in profile.__dataclass_fields__.values()}
        for forbidden in (
            "staff",
            "membership",
            "document",
            "admin_user",
            "phone",
            "address",
            "code",
            "path",
            "storage",
        ):
            self.assertFalse(any(forbidden in name for name in field_names))
