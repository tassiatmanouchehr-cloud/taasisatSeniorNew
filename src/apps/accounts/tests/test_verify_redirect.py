"""HTTP-level tests for role-aware post-OTP-login redirect (verify_view /
success_view). Drives the real phone -> OTP request -> verify flow via
the Django test client, exactly like a real browser would, rather than
calling resolve_post_login_destination() directly (that's covered in
test_post_login_destination.py).
"""

import uuid

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models.profiles import (
    OrganizationMembership,
    OrganizationProfile,
    OrgMembershipRole,
    OrgMembershipStatus,
)
from apps.accounts.services.profiles import ensure_caregiver_profile, ensure_customer_profile
from apps.kernel.models import Person, Tenant, UserAccount


@override_settings(DEBUG=True)
class VerifyRedirectTestCase(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"vr-{uuid.uuid4().hex[:8]}", name="Verify Redirect Tenant")

    def _create_user(self, phone, **kwargs):
        person = Person.objects.create(tenant=self.tenant, full_name="Test User")
        return UserAccount.objects.create_user(phone=phone, person=person, tenant=self.tenant, **kwargs)

    def _login_via_real_otp(self, phone, **extra_verify_data):
        """Drives the exact same phone -> request-OTP -> verify-OTP
        sequence a real browser does, using the real dev OTP code the
        session receives (DEBUG=True), never bypassing OTPService."""
        response = self.client.post(reverse("accounts:login"), {"phone": phone})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("accounts:verify"))

        code = self.client.session["dev_otp"]
        return self.client.post(reverse("accounts:verify"), {"code": code, **extra_verify_data})


class CustomerLoginRedirectTest(VerifyRedirectTestCase):
    """Item 1: customer OTP success redirect."""

    def test_customer_login_redirects_to_portal(self):
        user = self._create_user("09121110001")
        ensure_customer_profile(user)

        response = self._login_via_real_otp("09121110001")

        self.assertRedirects(response, "/portal/")


class IndependentProviderLoginRedirectTest(VerifyRedirectTestCase):
    """Item 2: independent-provider OTP success redirect."""

    def test_independent_provider_login_redirects_to_provider(self):
        user = self._create_user("09121110002")
        ensure_caregiver_profile(user)

        response = self._login_via_real_otp("09121110002")

        self.assertRedirects(response, "/provider/")


class AffiliatedProviderLoginRedirectTest(VerifyRedirectTestCase):
    """Item 3: affiliated-provider OTP success redirect."""

    def test_affiliated_provider_login_redirects_to_provider(self):
        from apps.accounts.models.profiles import CaregiverProviderType

        user = self._create_user("09121110003")
        ensure_caregiver_profile(user, provider_type=CaregiverProviderType.ORGANIZATION_AFFILIATED)

        response = self._login_via_real_otp("09121110003")

        self.assertRedirects(response, "/provider/")


class OrganizationAdminLoginRedirectTest(VerifyRedirectTestCase):
    """Item 4: organization-admin OTP success redirect."""

    def test_organization_admin_login_redirects_to_organization(self):
        user = self._create_user("09121110004")
        organization = OrganizationProfile.objects.create(
            name="Care Co",
            code=f"care-{uuid.uuid4().hex[:8]}",
            admin_user=user,
            tenant=self.tenant,
        )
        OrganizationMembership.objects.create(
            organization=organization,
            user=user,
            person=user.person,
            role_type=OrgMembershipRole.ADMIN,
            status=OrgMembershipStatus.ACTIVE,
        )

        response = self._login_via_real_otp("09121110004")

        self.assertRedirects(response, "/organization/")


class PlatformStaffLoginRedirectTest(VerifyRedirectTestCase):
    """Item 5: platform-admin policy."""

    def test_staff_login_with_no_marketplace_profile_redirects_to_django_admin(self):
        self._create_user("09121110005", is_staff=True, is_superuser=True)

        response = self._login_via_real_otp("09121110005")

        self.assertRedirects(response, "/admin/")


class UnsupportedAccountLoginFallbackTest(VerifyRedirectTestCase):
    """Item 6: unsupported/no-profile account uses safe fallback."""

    def test_login_with_no_resolvable_role_falls_back_to_success_page(self):
        self._create_user("09121110006")

        response = self._login_via_real_otp("09121110006")

        self.assertRedirects(response, reverse("accounts:success"))


class OpenRedirectRejectionTest(VerifyRedirectTestCase):
    """Item 10: malformed or external next parameter cannot cause an open
    redirect — the destination is resolved purely from canonical
    user/profile/membership state, never from any request parameter, so
    a next value (however it's supplied) has no effect at all."""

    def test_external_next_query_param_has_no_effect_on_destination(self):
        user = self._create_user("09121110007")
        ensure_customer_profile(user)

        self.client.post(
            reverse("accounts:login") + "?next=https://evil.example.com/",
            {"phone": "09121110007"},
        )
        code = self.client.session["dev_otp"]
        response = self.client.post(
            reverse("accounts:verify") + "?next=https://evil.example.com/",
            {"code": code, "next": "https://evil.example.com/"},
        )

        self.assertRedirects(response, "/portal/")
        self.assertNotIn("evil.example.com", response.url)

    def test_external_next_for_unsupported_account_still_lands_on_local_success_page(self):
        self._create_user("09121110008")

        response = self._login_via_real_otp("09121110008", next="//evil.example.com/")

        self.assertRedirects(response, reverse("accounts:success"))
        self.assertNotIn("evil.example.com", response.url)


class NoRedirectLoopTest(VerifyRedirectTestCase):
    """Item 14: already-authenticated users do not loop through
    /accounts/success/."""

    def test_authenticated_resolvable_user_visiting_success_page_is_bounced_once_not_looped(self):
        user = self._create_user("09121110009")
        ensure_customer_profile(user)
        self._login_via_real_otp("09121110009")

        response = self.client.get(reverse("accounts:success"))

        self.assertRedirects(response, "/portal/")
        # Following once more must not send us back to accounts:success —
        # /portal/ itself never redirects here, so there is nothing to loop.
        second_response = self.client.get("/portal/")
        self.assertNotEqual(second_response.status_code, 302)

    def test_authenticated_unresolvable_user_sees_fallback_page_without_looping(self):
        self._create_user("09121110010")
        self._login_via_real_otp("09121110010")

        response = self.client.get(reverse("accounts:success"))

        self.assertEqual(response.status_code, 200)


class StaleSuccessPageTextTest(VerifyRedirectTestCase):
    """Item 12: stale success-page text removed."""

    def test_stale_future_activation_claim_is_gone(self):
        self._create_user("09121110011")
        self._login_via_real_otp("09121110011")

        response = self.client.get(reverse("accounts:success"))

        self.assertNotContains(response, "پنل کاربری در مراحل بعدی فعال می‌شود")
        self.assertNotContains(response, "ثبت‌نام با موفقیت انجام شد")


class FallbackPageSafeActionsTest(VerifyRedirectTestCase):
    """Item 13: fallback page has working safe actions."""

    def test_fallback_page_offers_home_support_and_retry_links(self):
        self._create_user("09121110012")
        self._login_via_real_otp("09121110012")

        response = self.client.get(reverse("accounts:success"))

        self.assertContains(response, 'href="/"')
        self.assertContains(response, reverse("public_site:support"))
        self.assertContains(response, reverse("accounts:register"))

    def test_support_link_actually_resolves(self):
        response = self.client.get(reverse("public_site:support"))
        self.assertEqual(response.status_code, 200)
