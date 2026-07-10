"""Capacity overview and performance reports — Epic 02."""

from .helpers import OrganizationPortalTestCase


class CapacityViewTest(OrganizationPortalTestCase):
    def test_shows_active_staff_engagement(self):
        self.login_as_admin()
        response = self.client.get("/organization/capacity/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["rows"]), 1)
        self.assertEqual(response.context["rows"][0]["engagement_count"], 0)


class ReportsViewTest(OrganizationPortalTestCase):
    def test_shows_report_for_own_staff(self):
        self.login_as_admin()
        response = self.client.get("/organization/reports/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["reports"]), 1)
