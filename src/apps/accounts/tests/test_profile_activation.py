"""ProfileActivationService — Phase 1.3 Parts B, C, E, corrected in the
Phase 1.3 remediation (PR #5): `profile.status` is the sole source of
truth for current activation state; `AuditLog` is historical evidence of
the DRAFT -> ACTIVE transition only, never the activation signal itself."""

import threading
import uuid
from datetime import timedelta

from django.apps import apps as django_apps
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from apps.accounts.models.media import DocumentType
from apps.accounts.models.profiles import CaregiverProfile, OrganizationProfile, ProfileStatus
from apps.accounts.permission_keys import ACCOUNTS_DOCUMENT_REVIEW, ACCOUNTS_PROFILE_ACTIVATE
from apps.accounts.services.document_service import DocumentService
from apps.accounts.services.errors import AccountsError
from apps.accounts.services.profile_activation_service import (
    ProfileActivationError,
    ProfileActivationService,
)
from apps.accounts.services.verification_review_service import VerificationReviewService
from apps.kernel.models import Person, Tenant, UserAccount
from apps.kernel.models.audit import AuditLog
from apps.kernel.services.errors import PermissionDenied
from apps.kernel.tests.rbac_helpers import grant_permissions

PDF_BYTES = b"%PDF-1.4 fake test content"


class _ActivationFixtureMixin:
    def _build_fixture(self):
        self.tenant = Tenant.objects.create(slug=f"activate-{uuid.uuid4().hex[:8]}", name="Activation Test Tenant")
        self.other_tenant = Tenant.objects.create(slug=f"activate-other-{uuid.uuid4().hex[:8]}", name="Other Tenant")
        self.caregiver = self._create_caregiver(tenant=self.tenant)
        self.organization = self._create_organization(tenant=self.tenant)
        self.reviewer = self._create_user(tenant=self.tenant, full_name="Reviewer")
        grant_permissions(self.tenant, self.reviewer, [ACCOUNTS_DOCUMENT_REVIEW, ACCOUNTS_PROFILE_ACTIVATE])

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

    def _create_user(self, *, tenant, full_name="Test User") -> UserAccount:
        phone = f"0912{uuid.uuid4().hex[:7]}"
        person = Person.objects.create(tenant=tenant, full_name=full_name)
        return UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)

    def _approve_required_caregiver_documents(self, caregiver=None):
        caregiver = caregiver or self.caregiver
        for doc_type in (DocumentType.IDENTITY, DocumentType.BACKGROUND_CHECK):
            file = SimpleUploadedFile(f"{doc_type}.pdf", PDF_BYTES, content_type="application/pdf")
            doc = DocumentService.upload_caregiver_document(caregiver, document_type=doc_type, file=file)
            VerificationReviewService.approve(document_id=doc.id, tenant_id=self.tenant.id, reviewer=self.reviewer)

    def _approve_required_organization_documents(self, organization=None):
        organization = organization or self.organization
        for doc_type in (DocumentType.REGISTRATION, DocumentType.OPERATING_LICENSE):
            file = SimpleUploadedFile(f"{doc_type}.pdf", PDF_BYTES, content_type="application/pdf")
            doc = DocumentService.upload_organization_document(organization, document_type=doc_type, file=file)
            VerificationReviewService.approve(document_id=doc.id, tenant_id=self.tenant.id, reviewer=self.reviewer)


class EligibleCaregiverActivationTest(_ActivationFixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()

    def test_draft_caregiver_activates_to_active(self):
        self.assertEqual(self.caregiver.status, ProfileStatus.DRAFT)
        self._approve_required_caregiver_documents()
        result = ProfileActivationService.activate_caregiver(
            self.caregiver.id,
            tenant_id=self.tenant.id,
            actor=self.reviewer,
        )
        self.assertEqual(result.previous_status, ProfileStatus.DRAFT)
        self.assertEqual(result.status, ProfileStatus.ACTIVE)
        self.assertTrue(result.transitioned)

    def test_activation_persists_profile_status(self):
        self._approve_required_caregiver_documents()
        ProfileActivationService.activate_caregiver(self.caregiver.id, tenant_id=self.tenant.id, actor=self.reviewer)
        self.caregiver.refresh_from_db()
        self.assertEqual(self.caregiver.status, ProfileStatus.ACTIVE)
        self.assertTrue(ProfileActivationService.is_activated(self.caregiver))

    def test_audit_log_records_draft_to_active_transition(self):
        self._approve_required_caregiver_documents()
        ProfileActivationService.activate_caregiver(self.caregiver.id, tenant_id=self.tenant.id, actor=self.reviewer)
        entry = AuditLog.objects.get(
            tenant_id=self.tenant.id,
            resource_type="CaregiverProfile",
            resource_id=self.caregiver.id,
            action="accounts.profile.activated",
        )
        self.assertEqual(entry.actor_id, self.reviewer.person_id)
        self.assertEqual(entry.before_snapshot["status"], ProfileStatus.DRAFT)
        self.assertEqual(entry.after_snapshot["status"], ProfileStatus.ACTIVE)

    def test_repeated_activation_is_idempotent(self):
        self._approve_required_caregiver_documents()
        first = ProfileActivationService.activate_caregiver(
            self.caregiver.id,
            tenant_id=self.tenant.id,
            actor=self.reviewer,
        )
        second = ProfileActivationService.activate_caregiver(
            self.caregiver.id,
            tenant_id=self.tenant.id,
            actor=self.reviewer,
        )
        self.assertTrue(first.transitioned)
        self.assertFalse(second.transitioned)
        self.assertEqual(second.status, ProfileStatus.ACTIVE)
        count = AuditLog.objects.filter(
            tenant_id=self.tenant.id,
            resource_type="CaregiverProfile",
            resource_id=self.caregiver.id,
            action="accounts.profile.activated",
        ).count()
        self.assertEqual(count, 1, "repeated activation must not create a duplicate effective audit entry")

    def test_already_active_caregiver_activation_does_not_requery_eligibility(self):
        """An already-ACTIVE profile stays activatable (idempotent) even if
        it would no longer pass a fresh eligibility check — activation
        must not be silently undone by a later-invalidated eligibility
        state; that is the explicitly deferred deactivation workflow."""
        self._approve_required_caregiver_documents()
        ProfileActivationService.activate_caregiver(self.caregiver.id, tenant_id=self.tenant.id, actor=self.reviewer)

        doc = self.caregiver.documents.get(document_type=DocumentType.IDENTITY)
        doc.expiry_date = timezone.now().date() - timedelta(days=1)
        doc.save(update_fields=["expiry_date"])

        result = ProfileActivationService.activate_caregiver(
            self.caregiver.id,
            tenant_id=self.tenant.id,
            actor=self.reviewer,
        )
        self.assertFalse(result.transitioned)
        self.assertEqual(result.status, ProfileStatus.ACTIVE)


class EligibleOrganizationActivationTest(_ActivationFixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()

    def test_draft_organization_activates_to_active(self):
        self.assertEqual(self.organization.status, ProfileStatus.DRAFT)
        self._approve_required_organization_documents()
        result = ProfileActivationService.activate_organization(
            self.organization.id,
            tenant_id=self.tenant.id,
            actor=self.reviewer,
        )
        self.assertEqual(result.previous_status, ProfileStatus.DRAFT)
        self.assertEqual(result.status, ProfileStatus.ACTIVE)
        self.assertTrue(result.transitioned)

    def test_activation_persists_profile_status(self):
        self._approve_required_organization_documents()
        ProfileActivationService.activate_organization(
            self.organization.id,
            tenant_id=self.tenant.id,
            actor=self.reviewer,
        )
        self.organization.refresh_from_db()
        self.assertEqual(self.organization.status, ProfileStatus.ACTIVE)
        self.assertTrue(ProfileActivationService.is_activated(self.organization))

    def test_repeated_activation_is_idempotent(self):
        self._approve_required_organization_documents()
        ProfileActivationService.activate_organization(
            self.organization.id,
            tenant_id=self.tenant.id,
            actor=self.reviewer,
        )
        ProfileActivationService.activate_organization(
            self.organization.id,
            tenant_id=self.tenant.id,
            actor=self.reviewer,
        )
        count = AuditLog.objects.filter(
            tenant_id=self.tenant.id,
            resource_type="OrganizationProfile",
            resource_id=self.organization.id,
            action="accounts.profile.activated",
        ).count()
        self.assertEqual(count, 1)


class IneligibleActivationRefusalTest(_ActivationFixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()

    def test_ineligible_draft_caregiver_activation_raises_controlled_error_with_reasons(self):
        with self.assertRaises(ProfileActivationError) as ctx:
            ProfileActivationService.activate_caregiver(
                self.caregiver.id, tenant_id=self.tenant.id, actor=self.reviewer
            )
        self.assertTrue(ctx.exception.result.reasons)
        self.caregiver.refresh_from_db()
        self.assertEqual(self.caregiver.status, ProfileStatus.DRAFT)
        self.assertFalse(ProfileActivationService.is_activated(self.caregiver))

    def test_verification_required_documents_not_approved_blocks_activation(self):
        file = SimpleUploadedFile("id.pdf", PDF_BYTES, content_type="application/pdf")
        DocumentService.upload_caregiver_document(self.caregiver, document_type=DocumentType.IDENTITY, file=file)
        with self.assertRaises(ProfileActivationError):
            ProfileActivationService.activate_caregiver(
                self.caregiver.id, tenant_id=self.tenant.id, actor=self.reviewer
            )

    def test_expired_required_document_blocks_activation(self):
        self._approve_required_caregiver_documents()
        doc = self.caregiver.documents.get(document_type=DocumentType.IDENTITY)
        doc.expiry_date = timezone.now().date() - timedelta(days=1)
        doc.save(update_fields=["expiry_date"])

        with self.assertRaises(ProfileActivationError):
            ProfileActivationService.activate_caregiver(
                self.caregiver.id, tenant_id=self.tenant.id, actor=self.reviewer
            )

    def test_suspended_profile_cannot_be_activated(self):
        self._approve_required_caregiver_documents()
        self.caregiver.status = ProfileStatus.SUSPENDED
        self.caregiver.save(update_fields=["status"])
        with self.assertRaises(ProfileActivationError) as ctx:
            ProfileActivationService.activate_caregiver(
                self.caregiver.id, tenant_id=self.tenant.id, actor=self.reviewer
            )
        self.assertTrue(any(r.startswith("profile_status_blocked") for r in ctx.exception.result.reasons))
        self.caregiver.refresh_from_db()
        self.assertEqual(self.caregiver.status, ProfileStatus.SUSPENDED)

    def test_suspended_organization_cannot_be_activated(self):
        self._approve_required_organization_documents()
        self.organization.status = ProfileStatus.SUSPENDED
        self.organization.save(update_fields=["status"])
        with self.assertRaises(ProfileActivationError):
            ProfileActivationService.activate_organization(
                self.organization.id,
                tenant_id=self.tenant.id,
                actor=self.reviewer,
            )


class AuthorizationTest(_ActivationFixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()
        self._approve_required_caregiver_documents()
        self._approve_required_organization_documents()

    def test_unauthorized_actor_denied(self):
        ordinary = self._create_user(tenant=self.tenant, full_name="Ordinary")
        with self.assertRaises(PermissionDenied):
            ProfileActivationService.activate_caregiver(self.caregiver.id, tenant_id=self.tenant.id, actor=ordinary)

    def test_cross_tenant_activation_denied(self):
        other_reviewer = self._create_user(tenant=self.other_tenant, full_name="Other Tenant Reviewer")
        grant_permissions(self.other_tenant, other_reviewer, [ACCOUNTS_PROFILE_ACTIVATE])
        with self.assertRaises(AccountsError):
            ProfileActivationService.activate_caregiver(
                self.caregiver.id,
                tenant_id=self.other_tenant.id,
                actor=other_reviewer,
            )

    def test_caregiver_cannot_self_activate(self):
        grant_permissions(self.tenant, self.caregiver.user, [ACCOUNTS_PROFILE_ACTIVATE])
        with self.assertRaises(AccountsError):
            ProfileActivationService.activate_caregiver(
                self.caregiver.id,
                tenant_id=self.tenant.id,
                actor=self.caregiver.user,
            )

    def test_organization_admin_cannot_self_activate(self):
        grant_permissions(self.tenant, self.organization.admin_user, [ACCOUNTS_PROFILE_ACTIVATE])
        with self.assertRaises(AccountsError):
            ProfileActivationService.activate_organization(
                self.organization.id,
                tenant_id=self.tenant.id,
                actor=self.organization.admin_user,
            )


class EligibilitySemanticsTest(_ActivationFixtureMixin, TestCase):
    """Phase 1.3 remediation: eligibility must not require the profile to
    already be ACTIVE — that was the circular defect being fixed."""

    def setUp(self):
        self._build_fixture()

    def test_draft_caregiver_is_eligible_when_otherwise_complete(self):
        from apps.accounts.services.activation_eligibility_service import ActivationEligibilityService

        self._approve_required_caregiver_documents()
        self.assertEqual(self.caregiver.status, ProfileStatus.DRAFT)
        result = ActivationEligibilityService.evaluate_caregiver(self.caregiver)
        self.assertTrue(result.eligible, result.reasons)

    def test_draft_organization_is_eligible_when_otherwise_complete(self):
        from apps.accounts.services.activation_eligibility_service import ActivationEligibilityService

        self._approve_required_organization_documents()
        self.assertEqual(self.organization.status, ProfileStatus.DRAFT)
        result = ActivationEligibilityService.evaluate_organization(self.organization)
        self.assertTrue(result.eligible, result.reasons)

    def test_active_caregiver_remains_evaluable_as_eligible(self):
        from apps.accounts.services.activation_eligibility_service import ActivationEligibilityService

        self._approve_required_caregiver_documents()
        self.caregiver.status = ProfileStatus.ACTIVE
        self.caregiver.save(update_fields=["status"])
        result = ActivationEligibilityService.evaluate_caregiver(self.caregiver)
        self.assertTrue(result.eligible, result.reasons)


class VerificationBecomesInvalidTest(_ActivationFixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()

    def test_eligibility_becomes_false_when_verified_document_expires(self):
        from apps.accounts.services.activation_eligibility_service import ActivationEligibilityService

        self._approve_required_caregiver_documents()
        self.assertTrue(ActivationEligibilityService.evaluate_caregiver(self.caregiver).eligible)

        doc = self.caregiver.documents.get(document_type=DocumentType.IDENTITY)
        doc.expiry_date = timezone.now().date() - timedelta(days=1)
        doc.save(update_fields=["expiry_date"])

        self.assertFalse(ActivationEligibilityService.evaluate_caregiver(self.caregiver).eligible)


class ConcurrentActivationTest(_ActivationFixtureMixin, TransactionTestCase):
    """Mirrors apps.booking.tests.test_concurrency / the Phase 1.1-1.2
    TransactionTestCase pattern: two threads racing to activate the same
    DRAFT profile must leave exactly one effective ACTIVE transition, not
    two."""

    available_apps = [app_config.name for app_config in django_apps.get_app_configs()]

    def setUp(self):
        self._build_fixture()
        self._approve_required_caregiver_documents()

    def test_concurrent_activation_results_in_one_effective_change(self):
        barrier = threading.Barrier(2)
        errors = []

        def _activate():
            try:
                barrier.wait(timeout=10)
                ProfileActivationService.activate_caregiver(
                    self.caregiver.id,
                    tenant_id=self.tenant.id,
                    actor=self.reviewer,
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)
            finally:
                connection.close()

        threads = [threading.Thread(target=_activate) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)

        self.assertEqual(errors, [])
        count = AuditLog.objects.filter(
            tenant_id=self.tenant.id,
            resource_type="CaregiverProfile",
            resource_id=self.caregiver.id,
            action="accounts.profile.activated",
        ).count()
        self.assertEqual(count, 1, "concurrent activation must produce exactly one audit record")

        self.caregiver.refresh_from_db()
        self.assertEqual(
            self.caregiver.status, ProfileStatus.ACTIVE, "the profile must end in exactly one ACTIVE state"
        )


class NoAutomaticDeactivationTest(_ActivationFixtureMixin, TestCase):
    def test_activate_never_sets_a_non_active_status(self):
        """ProfileActivationService only ever moves toward ACTIVE — proves
        no automatic-deactivation behavior was introduced in this slice."""
        import inspect

        source = inspect.getsource(ProfileActivationService)
        self.assertNotIn("ProfileStatus.SUSPENDED", source)
        self.assertNotIn("ProfileStatus.ARCHIVED", source)


class AuditLogIsNotSourceOfTruthTest(_ActivationFixtureMixin, TestCase):
    """Phase 1.3 remediation: the root defect being fixed — proves
    AuditLog existence is not (and cannot be) the activation signal."""

    def setUp(self):
        self._build_fixture()

    def test_manually_written_audit_log_does_not_imply_activation(self):
        from apps.kernel.services.audit_service import AuditService

        AuditService.log(
            tenant_id=self.tenant.id,
            action="accounts.profile.activated",
            resource_type="CaregiverProfile",
            resource_id=self.caregiver.id,
            module_id="M08",
        )
        self.caregiver.refresh_from_db()
        self.assertEqual(self.caregiver.status, ProfileStatus.DRAFT)
        self.assertFalse(
            ProfileActivationService.is_activated(self.caregiver),
            "is_activated() must read profile.status, not AuditLog existence",
        )
