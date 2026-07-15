"""Skills / experience management — Phase 2.1 (Caregiver Professional
Profile Foundation). Visibility toggles, expiring-soon badges, and the
owner-side highlights preview — Sprint 2.3 (Credentials, Skills,
Experience, Highlights). Service-layer tests live in
apps.accounts.tests.test_caregiver_professional_profile."""

import datetime

from django.urls import reverse

from apps.accounts.models.profiles import CaregiverProfile
from apps.accounts.services.caregiver_professional_profile_service import (
    CaregiverExperienceService,
    CaregiverSkillService,
)
from apps.kernel.models import Person, UserAccount

from .helpers import ProviderPortalTestCase


class SkillManagementTest(ProviderPortalTestCase):
    def test_owner_can_add_skill(self):
        self.login_as_provider()
        response = self.client.post(reverse("provider_portal:profile-skills"), {"name": "مراقبت از سالمندان"})
        self.assertEqual(response.status_code, 302)
        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        self.assertEqual(caregiver.skills.count(), 1)

    def test_duplicate_skill_shows_form_error(self):
        self.login_as_provider()
        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        CaregiverSkillService.add_skill(caregiver, name="Nursing")
        response = self.client.post(reverse("provider_portal:profile-skills"), {"name": "Nursing"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already been added")

    def test_unauthenticated_cannot_add_skill(self):
        response = self.client.post(reverse("provider_portal:profile-skills"), {"name": "X"})
        self.assertEqual(response.status_code, 403)

    def test_customer_cannot_add_skill(self):
        self.client.force_login(self.customer.user)
        response = self.client.post(reverse("provider_portal:profile-skills"), {"name": "X"})
        self.assertEqual(response.status_code, 403)

    def test_owner_can_remove_own_skill(self):
        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        skill = CaregiverSkillService.add_skill(caregiver, name="Nursing")
        self.login_as_provider()
        response = self.client.post(reverse("provider_portal:profile-skill-remove", kwargs={"skill_id": skill.id}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(caregiver.skills.count(), 0)

    def test_another_caregiver_cannot_remove_skill(self):
        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        skill = CaregiverSkillService.add_skill(caregiver, name="Nursing")
        self.client.force_login(self.other_provider_user)
        self.client.post(reverse("provider_portal:profile-skill-remove", kwargs={"skill_id": skill.id}))
        self.assertEqual(caregiver.skills.count(), 1)

    def test_owner_can_toggle_skill_visibility(self):
        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        skill = CaregiverSkillService.add_skill(caregiver, name="Nursing")
        self.login_as_provider()
        response = self.client.post(
            reverse("provider_portal:profile-skill-visibility-toggle", kwargs={"skill_id": skill.id}),
        )
        self.assertEqual(response.status_code, 302)
        skill.refresh_from_db()
        self.assertFalse(skill.is_visible)

    def test_another_caregiver_cannot_toggle_skill_visibility(self):
        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        skill = CaregiverSkillService.add_skill(caregiver, name="Nursing")
        self.client.force_login(self.other_provider_user)
        self.client.post(
            reverse("provider_portal:profile-skill-visibility-toggle", kwargs={"skill_id": skill.id}),
        )
        skill.refresh_from_db()
        self.assertTrue(skill.is_visible)  # unchanged

    def test_cross_tenant_cannot_toggle_skill_visibility(self):
        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        skill = CaregiverSkillService.add_skill(caregiver, name="Nursing")
        self.client.force_login(self.other_tenant_provider_user)
        self.client.post(
            reverse("provider_portal:profile-skill-visibility-toggle", kwargs={"skill_id": skill.id}),
        )
        skill.refresh_from_db()
        self.assertTrue(skill.is_visible)  # unchanged

    def test_customer_cannot_toggle_skill_visibility(self):
        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        skill = CaregiverSkillService.add_skill(caregiver, name="Nursing")
        self.client.force_login(self.customer.user)
        response = self.client.post(
            reverse("provider_portal:profile-skill-visibility-toggle", kwargs={"skill_id": skill.id}),
        )
        self.assertEqual(response.status_code, 403)
        skill.refresh_from_db()
        self.assertTrue(skill.is_visible)

    def test_unrelated_organization_user_cannot_mutate_skills(self):
        """An account with no caregiver_profile at all (e.g. an
        organization admin) — Sprint 2.3 security item 5."""
        person = Person.objects.create(tenant=self.tenant, full_name="Org Admin Only")
        org_user = UserAccount.objects.create_user(phone="09129990098", person=person, tenant=self.tenant)
        self.client.force_login(org_user)
        response = self.client.post(reverse("provider_portal:profile-skills"), {"name": "X"})
        self.assertEqual(response.status_code, 403)


class ExperienceManagementTest(ProviderPortalTestCase):
    def test_owner_can_add_experience(self):
        self.login_as_provider()
        response = self.client.post(
            reverse("provider_portal:profile-experience-add"),
            {"title": "Home Care Nurse", "organization_name": "Care Co", "start_date": "2020-01-01"},
        )
        self.assertEqual(response.status_code, 302)
        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        self.assertEqual(caregiver.experiences.count(), 1)

    def test_end_date_before_start_date_shows_form_error(self):
        self.login_as_provider()
        response = self.client.post(
            reverse("provider_portal:profile-experience-add"),
            {"title": "X", "start_date": "2022-01-01", "end_date": "2020-01-01"},
        )
        self.assertEqual(response.status_code, 200)
        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        self.assertEqual(caregiver.experiences.count(), 0)

    def test_owner_can_edit_own_experience(self):
        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        entry = CaregiverExperienceService.create(caregiver, title="Old", start_date=datetime.date(2020, 1, 1))
        self.login_as_provider()
        response = self.client.post(
            reverse("provider_portal:profile-experience-edit", kwargs={"experience_id": entry.id}),
            {"title": "New Title", "start_date": "2020-01-01"},
        )
        self.assertEqual(response.status_code, 302)
        entry.refresh_from_db()
        self.assertEqual(entry.title, "New Title")

    def test_another_caregiver_cannot_edit_experience(self):
        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        entry = CaregiverExperienceService.create(caregiver, title="Old", start_date=datetime.date(2020, 1, 1))
        self.client.force_login(self.other_provider_user)
        response = self.client.post(
            reverse("provider_portal:profile-experience-edit", kwargs={"experience_id": entry.id}),
            {"title": "Hacked", "start_date": "2020-01-01"},
        )
        self.assertEqual(response.status_code, 404)
        entry.refresh_from_db()
        self.assertEqual(entry.title, "Old")

    def test_owner_can_delete_own_experience(self):
        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        entry = CaregiverExperienceService.create(caregiver, title="X", start_date=datetime.date(2020, 1, 1))
        self.login_as_provider()
        response = self.client.post(
            reverse("provider_portal:profile-experience-delete", kwargs={"experience_id": entry.id}),
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(caregiver.experiences.count(), 0)

    def test_cross_tenant_cannot_edit_experience(self):
        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        entry = CaregiverExperienceService.create(caregiver, title="Old", start_date=datetime.date(2020, 1, 1))
        self.client.force_login(self.other_tenant_provider_user)
        response = self.client.post(
            reverse("provider_portal:profile-experience-edit", kwargs={"experience_id": entry.id}),
            {"title": "Hacked", "start_date": "2020-01-01"},
        )
        self.assertEqual(response.status_code, 404)
        entry.refresh_from_db()
        self.assertEqual(entry.title, "Old")

    def test_owner_can_hide_experience_via_edit_form(self):
        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        entry = CaregiverExperienceService.create(caregiver, title="X", start_date=datetime.date(2020, 1, 1))
        self.login_as_provider()
        response = self.client.post(
            reverse("provider_portal:profile-experience-edit", kwargs={"experience_id": entry.id}),
            {"title": "X", "start_date": "2020-01-01"},  # is_visible omitted = unchecked
        )
        self.assertEqual(response.status_code, 302)
        entry.refresh_from_db()
        self.assertFalse(entry.is_visible)

    def test_owner_can_reshow_hidden_experience_via_edit_form(self):
        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        entry = CaregiverExperienceService.create(
            caregiver, title="X", start_date=datetime.date(2020, 1, 1), is_visible=False,
        )
        self.login_as_provider()
        response = self.client.post(
            reverse("provider_portal:profile-experience-edit", kwargs={"experience_id": entry.id}),
            {"title": "X", "start_date": "2020-01-01", "is_visible": "on"},
        )
        self.assertEqual(response.status_code, 302)
        entry.refresh_from_db()
        self.assertTrue(entry.is_visible)

    def test_another_caregiver_cannot_change_experience_visibility(self):
        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        entry = CaregiverExperienceService.create(caregiver, title="X", start_date=datetime.date(2020, 1, 1))
        self.client.force_login(self.other_provider_user)
        self.client.post(
            reverse("provider_portal:profile-experience-edit", kwargs={"experience_id": entry.id}),
            {"title": "X", "start_date": "2020-01-01"},
        )
        entry.refresh_from_db()
        self.assertTrue(entry.is_visible)  # unchanged — request was 404'd


class ProfilePagePreviewTest(ProviderPortalTestCase):
    def test_profile_page_shows_skills_and_experience_counts(self):
        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        CaregiverSkillService.add_skill(caregiver, name="Nursing")
        CaregiverExperienceService.create(caregiver, title="X", start_date=datetime.date(2020, 1, 1))
        self.login_as_provider()
        response = self.client.get(reverse("provider_portal:profile"))
        self.assertContains(response, "1 مهارت ثبت‌شده")
        self.assertContains(response, "1 سابقه کاری ثبت‌شده")

    def test_profile_page_shows_highlights_preview(self):
        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        CaregiverSkillService.add_skill(caregiver, name="Nursing")
        CaregiverSkillService.add_skill(caregiver, name="First Aid")
        hidden = CaregiverSkillService.add_skill(caregiver, name="Hidden Skill")
        CaregiverSkillService.toggle_visibility(caregiver, skill_id=hidden.id)
        self.login_as_provider()
        response = self.client.get(reverse("provider_portal:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "مدارک تأییدشده")
        self.assertContains(response, "مهارت‌های نمایش‌داده‌شده")
        self.assertContains(response, "سوابق نمایش‌داده‌شده")

    def test_hidden_skill_not_counted_in_visible_highlights(self):
        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        visible = CaregiverSkillService.add_skill(caregiver, name="Nursing")
        hidden = CaregiverSkillService.add_skill(caregiver, name="Hidden")
        CaregiverSkillService.toggle_visibility(caregiver, skill_id=hidden.id)

        from apps.provider_portal.services.profile_service import ProviderProfilePresentationService

        highlights = ProviderProfilePresentationService._highlights(caregiver, public_credential_count=0)
        self.assertEqual(highlights.visible_skill_count, 1)
        self.assertNotEqual(caregiver.skills.count(), highlights.visible_skill_count)  # 2 total, 1 visible


class DocumentExpiringSoonBadgeTest(ProviderPortalTestCase):
    def test_expiring_soon_document_shows_expiring_soon_badge(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.accounts.models.media import DocumentType
        from apps.accounts.permission_keys import ACCOUNTS_DOCUMENT_REVIEW
        from apps.accounts.services.document_service import DocumentService
        from apps.accounts.services.verification_review_service import VerificationReviewService
        from apps.kernel.tests.rbac_helpers import grant_permissions

        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        reviewer_person = Person.objects.create(tenant=self.tenant, full_name="Reviewer")
        reviewer = UserAccount.objects.create_user(phone="09129990097", person=reviewer_person, tenant=self.tenant)
        grant_permissions(self.tenant, reviewer, [ACCOUNTS_DOCUMENT_REVIEW])

        doc = DocumentService.upload_caregiver_document(
            caregiver, document_type=DocumentType.IDENTITY,
            file=SimpleUploadedFile("id.pdf", b"%PDF-1.4 x", content_type="application/pdf"),
        )
        VerificationReviewService.approve(document_id=doc.id, tenant_id=self.tenant.id, reviewer=reviewer)
        doc.refresh_from_db()
        doc.expiry_date = datetime.date.today() + datetime.timedelta(days=10)
        doc.save(update_fields=["expiry_date"])

        self.login_as_provider()
        response = self.client.get(reverse("provider_portal:profile"))
        self.assertContains(response, "به‌زودی منقضی می‌شود")
