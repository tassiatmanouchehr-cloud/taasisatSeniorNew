"""
Read-only Admin Portal view tests for the RBAC enforcement-toggle status
page — RBAC Enforcement-Toggle Visibility & Audit Remediation.

Per the approved architecture decision, this page is informational only:
no toggle, form, or mutation route exists anywhere in application UI.
"""

from apps.admin_portal import permission_keys
from apps.kernel.services.rbac_configuration import RBACConfiguration

from .helpers import AdminPortalTestCase

URL = "/admin-portal/system/rbac-enforcement/"


class RbacEnforcementStatusAccessTest(AdminPortalTestCase):
    def test_authorized_read_succeeds(self):
        self._grant(self.actor, self.tenant, [permission_keys.RBAC_ENFORCEMENT_READ])
        self.client.force_login(self.actor)

        response = self.client.get(URL)

        self.assertEqual(response.status_code, 200)

    def test_unauthorized_read_denied(self):
        self.client.force_login(self.actor)  # no permission granted

        response = self.client.get(URL)

        self.assertEqual(response.status_code, 403)

    def test_anonymous_read_denied(self):
        response = self.client.get(URL)
        self.assertEqual(response.status_code, 403)

    def test_no_post_mutation_route_exists(self):
        self._grant(self.actor, self.tenant, [permission_keys.RBAC_ENFORCEMENT_READ])
        self.client.force_login(self.actor)

        response = self.client.post(URL, {"enabled": "false"})

        self.assertEqual(response.status_code, 405)


class RbacEnforcementStatusContentTest(AdminPortalTestCase):
    def setUp(self):
        super().setUp()
        self._grant(self.actor, self.tenant, [permission_keys.RBAC_ENFORCEMENT_READ])
        self.client.force_login(self.actor)

    def test_correct_tenant_state_displayed_when_default(self):
        response = self.client.get(URL)
        self.assertContains(response, "فعال")
        self.assertNotContains(response, "هشدار: اجرای RBAC")

    def test_implicit_default_displayed_distinctly_from_explicit_override(self):
        response = self.client.get(URL)
        self.assertContains(response, "پیش‌فرض ضمنی")

        RBACConfiguration.set_enforcement_enabled(
            tenant_id=self.tenant.id,
            enabled=True,
            actor_display="ops:test",
            reason="explicit confirm",
        )

    def test_disabled_warning_visible_when_enforcement_disabled(self):
        RBACConfiguration.set_enforcement_enabled(
            tenant_id=self.tenant.id,
            enabled=False,
            actor_display="ops:test",
            reason="incident",
        )

        response = self.client.get(URL)

        self.assertContains(response, "هشدار: اجرای RBAC برای این مستأجر غیرفعال است")
        self.assertContains(response, "غیرفعال")

    def test_override_source_displayed_after_explicit_change(self):
        RBACConfiguration.set_enforcement_enabled(
            tenant_id=self.tenant.id,
            enabled=False,
            actor_display="ops:test",
            reason="incident",
        )

        response = self.client.get(URL)

        self.assertContains(response, "مقدار صریح")
        self.assertContains(response, "ops:test")
        self.assertContains(response, "incident")

    def test_no_form_or_mutation_control_rendered(self):
        response = self.client.get(URL)
        content = response.content.decode()
        self.assertNotIn("<form", content)
        self.assertNotIn('type="submit"', content)
        self.assertNotIn('method="post"', content.lower())

    def test_no_cross_tenant_data_disclosure(self):
        other_tenant = self.other_tenant
        RBACConfiguration.set_enforcement_enabled(
            tenant_id=other_tenant.id,
            enabled=False,
            actor_display="ops:other",
            reason="other tenant incident - must not leak",
        )

        response = self.client.get(URL)

        self.assertNotContains(response, "other tenant incident")
        self.assertNotContains(response, "ops:other")
        self.assertContains(response, "فعال")  # own tenant is still the untouched default

    def test_no_unrelated_configuration_values_exposed(self):
        response = self.client.get(URL)
        content = response.content.decode()
        self.assertNotIn("ConfigurationKey", content)
        self.assertNotIn("commission.", content)
