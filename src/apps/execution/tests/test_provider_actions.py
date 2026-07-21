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
            tenant=self.tenant,
            name="Home Care",
            slug="home-care",
            status=CatalogStatus.ACTIVE,
        )
        self.order = Order.objects.create(
            tenant=self.tenant,
            source=OrderSource.OPERATOR,
            status=OrderStatus.NEW,
            service_category=self.category,
            description="x",
            city="tehran",
            address="addr",
            phone="0912",
        )
        self.provider_user, self.supplier = self._create_provider()
        self.other_provider_user, self.other_supplier = self._create_provider(phone="09123334455")

        self.assignment = AssignmentService.assign(order_id=self.order.id, supplier=self.supplier)
        self.session = ExecutionService.create_session(
            supplier_assignment=self.assignment,
            execution_source=ExecutionSource.BOOKING,
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


class CrossTenantExecutionIsolationTest(TestCase):
    """A provider registered in Tenant A must not be able to view, start, or
    complete an ExecutionSession that belongs to Tenant B — using their own
    (correct) tenant_id/supplier, targeting another tenant's order_id."""

    def setUp(self):
        self.tenant_a = Tenant.objects.create(slug=f"tena-{uuid.uuid4().hex[:8]}", name="Tenant A")
        self.tenant_b = Tenant.objects.create(slug=f"tenb-{uuid.uuid4().hex[:8]}", name="Tenant B")

        self.category_a = ServiceCategory.objects.create(
            tenant=self.tenant_a,
            name="Home Care",
            slug="home-care",
            status=CatalogStatus.ACTIVE,
        )
        self.category_b = ServiceCategory.objects.create(
            tenant=self.tenant_b,
            name="Home Care",
            slug="home-care",
            status=CatalogStatus.ACTIVE,
        )

        self.order_a = Order.objects.create(
            tenant=self.tenant_a,
            source=OrderSource.OPERATOR,
            status=OrderStatus.NEW,
            service_category=self.category_a,
            description="x",
            city="tehran",
            address="addr",
            phone="0912",
        )
        self.order_b = Order.objects.create(
            tenant=self.tenant_b,
            source=OrderSource.OPERATOR,
            status=OrderStatus.NEW,
            service_category=self.category_b,
            description="x",
            city="tehran",
            address="addr",
            phone="0912",
        )

        self.provider_a, self.supplier_a = self._create_provider(tenant=self.tenant_a, phone="09121110003")
        self.provider_b, self.supplier_b = self._create_provider(tenant=self.tenant_b, phone="09121110004")

        self.assignment_a = AssignmentService.assign(order_id=self.order_a.id, supplier=self.supplier_a)
        self.assignment_b = AssignmentService.assign(order_id=self.order_b.id, supplier=self.supplier_b)
        self.session_a = ExecutionService.create_session(
            supplier_assignment=self.assignment_a,
            execution_source=ExecutionSource.BOOKING,
        )
        self.session_b = ExecutionService.create_session(
            supplier_assignment=self.assignment_b,
            execution_source=ExecutionSource.BOOKING,
        )

    def _create_provider(self, *, tenant, phone):
        person = Person.objects.create(tenant=tenant, full_name="Provider")
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)
        CaregiverProfile.objects.create(user=user, person=person, phone=phone, display_name="Provider")
        supplier = resolve_supplier_for_user(user)
        return user, supplier

    def test_list_active_never_includes_another_tenants_session(self):
        from apps.execution.services.queries import ProviderExecutionQueryService

        ProviderExecutionService.start_visit(session_id=self.session_a.id, actor=self.provider_a)
        ProviderExecutionService.start_visit(session_id=self.session_b.id, actor=self.provider_b)

        results = ProviderExecutionQueryService.list_active_for_supplier(
            supplier=self.supplier_a,
            tenant_id=self.tenant_a.id,
        )
        self.assertEqual([s.id for s in results], [self.session_a.id])

    def test_get_for_order_and_supplier_cannot_view_another_tenants_session(self):
        from apps.execution.services.queries import ProviderExecutionQueryService

        result = ProviderExecutionQueryService.get_for_order_and_supplier(
            order_id=self.order_b.id,
            supplier=self.supplier_a,
            tenant_id=self.tenant_a.id,
        )
        self.assertIsNone(result)

    def test_start_visit_cannot_reach_another_tenants_session(self):
        with self.assertRaises(ProviderExecutionActionError):
            ProviderExecutionService.start_visit(session_id=self.session_b.id, actor=self.provider_a)

        self.session_b.refresh_from_db()
        self.assertEqual(self.session_b.status, ExecutionSessionStatus.SCHEDULED)

    def test_complete_visit_cannot_reach_another_tenants_session(self):
        ProviderExecutionService.start_visit(session_id=self.session_b.id, actor=self.provider_b)

        with self.assertRaises(ProviderExecutionActionError):
            ProviderExecutionService.complete_visit(session_id=self.session_b.id, actor=self.provider_a)

        self.session_b.refresh_from_db()
        self.assertEqual(self.session_b.status, ExecutionSessionStatus.IN_PROGRESS)


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
