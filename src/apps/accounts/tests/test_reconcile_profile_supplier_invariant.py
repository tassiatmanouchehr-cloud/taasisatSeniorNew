"""
Tests for the `reconcile_profile_supplier_invariant` management command —
Core Profile-ServiceSupplier Invariant Remediation, Phase 6/8.
"""

import io

from django.core.management import call_command
from django.test import TestCase

from apps.accounts.models.profiles import CaregiverProfile, OrganizationProfile, ProfileStatus
from apps.accounts.services.supplier_bridge import CAREGIVER_LINKED_TYPE, ORGANIZATION_LINKED_TYPE
from apps.kernel.models import Person, UserAccount
from apps.kernel.models.supplier import ServiceSupplier, SupplierStatus, SupplierType
from apps.kernel.services.supplier_registry import SupplierRegistry
from apps.kernel.services.tenant_service import TenantService


class ReconcileProfileSupplierInvariantCommandTest(TestCase):
    def setUp(self):
        self.tenant = TenantService.get_default_tenant()

    def _create_caregiver(self, *, status, phone="09146660001"):
        person = Person.objects.create(tenant=self.tenant, full_name="Reconcile Caregiver")
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=self.tenant)
        return CaregiverProfile.objects.create(
            user=user, person=person, phone=phone, display_name="Reconcile Caregiver", status=status,
        )

    def _create_organization(self, *, status, phone="09146660002"):
        person = Person.objects.create(tenant=self.tenant, full_name="Reconcile Org Admin")
        admin_user = UserAccount.objects.create_user(phone=phone, person=person, tenant=self.tenant)
        return OrganizationProfile.objects.create(
            name="Reconcile Org", code="RECON-ORG-1", admin_user=admin_user, tenant=self.tenant, status=status,
        )

    def _call(self, *args):
        out = io.StringIO()
        call_command("reconcile_profile_supplier_invariant", *args, stdout=out)
        return out.getvalue()

    def test_dry_run_performs_no_writes(self):
        caregiver = self._create_caregiver(status=ProfileStatus.ACTIVE)
        output = self._call("--dry-run")

        self.assertFalse(
            ServiceSupplier.objects.filter(
                linked_entity_id=caregiver.id, linked_entity_type=CAREGIVER_LINKED_TYPE,
            ).exists(),
        )
        self.assertIn("Would repair", output)
        self.assertIn("created=1", output)

    def test_missing_supplier_is_created_for_active_profile(self):
        caregiver = self._create_caregiver(status=ProfileStatus.ACTIVE)
        self._call()

        supplier = ServiceSupplier.objects.get(
            linked_entity_id=caregiver.id, linked_entity_type=CAREGIVER_LINKED_TYPE,
        )
        self.assertEqual(supplier.status, SupplierStatus.ACTIVE)
        self.assertEqual(supplier.supplier_type, SupplierType.INDEPENDENT_PROVIDER)

    def test_status_drift_is_corrected(self):
        organization = self._create_organization(status=ProfileStatus.ACTIVE)
        supplier = SupplierRegistry.get_or_create_supplier(
            tenant_id=self.tenant.id, linked_entity_id=organization.id,
            linked_entity_type=ORGANIZATION_LINKED_TYPE, supplier_type=SupplierType.ORGANIZATION,
            display_name=organization.name, status=SupplierStatus.PENDING,
        )
        output = self._call()

        supplier.refresh_from_db()
        self.assertEqual(supplier.status, SupplierStatus.ACTIVE)
        self.assertIn("reconciled=1", output)

    def test_already_correct_row_is_unchanged(self):
        caregiver = self._create_caregiver(status=ProfileStatus.ACTIVE)
        supplier = SupplierRegistry.get_or_create_supplier(
            tenant_id=self.tenant.id, linked_entity_id=caregiver.id,
            linked_entity_type=CAREGIVER_LINKED_TYPE, supplier_type=SupplierType.INDEPENDENT_PROVIDER,
            display_name=caregiver.display_name, status=SupplierStatus.ACTIVE,
        )
        version_before = supplier.version

        output = self._call()

        supplier.refresh_from_db()
        self.assertEqual(supplier.version, version_before)
        self.assertIn("already_correct=1", output)

    def test_unsafe_inconsistency_is_reported_and_skipped(self):
        """Tenant mismatch between a profile and its existing supplier is
        detected and reported, never auto-repaired — guessing which side
        is correct could cross a tenant boundary.

        (A literal duplicate (linked_entity_id, linked_entity_type) pair —
        the other named "unsafe" case — can no longer even be constructed
        via the ORM once Phase 7's UniqueConstraint is in place; that
        detection branch in the command now only ever matters for a
        database state that predates the constraint, which this
        already-migrated test database cannot reach.)"""
        from apps.kernel.models import Tenant

        mismatched_tenant = Tenant.objects.create(slug="reconcile-mismatch-tenant", name="Mismatch Tenant")
        organization = self._create_organization(status=ProfileStatus.ACTIVE)
        ServiceSupplier.objects.create(
            tenant_id=mismatched_tenant.id, linked_entity_id=organization.id,
            linked_entity_type=ORGANIZATION_LINKED_TYPE, supplier_type=SupplierType.ORGANIZATION,
            display_name=organization.name, status=SupplierStatus.PENDING,
        )
        output = self._call()

        self.assertIn("TENANT MISMATCH", output)
        self.assertIn("invalid=", output)
        supplier = ServiceSupplier.objects.get(
            linked_entity_id=organization.id, linked_entity_type=ORGANIZATION_LINKED_TYPE,
        )
        self.assertEqual(supplier.tenant_id, mismatched_tenant.id, "must not silently rewrite either side")
        self.assertEqual(supplier.status, SupplierStatus.PENDING, "must not repair a tenant-mismatched row")

    def test_repeated_execution_is_idempotent(self):
        caregiver = self._create_caregiver(status=ProfileStatus.ACTIVE)
        self._call()
        first_count = ServiceSupplier.objects.filter(
            linked_entity_id=caregiver.id, linked_entity_type=CAREGIVER_LINKED_TYPE,
        ).count()

        second_output = self._call()

        second_count = ServiceSupplier.objects.filter(
            linked_entity_id=caregiver.id, linked_entity_type=CAREGIVER_LINKED_TYPE,
        ).count()
        self.assertEqual(first_count, 1)
        self.assertEqual(second_count, 1)
        self.assertIn("already_correct=1", second_output)
