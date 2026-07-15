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

    def test_hidden_experience_does_not_appear(self):
        supplier, caregiver = self._create_caregiver_supplier(verification_status="verified")
        CaregiverExperienceService.create(
            caregiver, title="پنهان", start_date=datetime.date(2020, 1, 1), is_visible=False,
        )
        profile = CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id)
        self.assertEqual(profile.experience, ())

    def test_skill_name_rendered_safely(self):
        supplier, caregiver = self._create_caregiver_supplier(verification_status="verified")
        CaregiverSkillService.add_skill(caregiver, name="<script>alert(1)</script>")
        response = self.client.get(
            reverse("public_site:caregiver-profile", args=[supplier.id]), {"tenant": self.tenant.slug},
        )
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "&lt;script&gt;")

    def test_experience_description_rendered_safely(self):
        supplier, caregiver = self._create_caregiver_supplier(verification_status="verified")
        CaregiverExperienceService.create(
            caregiver, title="X", description="<script>alert(1)</script>", start_date=datetime.date(2020, 1, 1),
        )
        response = self.client.get(
            reverse("public_site:caregiver-profile", args=[supplier.id]), {"tenant": self.tenant.slug},
        )
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "&lt;script&gt;")

    def test_experience_section_labeled_self_declared(self):
        supplier, caregiver = self._create_caregiver_supplier(verification_status="verified")
        CaregiverExperienceService.create(caregiver, title="X", start_date=datetime.date(2020, 1, 1))
        response = self.client.get(
            reverse("public_site:caregiver-profile", args=[supplier.id]), {"tenant": self.tenant.slug},
        )
        self.assertContains(response, "توسط خود مراقب اعلام شده")

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

    def test_rejection_reason_never_appears_publicly(self):
        supplier, caregiver = self._create_caregiver_supplier(verification_status="unverified")
        reviewer = self._reviewer()
        doc = DocumentService.upload_caregiver_document(
            caregiver, document_type=DocumentType.IDENTITY,
            file=SimpleUploadedFile("id.pdf", PDF_BYTES, content_type="application/pdf"),
        )
        VerificationReviewService.reject(
            document_id=doc.id, tenant_id=self.tenant.id, reviewer=reviewer,
            reason="مدرک جعلی به نظر می‌رسد و اسکن آن ناخوانا است",
        )
        # profile itself is None (unverified), but assert directly on the
        # selector too — the reason must never reach any public ViewModel.
        from apps.accounts.services.public_credential_selector import PublicCredentialSelector

        summaries = PublicCredentialSelector.for_caregiver(caregiver)
        self.assertEqual(summaries, ())
        for summary in summaries:
            self.assertFalse(hasattr(summary, "rejection_reason"))


class PublicProfileHighlightsAndBadgesTest(PublicSiteTestCase):
    """Sprint 2.3 (Credentials, Skills, Experience, Highlights) —
    ProfessionalHighlightsViewModel and precise VerificationBadgeViewModel
    entries, both purely derived from data get_profile() already fetched
    for the rest of the page."""

    def _reviewer(self):
        from apps.accounts.permission_keys import ACCOUNTS_DOCUMENT_REVIEW
        from apps.kernel.models import Person, UserAccount

        person = Person.objects.create(tenant=self.tenant, full_name="Reviewer")
        reviewer = UserAccount.objects.create_user(phone="09121230096", person=person, tenant=self.tenant)
        grant_permissions(self.tenant, reviewer, [ACCOUNTS_DOCUMENT_REVIEW])
        return reviewer

    def _approve_required_documents(self, caregiver, *, reviewer):
        for doc_type in (DocumentType.IDENTITY, DocumentType.BACKGROUND_CHECK):
            doc = DocumentService.upload_caregiver_document(
                caregiver, document_type=doc_type,
                file=SimpleUploadedFile(f"{doc_type}.pdf", PDF_BYTES, content_type="application/pdf"),
            )
            VerificationReviewService.approve(document_id=doc.id, tenant_id=self.tenant.id, reviewer=reviewer)

    def test_highlights_reflect_visible_skills_and_verified_credentials(self):
        supplier, caregiver = self._create_caregiver_supplier(
            verification_status="verified", years_experience=7,
        )
        CaregiverSkillService.add_skill(caregiver, name="مراقبت تخصصی")
        hidden = CaregiverSkillService.add_skill(caregiver, name="پنهان")
        hidden.is_visible = False
        hidden.save(update_fields=["is_visible"])
        reviewer = self._reviewer()
        self._approve_required_documents(caregiver, reviewer=reviewer)

        profile = CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id)
        self.assertEqual(profile.highlights.years_experience, 7)
        self.assertEqual(profile.highlights.visible_skill_count, 1)
        self.assertEqual(profile.highlights.verified_credential_count, 2)

    def test_verified_profile_with_no_credentials_gets_only_profile_badge(self):
        supplier, caregiver = self._create_caregiver_supplier(verification_status="verified")
        profile = CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id)
        labels = {badge.label for badge in profile.verification_badges}
        self.assertIn("نمایه تأییدشده", labels)
        self.assertNotIn("هویت تأییدشده", labels)
        self.assertNotIn("مدرک حرفه‌ای تأییدشده", labels)

    def test_approved_identity_document_gets_identity_verified_badge(self):
        supplier, caregiver = self._create_caregiver_supplier(verification_status="verified")
        reviewer = self._reviewer()
        self._approve_required_documents(caregiver, reviewer=reviewer)
        profile = CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id)
        labels = {badge.label for badge in profile.verification_badges}
        self.assertIn("هویت تأییدشده", labels)
        self.assertIn("مدرک حرفه‌ای تأییدشده", labels)

    def test_pending_document_grants_no_identity_badge(self):
        supplier, caregiver = self._create_caregiver_supplier(verification_status="unverified")
        DocumentService.upload_caregiver_document(
            caregiver, document_type=DocumentType.IDENTITY,
            file=SimpleUploadedFile("id.pdf", PDF_BYTES, content_type="application/pdf"),
        )
        # profile itself is None (unverified) — badges never computed at all.
        self.assertIsNone(CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id))

    def test_badges_never_imply_broader_approval_than_evidence(self):
        """Under the default required-document policy, a "verified"
        profile always has an approved IDENTITY document (it's mandatory)
        — so to prove the "Identity verified" badge is genuinely
        evidence-based and not just an alias for "profile verified", this
        narrows the tenant's required-document policy to exclude IDENTITY
        (the same override mechanism apps.accounts.tests
        .test_verification_policy.TenantOverrideTest already exercises),
        approves only BACKGROUND_CHECK, and confirms no "Identity
        verified" badge appears even though the profile itself is
        publicly verified."""
        from apps.accounts.services.verification_policy import CAREGIVER_REQUIRED_DOCUMENT_TYPES_KEY
        from apps.kernel.models.configuration import ConfigurationKey, ConfigurationValue, ScopeLevel, ValueType

        config_key, _ = ConfigurationKey.objects.get_or_create(
            key=CAREGIVER_REQUIRED_DOCUMENT_TYPES_KEY,
            defaults={
                "owner_module": "M08",
                "scope_level": ScopeLevel.TENANT,
                "value_type": ValueType.ARRAY,
                "default_value": [],
            },
        )
        supplier, caregiver = self._create_caregiver_supplier(verification_status="unverified")
        ConfigurationValue.objects.update_or_create(
            tenant_id=self.tenant.id, config_key=config_key, scope_type=ScopeLevel.TENANT,
            defaults={"value": [DocumentType.BACKGROUND_CHECK], "is_active": True},
        )
        reviewer = self._reviewer()
        doc = DocumentService.upload_caregiver_document(
            caregiver, document_type=DocumentType.BACKGROUND_CHECK,
            file=SimpleUploadedFile("bg.pdf", PDF_BYTES, content_type="application/pdf"),
        )
        VerificationReviewService.approve(document_id=doc.id, tenant_id=self.tenant.id, reviewer=reviewer)

        profile = CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id)
        self.assertIsNotNone(profile)  # publicly verified under the narrowed policy
        labels = {badge.label for badge in profile.verification_badges}
        self.assertNotIn("هویت تأییدشده", labels)
        self.assertIn("مدرک حرفه‌ای تأییدشده", labels)

    def test_hidden_caregiver_profile_has_no_highlights_or_badges(self):
        supplier, caregiver = self._create_caregiver_supplier(
            verification_status="verified", profile_status="draft",
        )
        CaregiverSkillService.add_skill(caregiver, name="X")
        self.assertIsNone(CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id))


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

        # 14, not 13 — Sprint 2.2 (Caregiver Gallery and Media Portfolio)
        # added one more fixed query for _gallery(); still O(1) regardless
        # of skill/experience/credential/gallery-item count (see
        # test_gallery_public.PublicGalleryQueryCountTest for the gallery
        # item count scaling proof).
        with self.assertNumQueries(14):
            CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id)

    def _reviewer_for_query_test(self):
        from apps.accounts.permission_keys import ACCOUNTS_DOCUMENT_REVIEW
        from apps.kernel.models import Person, UserAccount

        person = Person.objects.create(tenant=self.tenant, full_name="Reviewer")
        reviewer = UserAccount.objects.create_user(phone="09121230097", person=person, tenant=self.tenant)
        grant_permissions(self.tenant, reviewer, [ACCOUNTS_DOCUMENT_REVIEW])
        return reviewer
