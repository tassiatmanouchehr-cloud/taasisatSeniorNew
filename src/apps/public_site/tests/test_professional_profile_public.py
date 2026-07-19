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


class PublicProfileHeaderLayoutTest(PublicSiteTestCase):
    """FINAL UI CORRECTION BEFORE PR (Blocker 1): the profile header must
    render distinct, non-overlapping semantic regions for the back-link,
    avatar, identity (name/badges), and metadata (city/specialty,
    availability/affiliation badges) at every viewport — proven at the
    markup-contract level here; the geometric non-overlap claim itself is
    proven separately with real bounding-box measurement in the browser
    (Playwright), since Django's template-rendering test client cannot
    measure layout."""

    def test_header_has_distinct_semantic_regions_for_back_link_avatar_identity_badges_metadata(self):
        supplier, _caregiver = self._create_caregiver_supplier(
            display_name="مراقب نمونه", city="tehran", specialty="پرستار سالمندان",
        )
        response = self.client.get(
            reverse("public_site:caregiver-profile", args=[supplier.id]), {"tenant": self.tenant.slug},
        )
        content = response.content.decode()

        # Back-link region: its own wrapping block, reserving vertical
        # space (mb-14 / sm:mb-16) equal to the following block's
        # negative top margin (-mt-14 / sm:-mt-16) so the two never
        # collide — this is the exact fix for the reported overlap.
        self.assertIn('class="mx-auto max-w-5xl px-4 pt-4 mb-14 sm:px-6 sm:mb-16 lg:px-8"', content)
        self.assertIn("بازگشت به فهرست مراقبان", content)

        # Avatar region: its own wrapper, distinct from the identity block.
        self.assertIn('class="ring-4 ring-background rounded-full"', content)

        # Identity region: name + badges share a flex row, but the row
        # itself is a distinct element from the avatar and from the
        # metadata paragraph below it.
        self.assertIn('class="flex flex-wrap items-center gap-2"', content)
        self.assertIn("<h1", content)
        self.assertIn("مراقب نمونه", content)

        # Metadata (city/specialty) region: a separate <p>, not merged
        # into the <h1> or the badge row.
        self.assertIn('class="mt-1 text-sm text-text-muted"', content)
        self.assertIn("پرستار سالمندان", content)

        # Availability/affiliation badge row: a distinct block below the
        # identity block, not nested inside it.
        self.assertIn('class="mt-6 flex flex-wrap items-center gap-3"', content)

    def test_long_display_name_and_headline_render_without_truncation(self):
        long_name = "زهرا سادات میرمحمدصادقی حسینی طباطبایی نائینی اصفهانی"
        long_specialty = "مراقبت تخصصی از سالمندان مبتلا به آلزایمر و پارکینسون با سابقه طولانی درمانی"
        self.assertLessEqual(len(long_specialty), 100)
        supplier, _caregiver = self._create_caregiver_supplier(
            display_name=long_name, specialty=long_specialty, city="tehran",
        )
        response = self.client.get(
            reverse("public_site:caregiver-profile", args=[supplier.id]), {"tenant": self.tenant.slug},
        )

        # Full, untruncated text must appear — no CSS `truncate`/JS
        # substring shortening on the identity elements themselves. The
        # <h1>/<p> classes use wrapping (flex-wrap, whitespace-normal by
        # default), never a fixed single-line clamp.
        self.assertContains(response, long_name)
        self.assertContains(response, long_specialty)
        self.assertNotContains(response, "truncate")

    def test_missing_avatar_uses_approved_initials_fallback(self):
        supplier, caregiver = self._create_caregiver_supplier(display_name="بدون آواتار تست")
        self.assertFalse(caregiver.avatar)

        response = self.client.get(
            reverse("public_site:caregiver-profile", args=[supplier.id]), {"tenant": self.tenant.slug},
        )
        content = response.content.decode()

        # The approved fallback (ui/components/data/avatar.html, initials
        # mode): a role="img" container labelled with the caregiver's
        # name, no broken <img> tag inside the avatar wrapper.
        self.assertIn('role="img"', content)
        self.assertIn('aria-label="بدون آواتار تست"', content)
        self.assertNotContains(response, '<img src=""')

    def test_missing_optional_city_and_specialty_does_not_break_layout(self):
        supplier, _caregiver = self._create_caregiver_supplier(display_name="مراقب بدون شهر", city="", specialty="")
        response = self.client.get(
            reverse("public_site:caregiver-profile", args=[supplier.id]), {"tenant": self.tenant.slug},
        )

        self.assertEqual(response.status_code, 200)
        # metadata paragraph still renders (empty), identity region intact.
        self.assertContains(response, 'class="mt-1 text-sm text-text-muted"')
        self.assertContains(response, "مراقب بدون شهر")

    def test_unverified_badge_variant_still_renders_within_the_same_identity_row(self):
        """profile.verification_badges always carries at least the base
        "profile verified" badge for any publicly-visible caregiver
        (PublicProfileHighlightsAndBadgesTest already proves the data
        selection rules); this test only proves the *layout contract*:
        whatever the badge set is, it renders inside the same identity
        row as the name, not in a separately-positioned block."""
        supplier, _caregiver = self._create_caregiver_supplier(display_name="نشان تأیید تست")
        response = self.client.get(
            reverse("public_site:caregiver-profile", args=[supplier.id]), {"tenant": self.tenant.slug},
        )
        content = response.content.decode()

        h1_tag_index = content.index("<h1")
        row_start = content.rindex('class="flex flex-wrap items-center gap-2"', 0, h1_tag_index)
        row_end = content.index("</div>", h1_tag_index)
        row_markup = content[row_start:row_end]
        self.assertIn("نشان تأیید تست", row_markup)
        self.assertIn("نمایه تأییدشده", row_markup)


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

        # 15, not 13 — Sprint 2.2 (Caregiver Gallery and Media Portfolio)
        # added one fixed query for _gallery(), and Sprint 2.4 (Caregiver
        # Availability and Working Schedule) added one more fixed query for
        # _schedule_summary() (AvailabilityQueryService
        # .get_distinct_active_days()). Still O(1) regardless of
        # skill/experience/credential/gallery-item count (see
        # test_gallery_public.PublicGalleryQueryCountTest for the gallery
        # item count scaling proof).
        with self.assertNumQueries(15):
            CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id)

    def _reviewer_for_query_test(self):
        from apps.accounts.permission_keys import ACCOUNTS_DOCUMENT_REVIEW
        from apps.kernel.models import Person, UserAccount

        person = Person.objects.create(tenant=self.tenant, full_name="Reviewer")
        reviewer = UserAccount.objects.create_user(phone="09121230097", person=person, tenant=self.tenant)
        grant_permissions(self.tenant, reviewer, [ACCOUNTS_DOCUMENT_REVIEW])
        return reviewer


class PublicScheduleSummaryTest(PublicSiteTestCase):
    """Sprint 2.4 (Caregiver Availability and Working Schedule) —
    AvailabilityScheduleSummaryViewModel: safe, summarized (day labels
    only, never exact times or time-off details), gated by the same
    canonical is_publicly_visible() eligibility as every other section."""

    def _add_window(self, supplier, *, day_of_week, start="09:00", end="17:00"):
        import datetime as dt

        from apps.availability.services.mutation_service import AvailabilityMutationService

        AvailabilityMutationService.add_working_window(
            supplier=supplier,
            day_of_week=day_of_week,
            start_time=dt.time.fromisoformat(start),
            end_time=dt.time.fromisoformat(end),
        )

    def test_no_schedule_reports_has_schedule_false(self):
        supplier, _ = self._create_caregiver_supplier(verification_status="verified")
        profile = CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id)
        self.assertFalse(profile.schedule_summary.has_schedule)
        self.assertEqual(profile.schedule_summary.available_day_labels, ())

    def test_active_windows_produce_day_labels(self):
        supplier, caregiver = self._create_caregiver_supplier(verification_status="verified")
        self._add_window(supplier, day_of_week=0)
        self._add_window(supplier, day_of_week=2)
        profile = CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id)
        self.assertTrue(profile.schedule_summary.has_schedule)
        self.assertEqual(profile.schedule_summary.available_day_labels, ("دوشنبه", "چهارشنبه"))

    def test_disabled_window_excluded_from_summary(self):
        import datetime as dt

        from apps.availability.services.mutation_service import AvailabilityMutationService

        supplier, caregiver = self._create_caregiver_supplier(verification_status="verified")
        window = AvailabilityMutationService.add_working_window(
            supplier=supplier, day_of_week=1, start_time=dt.time(9, 0), end_time=dt.time(17, 0),
        )
        AvailabilityMutationService.update_working_window(window_id=window.id, is_active=False)
        profile = CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id)
        self.assertFalse(profile.schedule_summary.has_schedule)

    def test_summary_never_exposes_exact_times(self):
        supplier, _ = self._create_caregiver_supplier(verification_status="verified")
        self._add_window(supplier, day_of_week=0, start="09:00", end="17:00")
        response = self.client.get(
            reverse("public_site:caregiver-profile", args=[supplier.id]), {"tenant": self.tenant.slug},
        )
        self.assertContains(response, "دوشنبه")
        self.assertNotContains(response, "09:00")
        self.assertNotContains(response, "17:00")

    def test_summary_never_exposes_blocked_period_details(self):
        import datetime as dt

        from django.utils import timezone

        from apps.availability.models import BlockedPeriodReason
        from apps.availability.services.mutation_service import AvailabilityMutationService

        supplier, _ = self._create_caregiver_supplier(verification_status="verified")
        self._add_window(supplier, day_of_week=0)
        start = timezone.now() + dt.timedelta(days=1)
        AvailabilityMutationService.add_blocked_period(
            supplier=supplier,
            start_at=start,
            end_at=start + dt.timedelta(hours=2),
            reason=BlockedPeriodReason.SICK,
            notes="جزئیات محرمانه پزشکی",
        )
        response = self.client.get(
            reverse("public_site:caregiver-profile", args=[supplier.id]), {"tenant": self.tenant.slug},
        )
        self.assertNotContains(response, "جزئیات محرمانه پزشکی")
        self.assertNotContains(response, "SICK")

    def test_hidden_caregiver_has_no_schedule_summary(self):
        supplier, _ = self._create_caregiver_supplier(verification_status="verified", profile_status="draft")
        self._add_window(supplier, day_of_week=0)
        profile = CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id)
        self.assertIsNone(profile)
