"""CaregiverPublicProfileService — Epic 06."""

import uuid

from apps.kernel.models.supplier import SupplierStatus

from ..services.profile_service import CaregiverPublicProfileService
from .helpers import PublicSiteTestCase


class ProfileServiceTest(PublicSiteTestCase):
    def test_returns_none_for_unknown_supplier(self):
        self.assertIsNone(CaregiverPublicProfileService.get_profile(uuid.uuid4(), tenant_id=self.tenant.id))

    def test_returns_none_for_suspended_supplier(self):
        supplier, _ = self._create_caregiver_supplier(supplier_status=SupplierStatus.SUSPENDED)
        self.assertIsNone(CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id))

    def test_returns_none_for_archived_caregiver_profile(self):
        supplier, _ = self._create_caregiver_supplier(profile_status="archived")
        self.assertIsNone(CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id))

    def test_returns_none_across_tenants(self):
        from apps.kernel.models import Tenant

        supplier, _ = self._create_caregiver_supplier()
        other_tenant = Tenant.objects.create(slug="other-profile-tenant", name="Other")

        self.assertIsNone(CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=other_tenant.id))

    def test_full_profile_fields_are_populated_from_real_data(self):
        supplier, _ = self._create_caregiver_supplier(
            display_name="مریم احمدی",
            city="tehran",
            specialty="پرستار",
            bio="با سال‌ها تجربه",
            years_experience=6,
            service_radius_km=15,
            verification_status="verified",
        )

        profile = CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id)

        self.assertEqual(profile.display_name, "مریم احمدی")
        self.assertEqual(profile.city, "tehran")
        self.assertEqual(profile.specialty, "پرستار")
        self.assertEqual(profile.bio, "با سال‌ها تجربه")
        self.assertEqual(profile.years_experience, 6)
        self.assertEqual(profile.service_radius_km, 15)
        self.assertTrue(profile.is_verified)
        self.assertEqual(profile.verification_status, "verified")

    def test_service_names_resolved_from_supplier_service_categories(self):
        supplier, _ = self._create_caregiver_supplier()

        profile = CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id)

        self.assertIn(self.category.name, profile.service_names)

    def test_completed_jobs_counted(self):
        supplier, _ = self._create_caregiver_supplier()
        self._create_completed_order(supplier=supplier)

        profile = CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id)

        self.assertEqual(profile.completed_jobs, 1)

    def test_only_approved_reviews_are_shown(self):
        supplier, _ = self._create_caregiver_supplier()
        self._add_approved_review(supplier=supplier, text="نظر تأییدشده")
        self._add_pending_review(supplier=supplier, text="نظر در انتظار")

        profile = CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id)

        review_texts = [review.written_text for review in profile.reviews]
        self.assertIn("نظر تأییدشده", review_texts)
        self.assertNotIn("نظر در انتظار", review_texts)

    def test_no_private_document_fields_leak_into_the_viewmodel(self):
        """The Epic's explicit requirement: only a verification *status*
        label may ever be shown — never document metadata."""
        supplier, _ = self._create_caregiver_supplier(verification_status="verified")

        profile = CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id)

        viewmodel_fields = {f.name for f in profile.__dataclass_fields__.values()}
        for forbidden in ("document", "file", "attachment", "national_id", "id_card"):
            self.assertFalse(
                any(forbidden in field_name for field_name in viewmodel_fields),
                f"CaregiverProfileViewModel unexpectedly exposes a field matching '{forbidden}'",
            )
