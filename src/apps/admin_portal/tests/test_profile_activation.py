"""Profile activation admin-portal views — Phase 1.3 Part D. Business-rule
tests live in apps.accounts.tests.test_profile_activation."""

import uuid

from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models.media import DocumentType
from apps.accounts.models.profiles import CaregiverProfile, OrganizationProfile, ProfileStatus
from apps.accounts.permission_keys import ACCOUNTS_DOCUMENT_REVIEW, ACCOUNTS_PROFILE_ACTIVATE
from apps.accounts.services.document_service import DocumentService
from apps.accounts.services.verification_review_service import VerificationReviewService
from apps.kernel.models import Person, UserAccount

from .helpers import AdminPortalTestCase

PDF_BYTES = b"%PDF-1.4 fake test content"


class ProfileActivationViewsTestCase(AdminPortalTestCase):
    def setUp(self):
        super().setUp()
        self.caregiver = self._create_caregiver(tenant=self.tenant)
        self.organization = self._create_organization(tenant=self.tenant)
        self._grant(self.actor, self.tenant, [ACCOUNTS_DOCUMENT_REVIEW, ACCOUNTS_PROFILE_ACTIVATE])

    def _create_caregiver(self, *, tenant, full_name="Test Caregiver", status=ProfileStatus.DRAFT) -> CaregiverProfile:
        phone = f"0912{uuid.uuid4().hex[:7]}"
        person = Person.objects.create(tenant=tenant, full_name=full_name)
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)
        return CaregiverProfile.objects.create(
            user=user,
            person=person,
            phone=phone,
            display_name=full_name,
            city="tehran",
            specialty="elderly-care",
            bio="Experienced caregiver.",
            years_experience=5,
            service_radius_km=10,
            status=status,
        )

    def _create_organization(self, *, tenant, name="Test Org", status=ProfileStatus.DRAFT) -> OrganizationProfile:
        phone = f"0912{uuid.uuid4().hex[:7]}"
        person = Person.objects.create(tenant=tenant, full_name=f"{name} Admin")
        admin_user = UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)
        return OrganizationProfile.objects.create(
            name=name,
            code=f"ORG-{uuid.uuid4().hex[:6].upper()}",
            admin_user=admin_user,
            tenant=tenant,
            city="tehran",
            phone="09120000000",
            address="Some address",
            description="A senior-care company.",
            company_type="home_care",
            status=status,
        )

    def _approve_required_caregiver_documents(self):
        for doc_type in (DocumentType.IDENTITY, DocumentType.BACKGROUND_CHECK):
            file = SimpleUploadedFile(f"{doc_type}.pdf", PDF_BYTES, content_type="application/pdf")
            doc = DocumentService.upload_caregiver_document(self.caregiver, document_type=doc_type, file=file)
            VerificationReviewService.approve(document_id=doc.id, tenant_id=self.tenant.id, reviewer=self.actor)


class DetailPageAccessTest(ProfileActivationViewsTestCase):
    def test_unauthenticated_denied(self):
        response = self.client.get(f"/admin-portal/verification/caregivers/{self.caregiver.id}/")
        self.assertEqual(response.status_code, 403)

    def test_actor_without_permission_denied(self):
        other_actor = self._create_actor(tenant=self.tenant, full_name="No Permission Actor")
        self.client.force_login(other_actor)
        response = self.client.get(f"/admin-portal/verification/caregivers/{self.caregiver.id}/")
        self.assertEqual(response.status_code, 403)

    def test_authorized_reviewer_can_view_caregiver_detail(self):
        self.client.force_login(self.actor)
        response = self.client.get(f"/admin-portal/verification/caregivers/{self.caregiver.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.caregiver.display_name)

    def test_authorized_reviewer_can_view_organization_detail(self):
        self.client.force_login(self.actor)
        response = self.client.get(f"/admin-portal/verification/organizations/{self.organization.id}/")
        self.assertEqual(response.status_code, 200)

    def test_cross_tenant_caregiver_returns_404(self):
        other_actor = self._create_actor(tenant=self.other_tenant)
        self._grant(other_actor, self.other_tenant, [ACCOUNTS_PROFILE_ACTIVATE])
        self.client.force_login(other_actor)
        response = self.client.get(f"/admin-portal/verification/caregivers/{self.caregiver.id}/")
        self.assertEqual(response.status_code, 404)


class ActivateActionTest(ProfileActivationViewsTestCase):
    def test_unauthenticated_cannot_post_activate(self):
        response = self.client.post(f"/admin-portal/verification/caregivers/{self.caregiver.id}/activate/")
        self.assertEqual(response.status_code, 403)

    def test_authorized_reviewer_activates_eligible_caregiver(self):
        self.assertEqual(self.caregiver.status, ProfileStatus.DRAFT)
        self._approve_required_caregiver_documents()
        self.client.force_login(self.actor)

        response = self.client.post(f"/admin-portal/verification/caregivers/{self.caregiver.id}/activate/")
        self.assertEqual(response.status_code, 302)
        self.caregiver.refresh_from_db()
        self.assertEqual(self.caregiver.status, ProfileStatus.ACTIVE)

    def test_activating_ineligible_caregiver_does_not_raise_and_stays_draft(self):
        self.client.force_login(self.actor)
        response = self.client.post(f"/admin-portal/verification/caregivers/{self.caregiver.id}/activate/")
        self.assertEqual(response.status_code, 302)  # redirects back, no 500

        detail = self.client.get(f"/admin-portal/verification/caregivers/{self.caregiver.id}/")
        self.assertEqual(detail.status_code, 200)
        self.caregiver.refresh_from_db()
        self.assertEqual(self.caregiver.status, ProfileStatus.DRAFT)

    def test_suspended_caregiver_activation_is_refused(self):
        self.caregiver.status = ProfileStatus.SUSPENDED
        self.caregiver.save(update_fields=["status"])
        self._approve_required_caregiver_documents()
        self.client.force_login(self.actor)

        response = self.client.post(f"/admin-portal/verification/caregivers/{self.caregiver.id}/activate/")
        self.assertEqual(response.status_code, 302)
        self.caregiver.refresh_from_db()
        self.assertEqual(self.caregiver.status, ProfileStatus.SUSPENDED)

    def test_suspended_caregiver_detail_page_shows_suspended(self):
        self.caregiver.status = ProfileStatus.SUSPENDED
        self.caregiver.save(update_fields=["status"])
        self.client.force_login(self.actor)
        response = self.client.get(f"/admin-portal/verification/caregivers/{self.caregiver.id}/")
        self.assertContains(response, "معلق")

    def test_caregiver_cannot_self_activate_via_view(self):
        from apps.kernel.models.audit import AuditLog

        self._approve_required_caregiver_documents()
        self._grant(self.caregiver.user, self.tenant, [ACCOUNTS_PROFILE_ACTIVATE])
        self.client.force_login(self.caregiver.user)

        self.client.post(f"/admin-portal/verification/caregivers/{self.caregiver.id}/activate/")
        self.assertFalse(
            AuditLog.objects.filter(
                tenant_id=self.tenant.id,
                resource_type="CaregiverProfile",
                resource_id=self.caregiver.id,
                action="accounts.profile.activated",
            ).exists(),
            "self-activation must not be permitted, even with the permission granted",
        )
