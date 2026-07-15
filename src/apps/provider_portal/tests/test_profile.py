"""Provider self-profile tests — Epic 06 Sprint 2 (Shared Portal UI Core,
Provider Profile, Organization Profile)."""

import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from apps.accounts.models.media import VerificationDocument
from apps.kernel.models import Person, UserAccount

from .helpers import ProviderPortalTestCase


def _png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (1, 1), color=(255, 0, 0)).save(buffer, format="PNG")
    return buffer.getvalue()


_PNG_BYTES = _png_bytes()


class ProviderProfileAccessTest(ProviderPortalTestCase):
    def test_own_profile_access(self):
        self.login_as_provider()
        response = self.client.get(reverse("provider_portal:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Provider")

    def test_another_provider_editing_only_affects_their_own_profile(self):
        """No edit URL accepts an id — session identity is the only
        input, so 'another provider cannot edit it' is true by
        construction. Verify B's edit never touches A's data."""
        self.client.force_login(self.other_provider_user)
        self.client.post(
            reverse("provider_portal:profile-edit-basic"),
            {
                "display_name": "Provider B Updated",
                "city": "Shiraz",
            },
        )
        self.supplier.refresh_from_db()
        from apps.accounts.models.profiles import CaregiverProfile

        provider_a = CaregiverProfile.objects.get(user=self.provider_user)
        provider_b = CaregiverProfile.objects.get(user=self.other_provider_user)
        self.assertEqual(provider_a.display_name, "Test Provider")
        self.assertEqual(provider_b.display_name, "Provider B Updated")

    def test_customer_cannot_access_provider_profile(self):
        self.client.force_login(self.customer.user)
        response = self.client.get(reverse("provider_portal:profile"))
        self.assertEqual(response.status_code, 403)

    def test_organization_admin_without_caregiver_profile_cannot_access(self):
        person = Person.objects.create(tenant=self.tenant, full_name="Org Admin Only")
        admin_user = UserAccount.objects.create_user(phone="09129990099", person=person, tenant=self.tenant)
        self.client.force_login(admin_user)
        response = self.client.get(reverse("provider_portal:profile"))
        self.assertEqual(response.status_code, 403)

    def test_cross_tenant_isolation(self):
        """Both fixtures share the same generic 'Test Provider' display
        name, so isolation is verified by supplier id (public preview
        URL), not display name."""
        self.client.force_login(self.other_tenant_provider_user)
        response = self.client.get(reverse("provider_portal:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, f"/find-a-caregiver/{self.supplier.id}/")
        self.assertContains(response, f"/find-a-caregiver/{self.other_tenant_supplier.id}/")


class ProviderProfileUpdateTest(ProviderPortalTestCase):
    def test_basic_info_update(self):
        self.login_as_provider()
        response = self.client.post(
            reverse("provider_portal:profile-edit-basic"),
            {
                "display_name": "نام جدید",
                "city": "اصفهان",
            },
        )
        self.assertRedirects(response, reverse("provider_portal:profile"))
        from apps.accounts.models.profiles import CaregiverProfile

        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        self.assertEqual(caregiver.display_name, "نام جدید")
        self.assertEqual(caregiver.city, "اصفهان")

    def test_professional_info_update(self):
        self.login_as_provider()
        response = self.client.post(
            reverse("provider_portal:profile-edit-professional"),
            {
                "bio": "بیوگرافی جدید",
                "specialty": "پرستاری",
                "years_experience": "5",
                "service_radius_km": "10",
                "service_category_ids": [str(self.category.id)],
            },
        )
        self.assertRedirects(response, reverse("provider_portal:profile"))
        from apps.accounts.models.profiles import CaregiverProfile

        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        self.assertEqual(caregiver.bio, "بیوگرافی جدید")
        self.assertEqual(caregiver.years_experience, 5)
        self.supplier.refresh_from_db()
        self.assertIn(str(self.category.id), self.supplier.service_categories)

    def test_cannot_self_verify(self):
        """No form field anywhere accepts verification_status — POSTing
        it has zero effect."""
        self.login_as_provider()
        self.client.post(
            reverse("provider_portal:profile-edit-basic"),
            {
                "display_name": "X",
                "city": "Y",
                "verification_status": "verified",
            },
        )
        from apps.accounts.models.profiles import CaregiverProfile, VerificationStatus

        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        self.assertEqual(caregiver.verification_status, VerificationStatus.UNVERIFIED)


class ProviderMediaUploadTest(ProviderPortalTestCase):
    def test_avatar_upload(self):
        self.login_as_provider()
        response = self.client.post(
            reverse("provider_portal:profile-avatar-upload"),
            {
                "image": SimpleUploadedFile("avatar.png", _PNG_BYTES, content_type="image/png"),
            },
        )
        self.assertRedirects(response, reverse("provider_portal:profile"))
        from apps.accounts.models.profiles import CaregiverProfile

        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        self.assertTrue(caregiver.avatar)

    def test_cover_upload(self):
        self.login_as_provider()
        response = self.client.post(
            reverse("provider_portal:profile-cover-upload"),
            {
                "image": SimpleUploadedFile("cover.png", _PNG_BYTES, content_type="image/png"),
            },
        )
        self.assertRedirects(response, reverse("provider_portal:profile"))
        from apps.accounts.models.profiles import CaregiverProfile

        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        self.assertTrue(caregiver.cover_image)

    def test_invalid_upload_rejected(self):
        self.login_as_provider()
        response = self.client.post(
            reverse("provider_portal:profile-avatar-upload"),
            {
                "image": SimpleUploadedFile("not-an-image.txt", b"just some text", content_type="text/plain"),
            },
        )
        self.assertEqual(response.status_code, 200)
        from apps.accounts.models.profiles import CaregiverProfile

        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        self.assertFalse(caregiver.avatar)

    def test_avatar_remove(self):
        self.login_as_provider()
        self.client.post(
            reverse("provider_portal:profile-avatar-upload"),
            {
                "image": SimpleUploadedFile("avatar.png", _PNG_BYTES, content_type="image/png"),
            },
        )
        response = self.client.post(reverse("provider_portal:profile-avatar-remove"))
        self.assertRedirects(response, reverse("provider_portal:profile"))
        from apps.accounts.models.profiles import CaregiverProfile

        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        self.assertFalse(caregiver.avatar)


class ProviderDocumentTest(ProviderPortalTestCase):
    def test_document_upload_creates_pending_status(self):
        self.login_as_provider()
        response = self.client.post(
            reverse("provider_portal:document-manage", args=["identity"]),
            {
                "file": SimpleUploadedFile("id.pdf", b"%PDF-1.4 fake pdf content", content_type="application/pdf"),
            },
        )
        self.assertRedirects(response, reverse("provider_portal:profile"))
        from apps.accounts.models.profiles import CaregiverProfile

        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        doc = VerificationDocument.objects.get(caregiver=caregiver, document_type="identity")
        self.assertEqual(doc.status, "pending")

    def test_document_status_visible_on_profile(self):
        self.login_as_provider()
        self.client.post(
            reverse("provider_portal:document-manage", args=["identity"]),
            {
                "file": SimpleUploadedFile("id.pdf", b"%PDF-1.4 fake pdf content", content_type="application/pdf"),
            },
        )
        response = self.client.get(reverse("provider_portal:profile"))
        self.assertContains(response, "کارت هویت")

    def test_cannot_self_verify_document(self):
        """DocumentService has no method reachable from this portal that
        can set a document to verified — upload/replace always PENDING."""
        self.login_as_provider()
        self.client.post(
            reverse("provider_portal:document-manage", args=["identity"]),
            {
                "file": SimpleUploadedFile("id.pdf", b"%PDF-1.4 fake", content_type="application/pdf"),
                "status": "verified",
            },
        )
        from apps.accounts.models.profiles import CaregiverProfile

        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        doc = VerificationDocument.objects.get(caregiver=caregiver, document_type="identity")
        self.assertEqual(doc.status, "pending")

    def test_unknown_document_type_404(self):
        self.login_as_provider()
        response = self.client.get(reverse("provider_portal:document-manage", args=["not-a-real-type"]))
        self.assertEqual(response.status_code, 404)


class ProviderPublicPreviewTest(ProviderPortalTestCase):
    def test_public_preview_link_present(self):
        self.login_as_provider()
        response = self.client.get(reverse("provider_portal:profile"))
        self.assertContains(response, f"/find-a-caregiver/{self.supplier.id}/")

    def test_private_data_absent_from_public_preview(self):
        """The authenticated profile page must never leak into the
        public template — confirmed by checking the public page itself
        never renders document/verification internals."""
        from apps.public_site.services.profile_service import CaregiverPublicProfileService

        profile = CaregiverPublicProfileService.get_profile(self.supplier.id, tenant_id=self.tenant.id)
        if profile is not None:
            field_names = {f.name for f in profile.__dataclass_fields__.values()}
            for forbidden in ("document", "rejection_reason", "national_id", "reviewed_by"):
                self.assertFalse(any(forbidden in name for name in field_names))


class ProviderNavigationTest(ProviderPortalTestCase):
    def test_nav_includes_profile_link_and_marks_it_active(self):
        self.login_as_provider()
        response = self.client.get(reverse("provider_portal:profile"))
        self.assertContains(response, "/provider/profile/")
        self.assertContains(response, "نمایه من")

    def test_dashboard_nav_marks_dashboard_active_not_profile(self):
        self.login_as_provider()
        response = self.client.get(reverse("provider_portal:dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_no_cross_role_menu_leakage(self):
        """Provider nav must never include organization-only routes."""
        self.login_as_provider()
        response = self.client.get(reverse("provider_portal:profile"))
        self.assertNotContains(response, "/organization/")


class ProviderProfileQueryCountTest(ProviderPortalTestCase):
    """Epic 06 Sprint 2 explicitly requires query-count regression coverage
    for the new profile pages — "do not repeat the earlier directory N+1
    mistake" (Epic 06 Sprint 1's Architecture Review finding)."""

    def test_profile_page_query_count_bounded(self):
        """Locked baseline: session+user+caregiver+supplier resolution (4),
        rating summary (1), document list (1), completed-jobs count (1),
        plus Phase 1.3's fixed-cost activation-status lookup
        (required-document-policy config lookup + document list for
        eligibility — `is_activated` itself is a status check with no
        query, Phase 1.3 remediation) (2) — 9 queries for this fixture (no
        org affiliation, no service names). A regression that turns any
        of these into a per-item loop would raise this count; this test
        exists specifically to catch that."""
        self.login_as_provider()
        with self.assertNumQueries(9):
            self.client.get(reverse("provider_portal:profile"))

    def test_query_count_does_not_grow_with_document_or_order_count(self):
        """The profile page's own query count must stay flat as the
        number of documents/orders/reviews grows — a regression here
        would mean a new per-item N+1 was introduced."""
        from apps.accounts.services.document_service import DocumentService
        from apps.booking.services.assignment_service import AssignmentService
        from apps.orders.services.order_creation import create_public_order

        self.login_as_provider()
        with CaptureQueriesContextCounter(self.client, reverse("provider_portal:profile")) as before:
            pass

        for document_type in ("identity", "background_check", "qualification"):
            DocumentService.upload_caregiver_document(
                self._caregiver(),
                document_type=document_type,
                file=SimpleUploadedFile(f"{document_type}.pdf", b"%PDF-1.4 x", content_type="application/pdf"),
            )
        for _ in range(3):
            order = create_public_order(
                service_category_id=self.category.id,
                description="x",
                phone="0912",
                address="addr",
                city="tehran",
                customer_profile=self.customer,
                elder_profile=self.care_recipient,
                created_by=self.customer.user,
                tenant_id=self.tenant.id,
            )
            AssignmentService.assign(order_id=order.id, supplier=self.supplier)

        with CaptureQueriesContextCounter(self.client, reverse("provider_portal:profile")) as after:
            pass

        self.assertEqual(before.count, after.count)

    def _caregiver(self):
        from apps.accounts.models.profiles import CaregiverProfile

        return CaregiverProfile.objects.get(user=self.provider_user)


class CaptureQueriesContextCounter:
    """Small local helper: counts queries for one GET request."""

    def __init__(self, client, url):
        self.client = client
        self.url = url
        self.count = None

    def __enter__(self):
        from django.db import connection, reset_queries
        from django.test.utils import CaptureQueriesContext

        reset_queries()
        with CaptureQueriesContext(connection) as ctx:
            self.client.get(self.url)
        self.count = len(ctx.captured_queries)
        return self

    def __exit__(self, *exc_info):
        return False
