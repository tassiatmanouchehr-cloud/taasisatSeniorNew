"""Organization self-profile tests — Epic 06 Sprint 2 (Shared Portal UI
Core, Provider Profile, Organization Profile)."""

import io
import uuid

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from apps.accounts.models.media import VerificationDocument
from apps.accounts.models.profiles import (
    OrganizationMembership,
    OrganizationProfile,
    OrgMembershipRole,
    OrgMembershipStatus,
)

from .helpers import OrganizationPortalTestCase


def _png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (1, 1), color=(0, 255, 0)).save(buffer, format="PNG")
    return buffer.getvalue()


_PNG_BYTES = _png_bytes()


class OrganizationProfileAccessTest(OrganizationPortalTestCase):
    def test_active_admin_can_access_profile(self):
        self.login_as_admin()
        response = self.client.get(reverse("organization_portal:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Care Co")

    def test_provider_cannot_edit_organization(self):
        self.client.force_login(self.caregiver_user)
        response = self.client.get(reverse("organization_portal:profile"))
        self.assertEqual(response.status_code, 403)

    def test_non_admin_member_cannot_access(self):
        self.client.force_login(self.non_admin_user)
        response = self.client.get(reverse("organization_portal:profile"))
        self.assertEqual(response.status_code, 403)

    def test_unrelated_organization_admin_cannot_edit_this_organization(self):
        """resolve_organization() always resolves the caller's OWN
        organization — an unrelated admin editing never touches this
        organization's data, verified end to end."""
        other_admin = self._create_user(tenant=self.tenant, phone="09121110099")
        other_org = OrganizationProfile.objects.create(
            name="Other Org",
            code=f"other-{uuid.uuid4().hex[:8]}",
            admin_user=other_admin,
            tenant=self.tenant,
        )
        OrganizationMembership.objects.create(
            organization=other_org,
            user=other_admin,
            role_type=OrgMembershipRole.ADMIN,
            status=OrgMembershipStatus.ACTIVE,
        )
        self.client.force_login(other_admin)
        self.client.post(
            reverse("organization_portal:profile-edit"),
            {
                "name": "Hijacked Name",
                "description": "",
                "city": "",
                "phone": "",
                "address": "",
                "company_type": "",
                "team_size": "",
            },
        )
        self.organization.refresh_from_db()
        other_org.refresh_from_db()
        self.assertEqual(self.organization.name, "Care Co")
        self.assertEqual(other_org.name, "Hijacked Name")

    def test_cross_tenant_isolation(self):
        other_tenant_admin = self._create_user(tenant=self.other_tenant, phone="09121110098")
        other_tenant_org = OrganizationProfile.objects.create(
            name="Other Tenant Org",
            code=f"ot-{uuid.uuid4().hex[:8]}",
            admin_user=other_tenant_admin,
            tenant=self.other_tenant,
        )
        OrganizationMembership.objects.create(
            organization=other_tenant_org,
            user=other_tenant_admin,
            role_type=OrgMembershipRole.ADMIN,
            status=OrgMembershipStatus.ACTIVE,
        )
        self.client.force_login(other_tenant_admin)
        response = self.client.get(reverse("organization_portal:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Other Tenant Org")
        self.assertNotContains(response, "Care Co")


class OrganizationProfileUpdateTest(OrganizationPortalTestCase):
    def test_active_admin_can_update_profile(self):
        self.login_as_admin()
        response = self.client.post(
            reverse("organization_portal:profile-edit"),
            {
                "name": "نام جدید",
                "description": "توضیحات",
                "city": "شیراز",
                "phone": "07100000000",
                "address": "آدرس",
                "company_type": "",
                "team_size": "",
            },
        )
        self.assertRedirects(response, reverse("organization_portal:profile"))
        self.organization.refresh_from_db()
        self.assertEqual(self.organization.name, "نام جدید")
        self.assertEqual(self.organization.city, "شیراز")

    def test_services_update(self):
        self.login_as_admin()
        response = self.client.post(
            reverse("organization_portal:profile-edit-services"),
            {
                "service_category_ids": [str(self.category.id)],
            },
        )
        self.assertRedirects(response, reverse("organization_portal:profile"))
        from apps.accounts.services.supplier_bridge import get_or_create_supplier_for_organization

        supplier = get_or_create_supplier_for_organization(self.organization, tenant_id=self.tenant.id)
        self.assertIn(str(self.category.id), supplier.service_categories)

    def test_cannot_self_verify(self):
        self.login_as_admin()
        self.client.post(
            reverse("organization_portal:profile-edit"),
            {
                "name": "X",
                "description": "",
                "city": "",
                "phone": "",
                "address": "",
                "company_type": "",
                "team_size": "",
                "verification_status": "verified",
            },
        )
        from apps.accounts.models.profiles import VerificationStatus

        self.organization.refresh_from_db()
        self.assertEqual(self.organization.verification_status, VerificationStatus.UNVERIFIED)

    def test_headline_update(self):
        """Sprint 3.2: the professional-headline field is editable through
        the same profile-edit action, whitelisted alongside the other
        public/contact fields."""
        self.login_as_admin()
        response = self.client.post(
            reverse("organization_portal:profile-edit"),
            {
                "name": "Care Co",
                "headline": "بیش از ۱۰ سال تجربه در مراقبت سالمندان",
                "description": "",
                "city": "",
                "phone": "",
                "address": "",
                "company_type": "",
                "team_size": "",
            },
        )
        self.assertRedirects(response, reverse("organization_portal:profile"))
        self.organization.refresh_from_db()
        self.assertEqual(self.organization.headline, "بیش از ۱۰ سال تجربه در مراقبت سالمندان")

    def test_headline_shown_on_profile_page(self):
        self.organization.headline = "متخصص مراقبت در منزل"
        self.organization.save(update_fields=["headline"])
        self.login_as_admin()
        response = self.client.get(reverse("organization_portal:profile"))
        self.assertContains(response, "متخصص مراقبت در منزل")


class OrganizationMediaUploadTest(OrganizationPortalTestCase):
    def test_logo_upload(self):
        self.login_as_admin()
        response = self.client.post(
            reverse("organization_portal:profile-logo-upload"),
            {
                "image": SimpleUploadedFile("logo.png", _PNG_BYTES, content_type="image/png"),
            },
        )
        self.assertRedirects(response, reverse("organization_portal:profile"))
        self.organization.refresh_from_db()
        self.assertTrue(self.organization.logo)

    def test_cover_upload(self):
        self.login_as_admin()
        response = self.client.post(
            reverse("organization_portal:profile-cover-upload"),
            {
                "image": SimpleUploadedFile("cover.png", _PNG_BYTES, content_type="image/png"),
            },
        )
        self.assertRedirects(response, reverse("organization_portal:profile"))
        self.organization.refresh_from_db()
        self.assertTrue(self.organization.cover_image)

    def test_invalid_upload_rejected(self):
        self.login_as_admin()
        response = self.client.post(
            reverse("organization_portal:profile-logo-upload"),
            {
                "image": SimpleUploadedFile("not-an-image.txt", b"just text", content_type="text/plain"),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.organization.refresh_from_db()
        self.assertFalse(self.organization.logo)

    def test_media_upload_only_affects_own_organization(self):
        """Sprint 3.2 tenant-isolation requirement: an org admin's media
        upload/remove can only ever reach their own organization —
        profile-logo-upload/-remove take no organization id at all,
        always resolving through resolve_organization()'s own-identity
        lookup, so a second organization is structurally unreachable."""
        other_admin = self._create_user(tenant=self.tenant, phone="09121110097")
        other_org = OrganizationProfile.objects.create(
            name="Other Org",
            code=f"other-{uuid.uuid4().hex[:8]}",
            admin_user=other_admin,
            tenant=self.tenant,
        )
        OrganizationMembership.objects.create(
            organization=other_org,
            user=other_admin,
            role_type=OrgMembershipRole.ADMIN,
            status=OrgMembershipStatus.ACTIVE,
        )

        self.login_as_admin()
        self.client.post(
            reverse("organization_portal:profile-logo-upload"),
            {"image": SimpleUploadedFile("logo.png", _PNG_BYTES, content_type="image/png")},
        )
        other_org.refresh_from_db()
        self.assertFalse(other_org.logo)

    def test_media_upload_denied_for_unauthenticated(self):
        response = self.client.post(
            reverse("organization_portal:profile-logo-upload"),
            {"image": SimpleUploadedFile("logo.png", _PNG_BYTES, content_type="image/png")},
        )
        self.assertEqual(response.status_code, 403)

    def test_media_upload_denied_for_non_admin_staff(self):
        self.client.force_login(self.caregiver_user)
        response = self.client.post(
            reverse("organization_portal:profile-logo-upload"),
            {"image": SimpleUploadedFile("logo.png", _PNG_BYTES, content_type="image/png")},
        )
        self.assertEqual(response.status_code, 403)
        self.organization.refresh_from_db()
        self.assertFalse(self.organization.logo)

    def test_terminated_caregiver_membership_gets_no_portal_access(self):
        """Sprint 3.2 tenant-isolation requirement: a former (terminated)
        caregiver staff member must not retain any organization-internal
        access, mirroring the already-active-only rule an active
        CAREGIVER-role member is already held to."""
        self.staff_membership.status = OrgMembershipStatus.REMOVED
        self.staff_membership.save(update_fields=["status"])

        self.client.force_login(self.caregiver_user)
        response = self.client.get(reverse("organization_portal:profile"))
        self.assertEqual(response.status_code, 403)


class OrganizationDocumentTest(OrganizationPortalTestCase):
    def test_document_upload_creates_pending_status(self):
        self.login_as_admin()
        response = self.client.post(
            reverse("organization_portal:document-manage", args=["registration"]),
            {
                "file": SimpleUploadedFile("reg.pdf", b"%PDF-1.4 fake", content_type="application/pdf"),
            },
        )
        self.assertRedirects(response, reverse("organization_portal:profile"))
        doc = VerificationDocument.objects.get(organization=self.organization, document_type="registration")
        self.assertEqual(doc.status, "pending")

    def test_document_status_visible_on_profile(self):
        self.login_as_admin()
        self.client.post(
            reverse("organization_portal:document-manage", args=["registration"]),
            {
                "file": SimpleUploadedFile("reg.pdf", b"%PDF-1.4 fake", content_type="application/pdf"),
            },
        )
        response = self.client.get(reverse("organization_portal:profile"))
        self.assertContains(response, "مدرک ثبت شرکت")

    def test_cannot_self_verify_document(self):
        self.login_as_admin()
        self.client.post(
            reverse("organization_portal:document-manage", args=["registration"]),
            {
                "file": SimpleUploadedFile("reg.pdf", b"%PDF-1.4 fake", content_type="application/pdf"),
                "status": "verified",
            },
        )
        doc = VerificationDocument.objects.get(organization=self.organization, document_type="registration")
        self.assertEqual(doc.status, "pending")

    def test_unknown_document_type_404(self):
        self.login_as_admin()
        response = self.client.get(reverse("organization_portal:document-manage", args=["not-a-real-type"]))
        self.assertEqual(response.status_code, 404)


class OrganizationPublicPreviewTest(OrganizationPortalTestCase):
    def test_public_preview_link_present(self):
        from apps.accounts.services.supplier_bridge import get_or_create_supplier_for_organization

        self.login_as_admin()
        supplier = get_or_create_supplier_for_organization(self.organization, tenant_id=self.tenant.id)
        response = self.client.get(reverse("organization_portal:profile"))
        self.assertContains(response, f"/find-an-organization/{supplier.id}/")

    def test_private_staff_data_absent_from_public_preview(self):
        from apps.accounts.models.profiles import VerificationStatus
        from apps.accounts.services.supplier_bridge import get_or_create_supplier_for_organization
        from apps.public_site.services.organization_profile_service import OrganizationPublicProfileService

        self.organization.verification_status = VerificationStatus.VERIFIED
        self.organization.save(update_fields=["verification_status"])
        supplier = get_or_create_supplier_for_organization(self.organization, tenant_id=self.tenant.id)
        supplier.status = "active"
        supplier.save(update_fields=["status"])
        profile = OrganizationPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id)
        self.assertIsNotNone(profile)
        field_names = {f.name for f in profile.__dataclass_fields__.values()}
        for forbidden in ("staff", "membership", "document", "admin_user", "phone", "address"):
            self.assertFalse(any(forbidden in name for name in field_names))


class OrganizationNavigationTest(OrganizationPortalTestCase):
    def test_nav_includes_profile_link(self):
        self.login_as_admin()
        response = self.client.get(reverse("organization_portal:profile"))
        self.assertContains(response, "/organization/profile/")
        self.assertContains(response, "نمایه سازمان")

    def test_no_cross_role_menu_leakage(self):
        self.login_as_admin()
        response = self.client.get(reverse("organization_portal:profile"))
        self.assertNotContains(response, "/provider/")


class OrganizationProfileQueryCountTest(OrganizationPortalTestCase):
    """Epic 06 Sprint 2 explicitly requires query-count regression coverage
    for the new profile pages — "do not repeat the earlier directory N+1
    mistake" (Epic 06 Sprint 1's Architecture Review finding)."""

    def test_profile_page_query_count_bounded(self):
        """Locked baseline (steady state — the org's own ServiceSupplier
        row already exists, matching real usage after the first ever
        page load): session+user+org resolution (3), supplier lookup (1),
        rating summary (1), document list (1), active-staff count (1),
        plus Phase 1.3's fixed-cost activation-status lookup
        (session/user re-resolution inside the eligibility check,
        required-document-policy config lookup, document list for
        eligibility — `is_activated` itself is a status check with no
        query, Phase 1.3 remediation) (3) — 10 queries. A regression
        that turns any of these into a per-item loop would raise this
        count; this test exists specifically to catch that."""
        from apps.accounts.services.supplier_bridge import get_or_create_supplier_for_organization

        get_or_create_supplier_for_organization(self.organization, tenant_id=self.tenant.id)
        self.login_as_admin()
        with self.assertNumQueries(10):
            self.client.get(reverse("organization_portal:profile"))

    def test_query_count_does_not_grow_with_document_or_staff_count(self):
        from apps.accounts.services.document_service import DocumentService
        from apps.accounts.services.supplier_bridge import get_or_create_supplier_for_organization

        get_or_create_supplier_for_organization(self.organization, tenant_id=self.tenant.id)
        self.login_as_admin()
        with _QueryCounter(self.client, reverse("organization_portal:profile")) as before:
            pass

        for document_type in ("registration", "operating_license", "insurance"):
            DocumentService.upload_organization_document(
                self.organization,
                document_type=document_type,
                file=SimpleUploadedFile(f"{document_type}.pdf", b"%PDF-1.4 x", content_type="application/pdf"),
            )
        for i in range(3):
            extra_user = self._create_user(tenant=self.tenant, phone=f"0912111009{i}")
            OrganizationMembership.objects.create(
                organization=self.organization,
                user=extra_user,
                role_type=OrgMembershipRole.CAREGIVER,
                status=OrgMembershipStatus.ACTIVE,
            )

        with _QueryCounter(self.client, reverse("organization_portal:profile")) as after:
            pass

        self.assertEqual(before.count, after.count)


class _QueryCounter:
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
