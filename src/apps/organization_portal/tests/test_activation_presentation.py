"""Owner-facing activation status on the organization profile page — Phase
1.3 Part D. Service-layer activation tests live in
apps.accounts.tests.test_profile_activation."""

from django.urls import reverse

from apps.accounts.models.media import DocumentType
from apps.accounts.services.document_service import DocumentService
from apps.accounts.services.profile_activation_service import ProfileActivationService
from apps.accounts.services.verification_review_service import VerificationReviewService
from apps.kernel.models import Person, UserAccount
from apps.kernel.tests.rbac_helpers import grant_permissions

from .helpers import OrganizationPortalTestCase

PDF_BYTES = b"%PDF-1.4 fake test content"


class OwnerActivationStatusTest(OrganizationPortalTestCase):
    def _reviewer(self):
        from apps.accounts.permission_keys import ACCOUNTS_DOCUMENT_REVIEW, ACCOUNTS_PROFILE_ACTIVATE

        person = Person.objects.create(tenant=self.tenant, full_name="Reviewer")
        reviewer = UserAccount.objects.create_user(phone="09121230000", person=person, tenant=self.tenant)
        grant_permissions(self.tenant, reviewer, [ACCOUNTS_DOCUMENT_REVIEW, ACCOUNTS_PROFILE_ACTIVATE])
        return reviewer

    def test_owner_sees_not_yet_eligible_before_documents_reviewed(self):
        self.login_as_admin()
        response = self.client.get(reverse("organization_portal:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "هنوز آماده فعال‌سازی نیست")

    def test_owner_sees_activated_badge_after_platform_activation(self):
        self.organization.city = "tehran"
        self.organization.phone = "09120000000"
        self.organization.address = "Some address"
        self.organization.description = "A senior-care company."
        self.organization.company_type = "home_care"
        self.organization.save()

        reviewer = self._reviewer()
        for doc_type in (DocumentType.REGISTRATION, DocumentType.OPERATING_LICENSE):
            from django.core.files.uploadedfile import SimpleUploadedFile

            file = SimpleUploadedFile(f"{doc_type}.pdf", PDF_BYTES, content_type="application/pdf")
            doc = DocumentService.upload_organization_document(self.organization, document_type=doc_type, file=file)
            VerificationReviewService.approve(document_id=doc.id, tenant_id=self.tenant.id, reviewer=reviewer)
        ProfileActivationService.activate_organization(self.organization.id, tenant_id=self.tenant.id, actor=reviewer)

        self.login_as_admin()
        response = self.client.get(reverse("organization_portal:profile"))
        self.assertContains(response, "فعال‌شده توسط پلتفرم")
