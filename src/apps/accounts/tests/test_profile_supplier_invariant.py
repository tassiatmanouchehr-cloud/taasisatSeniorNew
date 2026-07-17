"""
Core Profile-ServiceSupplier Invariant Remediation — Phase 8 tests.

Covers the activation-time enforcement Phase 4 added to
`ProfileActivationService` (a real DRAFT -> ACTIVE transition must, in the
same transaction, guarantee an ACTIVE `ServiceSupplier`), its
transaction-failure/rollback behavior, and one end-to-end proof that the
real activation path (not a direct `status="active"` write) is what makes
a profile appear on the public directory.

Reuses `_ActivationFixtureMixin` from `test_profile_activation.py` — same
fixture shape, no need to duplicate it.
"""

from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.accounts.models.media import DocumentType
from apps.accounts.models.profiles import ProfileStatus
from apps.accounts.services.document_service import DocumentService
from apps.accounts.services.profile_activation_service import ProfileActivationService
from apps.accounts.services.supplier_bridge import (
    CAREGIVER_LINKED_TYPE,
    ORGANIZATION_LINKED_TYPE,
)
from apps.accounts.services.verification_review_service import VerificationReviewService
from apps.kernel.models.audit import AuditLog
from apps.kernel.models.supplier import ServiceSupplier, SupplierStatus, SupplierType
from apps.kernel.services.supplier_registry import SupplierRegistry

from .test_profile_activation import PDF_BYTES, _ActivationFixtureMixin


class SupplierSyncOnActivationTest(_ActivationFixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()

    def test_caregiver_activation_creates_correct_supplier(self):
        self._approve_required_caregiver_documents()
        ProfileActivationService.activate_caregiver(self.caregiver.id, tenant_id=self.tenant.id, actor=self.reviewer)

        supplier = SupplierRegistry.find_by_linked_entity(
            linked_entity_id=self.caregiver.id, linked_entity_type=CAREGIVER_LINKED_TYPE,
        )
        self.assertIsNotNone(supplier)
        self.assertEqual(supplier.supplier_type, SupplierType.INDEPENDENT_PROVIDER)

    def test_organization_activation_creates_correct_supplier(self):
        self._approve_required_organization_documents()
        ProfileActivationService.activate_organization(
            self.organization.id, tenant_id=self.tenant.id, actor=self.reviewer,
        )
        supplier = SupplierRegistry.find_by_linked_entity(
            linked_entity_id=self.organization.id, linked_entity_type=ORGANIZATION_LINKED_TYPE,
        )
        self.assertIsNotNone(supplier)
        self.assertEqual(supplier.supplier_type, SupplierType.ORGANIZATION)

    def test_activation_supplier_uses_the_profile_authoritative_tenant(self):
        self._approve_required_caregiver_documents()
        ProfileActivationService.activate_caregiver(self.caregiver.id, tenant_id=self.tenant.id, actor=self.reviewer)
        supplier = SupplierRegistry.find_by_linked_entity(
            linked_entity_id=self.caregiver.id, linked_entity_type=CAREGIVER_LINKED_TYPE,
        )
        self.assertEqual(supplier.tenant_id, self.tenant.id)

    def test_activation_supplier_uses_the_correct_linked_entity_type(self):
        self._approve_required_organization_documents()
        ProfileActivationService.activate_organization(
            self.organization.id, tenant_id=self.tenant.id, actor=self.reviewer,
        )
        supplier = SupplierRegistry.find_by_linked_entity(
            linked_entity_id=self.organization.id, linked_entity_type=ORGANIZATION_LINKED_TYPE,
        )
        self.assertEqual(supplier.linked_entity_type, ORGANIZATION_LINKED_TYPE)

    def test_activation_supplier_status_is_active(self):
        self._approve_required_caregiver_documents()
        ProfileActivationService.activate_caregiver(self.caregiver.id, tenant_id=self.tenant.id, actor=self.reviewer)
        supplier = SupplierRegistry.find_by_linked_entity(
            linked_entity_id=self.caregiver.id, linked_entity_type=CAREGIVER_LINKED_TYPE,
        )
        self.assertEqual(supplier.status, SupplierStatus.ACTIVE)

    def test_repeated_activation_creates_no_duplicate_supplier(self):
        self._approve_required_caregiver_documents()
        ProfileActivationService.activate_caregiver(self.caregiver.id, tenant_id=self.tenant.id, actor=self.reviewer)
        ProfileActivationService.activate_caregiver(self.caregiver.id, tenant_id=self.tenant.id, actor=self.reviewer)

        count = ServiceSupplier.objects.filter(
            linked_entity_id=self.caregiver.id, linked_entity_type=CAREGIVER_LINKED_TYPE,
        ).count()
        self.assertEqual(count, 1)

    def test_already_correct_existing_supplier_is_left_unchanged(self):
        """A supplier that already matches (ACTIVE, created via the
        sanctioned bridge before activation, e.g. by a prior repair run)
        must not be mutated again — SupplierRegistry.set_status() is a
        true no-op when the value is already correct."""
        from apps.accounts.services.supplier_bridge import get_or_create_supplier_for_caregiver

        pre_existing = get_or_create_supplier_for_caregiver(self.caregiver, tenant_id=self.tenant.id)
        SupplierRegistry.set_status(pre_existing, status=SupplierStatus.ACTIVE)
        version_before = pre_existing.version

        self._approve_required_caregiver_documents()
        ProfileActivationService.activate_caregiver(self.caregiver.id, tenant_id=self.tenant.id, actor=self.reviewer)

        pre_existing.refresh_from_db()
        self.assertEqual(pre_existing.version, version_before)

    def test_existing_incorrect_supplier_status_is_reconciled_on_activation(self):
        """A supplier that already exists but is not ACTIVE (e.g. created
        with the registry's PENDING default some other way) must be
        reconciled to ACTIVE as part of activation."""
        supplier = SupplierRegistry.get_or_create_supplier(
            tenant_id=self.tenant.id,
            linked_entity_id=self.caregiver.id,
            linked_entity_type=CAREGIVER_LINKED_TYPE,
            supplier_type=SupplierType.INDEPENDENT_PROVIDER,
            display_name=self.caregiver.display_name,
            status=SupplierStatus.PENDING,
        )
        self.assertEqual(supplier.status, SupplierStatus.PENDING)

        self._approve_required_caregiver_documents()
        ProfileActivationService.activate_caregiver(self.caregiver.id, tenant_id=self.tenant.id, actor=self.reviewer)

        supplier.refresh_from_db()
        self.assertEqual(supplier.status, SupplierStatus.ACTIVE)


class ActivationSupplierSyncFailureTest(_ActivationFixtureMixin, TestCase):
    """Phase 4: a failure while synchronizing the supplier must roll back
    the entire activation transaction — the profile transition, any
    partial supplier mutation, and the audit record all together."""

    def setUp(self):
        self._build_fixture()
        self._approve_required_caregiver_documents()

    def test_sync_failure_rolls_back_profile_activation(self):
        with patch(
            "apps.accounts.services.profile_activation_service.sync_supplier_for_profile_activation",
            side_effect=RuntimeError("simulated supplier sync failure"),
        ):
            with self.assertRaises(RuntimeError):
                ProfileActivationService.activate_caregiver(
                    self.caregiver.id, tenant_id=self.tenant.id, actor=self.reviewer,
                )

        self.caregiver.refresh_from_db()
        self.assertEqual(self.caregiver.status, ProfileStatus.DRAFT)

    def test_sync_failure_leaves_no_activation_audit_entry(self):
        with patch(
            "apps.accounts.services.profile_activation_service.sync_supplier_for_profile_activation",
            side_effect=RuntimeError("simulated supplier sync failure"),
        ):
            with self.assertRaises(RuntimeError):
                ProfileActivationService.activate_caregiver(
                    self.caregiver.id, tenant_id=self.tenant.id, actor=self.reviewer,
                )

        count = AuditLog.objects.filter(
            tenant_id=self.tenant.id, resource_type="CaregiverProfile", resource_id=self.caregiver.id,
            action="accounts.profile.activated",
        ).count()
        self.assertEqual(count, 0)

    def test_sync_failure_leaves_no_partial_supplier_mutation(self):
        with patch(
            "apps.accounts.services.profile_activation_service.sync_supplier_for_profile_activation",
            side_effect=RuntimeError("simulated supplier sync failure"),
        ):
            with self.assertRaises(RuntimeError):
                ProfileActivationService.activate_caregiver(
                    self.caregiver.id, tenant_id=self.tenant.id, actor=self.reviewer,
                )

        exists = ServiceSupplier.objects.filter(
            linked_entity_id=self.caregiver.id, linked_entity_type=CAREGIVER_LINKED_TYPE,
        ).exists()
        self.assertFalse(exists)


class ActivationToPublicDirectoryIntegrationTest(_ActivationFixtureMixin, TestCase):
    """The real activation path (not a direct status='active' write) must
    be sufficient, by itself, to make a verified profile appear on the
    public directory — proving Phase 4's change composes correctly with
    the pre-existing BG-022 public-visibility policy
    (apps.public_site.services.common.is_publicly_visible_attrs())."""

    def setUp(self):
        self._build_fixture()

    def test_activated_and_verified_caregiver_appears_in_directory(self):
        """Document approval (required for activation eligibility) rolls
        verification up to "verified" — no separate verify step needed."""
        from apps.public_site.services.directory_service import CaregiverDirectoryService

        self._approve_required_caregiver_documents()
        ProfileActivationService.activate_caregiver(self.caregiver.id, tenant_id=self.tenant.id, actor=self.reviewer)

        page = CaregiverDirectoryService.search(tenant_id=self.tenant.id)
        self.assertIn(self.caregiver.display_name, {c.display_name for c in page.caregivers})

    def test_activated_and_verified_organization_appears_in_directory(self):
        from apps.public_site.services.organization_directory_service import OrganizationDirectoryService

        self._approve_required_organization_documents()
        ProfileActivationService.activate_organization(
            self.organization.id, tenant_id=self.tenant.id, actor=self.reviewer,
        )

        page = OrganizationDirectoryService.search(tenant_id=self.tenant.id)
        self.assertIn(self.organization.name, {o.name for o in page.organizations})

    def test_activated_but_unverified_caregiver_stays_excluded(self):
        """Reaching ACTIVE through the real `ProfileActivationService` path
        always implies documents were approved (`ActivationEligibilityService`
        requires it), which in turn rolls verification up to "verified" —
        so an activated-but-still-unverified caregiver can only arise from a
        non-canonical direct write (e.g. a seed command), not from real
        activation. That state, and its exclusion from the directory, is
        already covered end-to-end by
        apps.public_site.tests.test_public_visibility_policy
        .CanonicalVisibilityAcrossSurfacesTest
        .test_unverified_caregiver_hidden_on_every_surface — deliberately
        not duplicated here."""
        self._approve_required_caregiver_documents()
        ProfileActivationService.activate_caregiver(self.caregiver.id, tenant_id=self.tenant.id, actor=self.reviewer)
        self.caregiver.refresh_from_db()
        self.assertEqual(
            self.caregiver.verification_status, "verified",
            "activation eligibility requires approved documents, which roll up to verified",
        )

    def test_activation_stays_tenant_isolated_in_directory_results(self):
        from apps.accounts.permission_keys import ACCOUNTS_DOCUMENT_REVIEW, ACCOUNTS_PROFILE_ACTIVATE
        from apps.kernel.tests.rbac_helpers import grant_permissions
        from apps.public_site.services.directory_service import CaregiverDirectoryService

        other_caregiver = self._create_caregiver(tenant=self.other_tenant, full_name="Other Tenant Caregiver")
        other_reviewer = self._create_user(tenant=self.other_tenant, full_name="Other Tenant Reviewer")
        grant_permissions(self.other_tenant, other_reviewer, [ACCOUNTS_DOCUMENT_REVIEW, ACCOUNTS_PROFILE_ACTIVATE])

        for doc_type in (DocumentType.IDENTITY, DocumentType.BACKGROUND_CHECK):
            file = SimpleUploadedFile(f"{doc_type}.pdf", PDF_BYTES, content_type="application/pdf")
            doc = DocumentService.upload_caregiver_document(other_caregiver, document_type=doc_type, file=file)
            VerificationReviewService.approve(document_id=doc.id, tenant_id=self.other_tenant.id, reviewer=other_reviewer)

        ProfileActivationService.activate_caregiver(
            other_caregiver.id, tenant_id=self.other_tenant.id, actor=other_reviewer,
        )

        page = CaregiverDirectoryService.search(tenant_id=self.tenant.id)
        self.assertNotIn(other_caregiver.display_name, {c.display_name for c in page.caregivers})
