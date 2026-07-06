"""
Tests for Audit Log model and AuditService.

Covers:
- Audit record creation with full envelope
- Append-only enforcement (no update, no delete)
- AuditService.log() creates records
- AuditService convenience methods (log_security, log_financial, log_compliance)
"""

import uuid

from django.test import TestCase

from apps.kernel.models.audit import AuditClassification, AuditLog
from apps.kernel.services.audit_service import AuditService


class AuditLogModelTest(TestCase):
    """Test AuditLog model behavior."""

    def setUp(self):
        self.tenant_id = uuid.uuid4()

    def test_create_audit_record(self):
        record = AuditLog.objects.create(
            tenant_id=self.tenant_id,
            action="role.assign",
            module_id="M08",
            resource_type="RoleAssignment",
            resource_id=uuid.uuid4(),
            actor_id=uuid.uuid4(),
            audit_class=AuditClassification.SECURITY,
        )
        self.assertIsNotNone(record.id)
        self.assertIsNotNone(record.occurred_at)
        self.assertEqual(record.audit_class, AuditClassification.SECURITY)

    def test_cannot_update_audit_record(self):
        record = AuditLog.objects.create(
            tenant_id=self.tenant_id,
            action="test.action",
            module_id="M99",
            resource_type="TestResource",
        )
        record.action = "modified.action"
        with self.assertRaises(ValueError) as ctx:
            record.save()
        self.assertIn("immutable", str(ctx.exception).lower())

    def test_cannot_delete_audit_record(self):
        record = AuditLog.objects.create(
            tenant_id=self.tenant_id,
            action="test.action",
            module_id="M99",
            resource_type="TestResource",
        )
        with self.assertRaises(ValueError) as ctx:
            record.delete()
        self.assertIn("cannot be deleted", str(ctx.exception).lower())


class AuditServiceTest(TestCase):
    """Test AuditService."""

    def setUp(self):
        self.tenant_id = uuid.uuid4()

    def test_log_creates_record(self):
        record = AuditService.log(
            tenant_id=self.tenant_id,
            action="supplier.activate",
            resource_type="ServiceSupplier",
            module_id="M25",
            actor_id=uuid.uuid4(),
            resource_id=uuid.uuid4(),
            after={"status": "active"},
        )
        self.assertIsNotNone(record.id)
        self.assertEqual(record.action, "supplier.activate")
        self.assertEqual(record.audit_class, AuditClassification.STANDARD)

    def test_log_security(self):
        record = AuditService.log_security(
            tenant_id=self.tenant_id,
            action="login.failed",
            resource_type="UserAccount",
            module_id="M08",
        )
        self.assertEqual(record.audit_class, AuditClassification.SECURITY)

    def test_log_financial(self):
        record = AuditService.log_financial(
            tenant_id=self.tenant_id,
            action="payment.received",
            resource_type="PaymentTransaction",
            module_id="M05",
        )
        self.assertEqual(record.audit_class, AuditClassification.FINANCIAL)

    def test_log_compliance(self):
        record = AuditService.log_compliance(
            tenant_id=self.tenant_id,
            action="enforcement.applied",
            resource_type="EnforcementAction",
            module_id="M06",
        )
        self.assertEqual(record.audit_class, AuditClassification.COMPLIANCE)
