"""Public caregiver profile: skills, experience, verified-credential
summary, and eligibility — Phase 2.1 (Caregiver Professional Profile
Foundation)."""

import datetime

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.accounts.models.media import DocumentType
from apps.accounts.services.caregiver_professional_profile_service import (
    CaregiverExperienceService,
    CaregiverSkillService,
)
from apps.accounts.services.document_service import DocumentService
from apps.accounts.services.verification_review_service import VerificationReviewService
from apps.kernel.tests.rbac_helpers import grant_permissions

from ..services.profile_service import CaregiverPublicProfileService
from .helpers import PublicSiteTestCase

PDF_BYTES = b"%PDF-1.4 fake test content"


class PublicProfileEligibilityTest(PublicSiteTestCase):
    def test_active_verified_caregiver_is_visible(self):
        supplier, _ = self._create_caregiver_supplier(verification_status="verified", profile_status="active")
        self.assertIsNotNone(CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id))

    def test_draft_caregiver_is_hidden(self):
        supplier, _ = self._create_caregiver_supplier(verification_status="verified", profile_status="draft")
        self.assertIsNone(CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id))

    def test_suspended_caregiver_is_hidden(self):
        supplier, _ = self._create_caregiver_supplier(verification_status="verified", profile_status="suspended")
        self.assertIsNone(CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id))

    def test_customer_can_view_a_valid_public_profile(self):
        from apps.accounts.models.profiles import CustomerProfile
        from apps.kernel.models import Person, UserAccount

        supplier, _ = self._create_caregiver_supplier(
            display_name="مراقب واقعی", verification_status="verified", profile_status="active",
        )
        person = Person.objects.create(tenant=self.tenant, full_name="Customer")
        user = UserAccount.objects.create_user(phone="09121110000", person=person, tenant=self.tenant)
        CustomerProfile.objects.create(user=user, person=person, phone="09121110000", display_name="Customer")

        self.client.force_login(user)
        response = self.client.get(
            reverse("public_site:caregiver-profile", args=[supplier.id]), {"tenant": self.tenant.slug},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "مراقب واقعی")

    def test_public_context_excludes_private_fields(self):
        supplier, caregiver = self._create_caregiver_supplier(verification_status="verified")
        response = self.client.get(
            reverse("public_site:caregiver-profile", args=[supplier.id]), {"tenant": self.tenant.slug},
        )
        self.assertNotContains(response, caregiver.phone)
        self.assertNotContains(response, caregiver.user.phone)


class PublicProfileSkillsExperienceCredentialsTest(PublicSiteTestCase):
    def _reviewer(self):
        from apps.accounts.permission_keys import ACCOUNTS_DOCUMENT_REVIEW
        from apps.kernel.models import Person, UserAccount

        person = Person.objects.create(tenant=self.tenant, full_name="Reviewer")
        reviewer = UserAccount.objects.create_user(phone="09121230098", person=person, tenant=self.tenant)
        grant_permissions(self.tenant, reviewer, [ACCOUNTS_DOCUMENT_REVIEW])
        return reviewer

    def test_visible_skill_appears_on_public_profile(self):
        supplier, caregiver = self._create_caregiver_supplier(verification_status="verified")
        CaregiverSkillService.add_skill(caregiver, name="مراقبت تخصصی")
        profile = CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id)
        self.assertEqual(profile.skills[0].name, "مراقبت تخصصی")

    def test_hidden_skill_does_not_appear(self):
        supplier, caregiver = self._create_caregiver_supplier(verification_status="verified")
        skill = CaregiverSkillService.add_skill(caregiver, name="مراقبت تخصصی")
        skill.is_visible = False
        skill.save(update_fields=["is_visible"])
        profile = CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id)
        self.assertEqual(profile.skills, ())

    def test_experience_appears_on_public_profile(self):
        supplier, caregiver = self._create_caregiver_supplier(verification_status="verified")
        CaregiverExperienceService.create(caregiver, title="پرستار سالمندان", start_date=datetime.date(2020, 1, 1))
        profile = CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id)
        self.assertEqual(profile.experience[0].title, "پرستار سالمندان")

    def _approve_required_documents(self, caregiver, *, reviewer):
        """Approving only one of the two required caregiver document types
        would leave ProfileVerificationRollupService's own recompute (run
        automatically inside VerificationReviewService.approve()) at
        PENDING, not VERIFIED — both required types must be approved for
        the fixture's `verification_status="verified"` to actually hold
        after the call."""
        for doc_type in (DocumentType.IDENTITY, DocumentType.BACKGROUND_CHECK):
            doc = DocumentService.upload_caregiver_document(
                caregiver, document_type=doc_type,
                file=SimpleUploadedFile(f"{doc_type}.pdf", PDF_BYTES, content_type="application/pdf"),
            )
            VerificationReviewService.approve(document_id=doc.id, tenant_id=self.tenant.id, reviewer=reviewer)

    def test_approved_credential_appears_on_public_profile(self):
        supplier, caregiver = self._create_caregiver_supplier(verification_status="verified")
        reviewer = self._reviewer()
        self._approve_required_documents(caregiver, reviewer=reviewer)
        profile = CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id)
        self.assertEqual(len(profile.credentials), 2)

    def test_credential_summary_never_includes_file_url_or_reviewer(self):
        supplier, caregiver = self._create_caregiver_supplier(verification_status="verified")
        reviewer = self._reviewer()
        self._approve_required_documents(caregiver, reviewer=reviewer)

        response = self.client.get(
            reverse("public_site:caregiver-profile", args=[supplier.id]), {"tenant": self.tenant.slug},
        )
        self.assertNotContains(response, "private/documents/")
        self.assertNotContains(response, str(reviewer.id))


class PublicProfileQueryCountTest(PublicSiteTestCase):
    def test_query_count_does_not_grow_with_skills_experience_or_credentials(self):
        supplier, caregiver = self._create_caregiver_supplier(verification_status="verified")
        reviewer = self._reviewer_for_query_test()
        from django.core.files.uploadedfile import SimpleUploadedFile

        for i in range(5):
            CaregiverSkillService.add_skill(caregiver, name=f"Skill {i}")
            CaregiverExperienceService.create(
                caregiver, title=f"Role {i}", start_date=datetime.date(2015 + i, 1, 1),
            )
        for doc_type in (DocumentType.IDENTITY, DocumentType.BACKGROUND_CHECK):
            doc = DocumentService.upload_caregiver_document(
                caregiver, document_type=doc_type,
                file=SimpleUploadedFile(f"{doc_type}.pdf", PDF_BYTES, content_type="application/pdf"),
            )
            VerificationReviewService.approve(document_id=doc.id, tenant_id=self.tenant.id, reviewer=reviewer)

        with self.assertNumQueries(13):
            CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id)

    def _reviewer_for_query_test(self):
        from apps.accounts.permission_keys import ACCOUNTS_DOCUMENT_REVIEW
        from apps.kernel.models import Person, UserAccount

        person = Person.objects.create(tenant=self.tenant, full_name="Reviewer")
        reviewer = UserAccount.objects.create_user(phone="09121230097", person=person, tenant=self.tenant)
        grant_permissions(self.tenant, reviewer, [ACCOUNTS_DOCUMENT_REVIEW])
        return reviewer
