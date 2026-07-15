"""RequiredDocumentPolicy — Phase 1.2 Part A."""

import uuid
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models.media import DocumentStatus, DocumentType
from apps.accounts.services.verification_policy import (
    CAREGIVER_REQUIRED_DOCUMENT_TYPES_KEY,
    DEFAULT_CAREGIVER_REQUIRED_DOCUMENT_TYPES,
    DEFAULT_ORGANIZATION_REQUIRED_DOCUMENT_TYPES,
    ORGANIZATION_REQUIRED_DOCUMENT_TYPES_KEY,
    RequiredDocumentPolicy,
)
from apps.kernel.models import Tenant
from apps.kernel.models.configuration import ConfigurationKey, ConfigurationValue, ScopeLevel, ValueType


class DefaultPolicyTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"policy-{uuid.uuid4().hex[:8]}", name="Policy Test Tenant")

    def test_default_caregiver_required_types(self):
        result = RequiredDocumentPolicy.required_caregiver_document_types(tenant_id=self.tenant.id)
        self.assertEqual(result, DEFAULT_CAREGIVER_REQUIRED_DOCUMENT_TYPES)
        self.assertIn(DocumentType.IDENTITY, result)
        self.assertIn(DocumentType.BACKGROUND_CHECK, result)

    def test_default_organization_required_types(self):
        result = RequiredDocumentPolicy.required_organization_document_types(tenant_id=self.tenant.id)
        self.assertEqual(result, DEFAULT_ORGANIZATION_REQUIRED_DOCUMENT_TYPES)
        self.assertIn(DocumentType.REGISTRATION, result)
        self.assertIn(DocumentType.OPERATING_LICENSE, result)

    def test_optional_types_not_required_by_default(self):
        result = RequiredDocumentPolicy.required_caregiver_document_types(tenant_id=self.tenant.id)
        self.assertNotIn(DocumentType.QUALIFICATION, result)
        self.assertNotIn(DocumentType.TRAINING_CERTIFICATE, result)


class TenantOverrideTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"policy-ov-{uuid.uuid4().hex[:8]}", name="Override Tenant")

    def _set_override(self, key, value):
        config_key, _ = ConfigurationKey.objects.get_or_create(
            key=key,
            defaults={
                "owner_module": "M08",
                "scope_level": ScopeLevel.TENANT,
                "value_type": ValueType.ARRAY,
                "default_value": [],
            },
        )
        ConfigurationValue.objects.update_or_create(
            tenant_id=self.tenant.id, config_key=config_key, scope_type=ScopeLevel.TENANT,
            defaults={"value": value, "is_active": True},
        )

    def test_tenant_can_narrow_required_caregiver_types(self):
        self._set_override(CAREGIVER_REQUIRED_DOCUMENT_TYPES_KEY, [DocumentType.IDENTITY])
        result = RequiredDocumentPolicy.required_caregiver_document_types(tenant_id=self.tenant.id)
        self.assertEqual(result, (DocumentType.IDENTITY,))

    def test_tenant_can_widen_within_applicable_set(self):
        self._set_override(
            CAREGIVER_REQUIRED_DOCUMENT_TYPES_KEY,
            [DocumentType.IDENTITY, DocumentType.BACKGROUND_CHECK, DocumentType.QUALIFICATION],
        )
        result = RequiredDocumentPolicy.required_caregiver_document_types(tenant_id=self.tenant.id)
        self.assertIn(DocumentType.QUALIFICATION, result)

    def test_override_naming_a_type_outside_applicable_set_is_dropped(self):
        # REGISTRATION is organization-applicable, not caregiver-applicable.
        self._set_override(CAREGIVER_REQUIRED_DOCUMENT_TYPES_KEY, [DocumentType.IDENTITY, DocumentType.REGISTRATION])
        result = RequiredDocumentPolicy.required_caregiver_document_types(tenant_id=self.tenant.id)
        self.assertEqual(result, (DocumentType.IDENTITY,))

    def test_override_with_all_invalid_types_falls_back_to_default(self):
        self._set_override(CAREGIVER_REQUIRED_DOCUMENT_TYPES_KEY, [DocumentType.REGISTRATION])
        result = RequiredDocumentPolicy.required_caregiver_document_types(tenant_id=self.tenant.id)
        self.assertEqual(result, DEFAULT_CAREGIVER_REQUIRED_DOCUMENT_TYPES)

    def test_non_list_override_falls_back_to_default(self):
        self._set_override(ORGANIZATION_REQUIRED_DOCUMENT_TYPES_KEY, "not-a-list")
        result = RequiredDocumentPolicy.required_organization_document_types(tenant_id=self.tenant.id)
        self.assertEqual(result, DEFAULT_ORGANIZATION_REQUIRED_DOCUMENT_TYPES)

    def test_override_is_tenant_scoped(self):
        other_tenant = Tenant.objects.create(slug=f"policy-other-{uuid.uuid4().hex[:8]}", name="Other Tenant")
        self._set_override(CAREGIVER_REQUIRED_DOCUMENT_TYPES_KEY, [DocumentType.IDENTITY])
        result = RequiredDocumentPolicy.required_caregiver_document_types(tenant_id=other_tenant.id)
        self.assertEqual(result, DEFAULT_CAREGIVER_REQUIRED_DOCUMENT_TYPES)


class EffectiveExpiryTest(TestCase):
    class _Doc:
        def __init__(self, status, expiry_date):
            self.status = status
            self.expiry_date = expiry_date

    def test_verified_with_future_expiry_is_not_expired(self):
        doc = self._Doc(DocumentStatus.VERIFIED, timezone.now().date() + timedelta(days=1))
        self.assertFalse(RequiredDocumentPolicy.is_effectively_expired(doc))

    def test_verified_with_past_expiry_is_expired(self):
        doc = self._Doc(DocumentStatus.VERIFIED, timezone.now().date() - timedelta(days=1))
        self.assertTrue(RequiredDocumentPolicy.is_effectively_expired(doc))

    def test_verified_with_no_expiry_is_not_expired(self):
        doc = self._Doc(DocumentStatus.VERIFIED, None)
        self.assertFalse(RequiredDocumentPolicy.is_effectively_expired(doc))

    def test_pending_with_past_expiry_is_not_counted_expired(self):
        # expiry only matters for a document the platform already approved.
        doc = self._Doc(DocumentStatus.PENDING, timezone.now().date() - timedelta(days=1))
        self.assertFalse(RequiredDocumentPolicy.is_effectively_expired(doc))


class ExpiringSoonTest(TestCase):
    """Sprint 2.3 (Credentials, Skills, Experience, Highlights) —
    owner-facing-only "expiring soon" derived fact, a sibling of
    is_effectively_expired() with no DB status mutation."""

    class _Doc:
        def __init__(self, status, expiry_date):
            self.status = status
            self.expiry_date = expiry_date

    def test_verified_expiring_within_window_is_expiring_soon(self):
        doc = self._Doc(DocumentStatus.VERIFIED, timezone.now().date() + timedelta(days=10))
        self.assertTrue(RequiredDocumentPolicy.is_expiring_soon(doc))

    def test_verified_expiring_far_in_future_is_not_expiring_soon(self):
        doc = self._Doc(DocumentStatus.VERIFIED, timezone.now().date() + timedelta(days=365))
        self.assertFalse(RequiredDocumentPolicy.is_expiring_soon(doc))

    def test_already_expired_is_not_expiring_soon(self):
        # mutually exclusive with is_effectively_expired() — a document is
        # either already expired or expiring soon, never both.
        doc = self._Doc(DocumentStatus.VERIFIED, timezone.now().date() - timedelta(days=1))
        self.assertFalse(RequiredDocumentPolicy.is_expiring_soon(doc))
        self.assertTrue(RequiredDocumentPolicy.is_effectively_expired(doc))

    def test_verified_with_no_expiry_is_not_expiring_soon(self):
        doc = self._Doc(DocumentStatus.VERIFIED, None)
        self.assertFalse(RequiredDocumentPolicy.is_expiring_soon(doc))

    def test_pending_document_is_not_expiring_soon(self):
        doc = self._Doc(DocumentStatus.PENDING, timezone.now().date() + timedelta(days=10))
        self.assertFalse(RequiredDocumentPolicy.is_expiring_soon(doc))

    def test_expiring_exactly_at_window_boundary_is_expiring_soon(self):
        from apps.accounts.services.verification_policy import RequiredDocumentPolicy as Policy

        doc = self._Doc(DocumentStatus.VERIFIED, timezone.now().date() + timedelta(days=Policy.EXPIRING_SOON_WINDOW_DAYS))
        self.assertTrue(RequiredDocumentPolicy.is_expiring_soon(doc))
