"""Skills / experience management — Phase 2.1 (Caregiver Professional
Profile Foundation). Service-layer tests live in
apps.accounts.tests.test_caregiver_professional_profile."""

import datetime

from django.urls import reverse

from apps.accounts.models.profiles import CaregiverProfile
from apps.accounts.services.caregiver_professional_profile_service import (
    CaregiverExperienceService,
    CaregiverSkillService,
)

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


class ProfilePagePreviewTest(ProviderPortalTestCase):
    def test_profile_page_shows_skills_and_experience_counts(self):
        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        CaregiverSkillService.add_skill(caregiver, name="Nursing")
        CaregiverExperienceService.create(caregiver, title="X", start_date=datetime.date(2020, 1, 1))
        self.login_as_provider()
        response = self.client.get(reverse("provider_portal:profile"))
        self.assertContains(response, "1 مهارت ثبت‌شده")
        self.assertContains(response, "1 سابقه کاری ثبت‌شده")
