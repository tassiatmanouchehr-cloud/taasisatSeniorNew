"""Tests for ProviderExecutionService — Epic 02."""

import uuid

from django.test import TestCase

from apps.accounts.models.profiles import CaregiverProfile
from apps.accounts.services.provider_identity import resolve_supplier_for_user
from apps.booking.services.assignment_service import AssignmentService
from apps.execution.models import ExecutionSessionStatus, ExecutionSource
from apps.execution.services.provider_actions import ProviderExecutionActionError, ProviderExecutionService
from apps.execution.services.session_service import ExecutionService
from apps.kernel.models import Person, Tenant, UserAccount
from apps.orders.models import CatalogStatus, Order, OrderSource, OrderStatus, ServiceCategory


class ProviderExecutionActionTestCase(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"provexec-{uuid.uuid4().hex[:8]}", name="Provider Exec Tenant")
        self.category = ServiceCategory.objects.create(
            tenant=self.tenant, name="Home Care", slug="home-care", status=CatalogStatus.ACTIVE,
        )
        self.order = Order.objects.create(
            tenant=self.tenant, source=OrderSource.OPERATOR, status=OrderStatus.NEW,
            service_category=self.category, description="x", city="tehran", address="addr", phone="0912",
        )
        self.provider_user, self.supplier = self._create_provider()
        self.other_provider_user, self.other_supplier = self._create_provider(phone="09123334455")

        self.assignment = AssignmentService.assign(order_id=self.order.id, supplier=self.supplier)
        self.session = ExecutionService.create_session(
            supplier_assignment=self.assignment, execution_source=ExecutionSource.BOOKING,
        )

    def _create_provider(self, *, phone=None):
        phone = phone or f"0912{uuid.uuid4().hex[:7]}"
        person = Person.objects.create(tenant=self.tenant, full_name="Provider")
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=self.tenant)
        CaregiverProfile.objects.create(user=user, person=person, phone=phone, display_name="Provider")
        supplier = resolve_supplier_for_user(user)
        return user, supplier


class StartVisitTest(ProviderExecutionActionTestCase):
    def test_start_visit_transitions_to_in_progress(self):
        result = ProviderExecutionService.start_visit(session_id=self.session.id, actor=self.provider_user)
        self.assertEqual(result.status, ExecutionSessionStatus.IN_PROGRESS)

    def test_other_provider_cannot_start(self):
        with self.assertRaises(ProviderExecutionActionError):
            ProviderExecutionService.start_visit(session_id=self.session.id, actor=self.other_provider_user)

    def test_start_visit_unknown_session_raises(self):
        with self.assertRaises(ProviderExecutionActionError):
            ProviderExecutionService.start_visit(session_id=uuid.uuid4(), actor=self.provider_user)


class CompleteVisitTest(ProviderExecutionActionTestCase):
    def setUp(self):
        super().setUp()
        ProviderExecutionService.start_visit(session_id=self.session.id, actor=self.provider_user)

    def test_complete_visit_transitions_to_provider_completed(self):
        result = ProviderExecutionService.complete_visit(session_id=self.session.id, actor=self.provider_user)
        self.assertEqual(result.status, ExecutionSessionStatus.PROVIDER_COMPLETED)

    def test_other_provider_cannot_complete(self):
        with self.assertRaises(ProviderExecutionActionError):
            ProviderExecutionService.complete_visit(session_id=self.session.id, actor=self.other_provider_user)

    def test_complete_does_not_close_session(self):
        result = ProviderExecutionService.complete_visit(session_id=self.session.id, actor=self.provider_user)
        self.assertNotEqual(result.status, ExecutionSessionStatus.CLOSED)


class ProviderExecutionEventPublishingTest(ProviderExecutionActionTestCase):
    def test_start_visit_publishes_and_audits(self):
        from apps.kernel.models.audit import AuditLog

        with self.captureOnCommitCallbacks(execute=True):
            ProviderExecutionService.start_visit(session_id=self.session.id, actor=self.provider_user)

        entry = AuditLog.objects.get(action="domain_event.ProviderVisitStarted", resource_id=self.session.id)
        self.assertEqual(entry.resource_type, "ExecutionSession")

    def test_complete_visit_publishes_and_audits(self):
        from apps.kernel.models.audit import AuditLog

        with self.captureOnCommitCallbacks(execute=True):
            ProviderExecutionService.start_visit(session_id=self.session.id, actor=self.provider_user)
        with self.captureOnCommitCallbacks(execute=True):
            ProviderExecutionService.complete_visit(session_id=self.session.id, actor=self.provider_user)

        entry = AuditLog.objects.get(action="domain_event.ProviderVisitCompleted", resource_id=self.session.id)
        self.assertEqual(entry.resource_type, "ExecutionSession")
