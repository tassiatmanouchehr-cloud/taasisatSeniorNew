from apps.orders.models import Order

from .helpers import PortalTestCase


class WizardHappyPathTest(PortalTestCase):
    def test_full_wizard_flow_creates_an_order(self):
        self.login_as_customer()

        response = self.client.post(
            "/portal/requests/new/care-recipient/",
            {"care_recipient_id": str(self.care_recipient.id)},
        )
        self.assertRedirects(response, "/portal/requests/new/service/")

        response = self.client.post(
            "/portal/requests/new/service/",
            {"service_category_id": str(self.category.id)},
        )
        self.assertRedirects(response, "/portal/requests/new/schedule/")

        response = self.client.post("/portal/requests/new/schedule/", {})
        self.assertRedirects(response, "/portal/requests/new/address/")

        response = self.client.post(
            "/portal/requests/new/address/",
            {"city": "tehran", "address": "خیابان آزادی", "phone": "09121234567"},
        )
        self.assertRedirects(response, "/portal/requests/new/notes/")

        response = self.client.post(
            "/portal/requests/new/notes/",
            {"description": "نیاز به مراقبت روزانه"},
        )
        self.assertRedirects(response, "/portal/requests/new/review/")

        response = self.client.get("/portal/requests/new/review/")
        self.assertEqual(response.status_code, 200)

        response = self.client.post("/portal/requests/new/submit/")
        self.assertEqual(response.status_code, 302)

        order = Order.objects.get(customer_profile=self.customer)
        self.assertEqual(order.elder_profile_id, self.care_recipient.id)
        self.assertEqual(order.description, "نیاز به مراقبت روزانه")
        self.assertEqual(order.address, "خیابان آزادی")
        self.assertRedirects(response, f"/portal/requests/{order.id}/")

    def test_submit_clears_wizard_session(self):
        self.login_as_customer()
        self.client.post(
            "/portal/requests/new/care-recipient/",
            {"care_recipient_id": str(self.care_recipient.id)},
        )
        self.client.post("/portal/requests/new/service/", {"service_category_id": str(self.category.id)})
        self.client.post("/portal/requests/new/schedule/", {})
        self.client.post(
            "/portal/requests/new/address/",
            {"city": "tehran", "address": "addr", "phone": "0912"},
        )
        self.client.post("/portal/requests/new/notes/", {"description": "desc"})
        self.client.post("/portal/requests/new/submit/")

        self.assertNotIn("portal_request_wizard", self.client.session)


class WizardGuardTest(PortalTestCase):
    def test_service_step_redirects_to_care_recipient_step_if_skipped(self):
        self.login_as_customer()
        response = self.client.get("/portal/requests/new/service/")
        self.assertRedirects(response, "/portal/requests/new/care-recipient/")

    def test_care_recipient_step_rejects_a_recipient_owned_by_another_customer(self):
        self.login_as_customer()
        from apps.accounts.services.care_recipients import CareRecipientService

        other_recipient = CareRecipientService.create(
            customer_profile=self.other_customer,
            full_name="Not Mine",
        )
        response = self.client.post(
            "/portal/requests/new/care-recipient/",
            {"care_recipient_id": str(other_recipient.id)},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("care_recipient_id", self.client.session.get("portal_request_wizard", {}))
