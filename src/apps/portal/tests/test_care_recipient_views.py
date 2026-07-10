from apps.accounts.models.profiles import ElderProfile

from .helpers import PortalTestCase


class CareRecipientCreateViewTest(PortalTestCase):
    def test_get_renders_form(self):
        self.login_as_customer()
        response = self.client.get("/portal/care-recipients/new/")
        self.assertEqual(response.status_code, 200)

    def test_post_creates_care_recipient_owned_by_caller(self):
        self.login_as_customer()
        response = self.client.post("/portal/care-recipients/new/", {"full_name": "پدربزرگ"})
        self.assertRedirects(response, "/portal/care-recipients/")
        created = ElderProfile.objects.get(full_name="پدربزرگ")
        self.assertEqual(created.customer_profile_id, self.customer.id)

    def test_post_without_full_name_reshows_form_with_error(self):
        self.login_as_customer()
        response = self.client.post("/portal/care-recipients/new/", {"full_name": ""})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ElderProfile.objects.filter(customer_profile=self.customer, full_name="").exists())


class CareRecipientEditViewTest(PortalTestCase):
    def test_get_prefills_existing_data(self):
        self.login_as_customer()
        response = self.client.get(f"/portal/care-recipients/{self.care_recipient.id}/edit/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "مادر بزرگ")

    def test_post_updates_care_recipient(self):
        self.login_as_customer()
        response = self.client.post(
            f"/portal/care-recipients/{self.care_recipient.id}/edit/",
            {"full_name": "مادر بزرگ عزیز"},
        )
        self.assertRedirects(response, "/portal/care-recipients/")
        self.care_recipient.refresh_from_db()
        self.assertEqual(self.care_recipient.full_name, "مادر بزرگ عزیز")


class CareRecipientsListViewTest(PortalTestCase):
    def test_list_only_shows_own_recipients(self):
        from apps.accounts.services.care_recipients import CareRecipientService

        CareRecipientService.create(customer_profile=self.other_customer, full_name="Someone Else")
        self.login_as_customer()
        response = self.client.get("/portal/care-recipients/")
        self.assertContains(response, "مادر بزرگ")
        self.assertNotContains(response, "Someone Else")

    def test_archived_recipient_is_hidden_from_list(self):
        from apps.accounts.models.profiles import ProfileStatus

        self.login_as_customer()
        response = self.client.post(f"/portal/care-recipients/{self.care_recipient.id}/archive/")
        self.assertRedirects(response, "/portal/care-recipients/")
        self.care_recipient.refresh_from_db()
        self.assertEqual(self.care_recipient.status, ProfileStatus.ARCHIVED)

        response = self.client.get("/portal/care-recipients/")
        self.assertNotContains(response, "مادر بزرگ")

    def test_cannot_archive_another_customers_recipient(self):
        self.client.force_login(self.other_customer.user)
        response = self.client.post(f"/portal/care-recipients/{self.care_recipient.id}/archive/")
        self.assertEqual(response.status_code, 404)
