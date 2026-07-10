"""Assignment confirm/decline + execution start/complete — Epic 02."""

from apps.booking.models import SupplierAssignmentStatus
from apps.execution.models import ExecutionSessionStatus

from .helpers import ProviderPortalTestCase


class AssignmentDetailViewTest(ProviderPortalTestCase):
    def test_shows_assignment_for_this_order(self):
        self.assign_order_to_supplier()
        self.login_as_provider()
        response = self.client.get(f"/provider/assignments/{self.order.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.order.order_number)

    def test_returns_404_when_no_assignment_exists(self):
        self.login_as_provider()
        response = self.client.get(f"/provider/assignments/{self.order.id}/")
        self.assertEqual(response.status_code, 404)


class ConfirmAssignmentViewTest(ProviderPortalTestCase):
    def test_confirm_transitions_assignment_and_creates_execution_session(self):
        assignment = self.assign_order_to_supplier()
        self.login_as_provider()

        response = self.client.post(f"/provider/assignments/{self.order.id}/confirm/")
        self.assertRedirects(response, f"/provider/assignments/{self.order.id}/")

        assignment.refresh_from_db()
        self.assertEqual(assignment.status, SupplierAssignmentStatus.CONFIRMED)

        from apps.execution.models import ExecutionSession

        session = ExecutionSession.objects.get(order=self.order)
        self.assertEqual(session.status, ExecutionSessionStatus.SCHEDULED)
        self.assertEqual(session.supplier_assignment_id, assignment.id)

    def test_other_provider_cannot_confirm(self):
        self.assign_order_to_supplier()
        self.client.force_login(self.other_provider_user)
        response = self.client.post(f"/provider/assignments/{self.order.id}/confirm/")
        self.assertEqual(response.status_code, 404)

    def test_cross_tenant_provider_cannot_confirm(self):
        """self.provider_user (tenant A) posting confirm against an order
        that only exists, and is only assigned, in tenant B."""
        self.assign_cross_tenant_order_to_supplier()
        self.login_as_provider()
        response = self.client.post(f"/provider/assignments/{self.other_tenant_order.id}/confirm/")
        self.assertEqual(response.status_code, 404)

        from apps.booking.models import SupplierAssignment

        cross_tenant_assignment = SupplierAssignment.objects.get(order=self.other_tenant_order)
        self.assertEqual(cross_tenant_assignment.status, SupplierAssignmentStatus.ASSIGNED)


class DeclineAssignmentViewTest(ProviderPortalTestCase):
    def test_decline_transitions_assignment_and_redirects_to_list(self):
        assignment = self.assign_order_to_supplier()
        self.login_as_provider()

        response = self.client.post(
            f"/provider/assignments/{self.order.id}/decline/", {"reason": "Too far"},
        )
        self.assertRedirects(response, "/provider/assignments/")

        assignment.refresh_from_db()
        self.assertEqual(assignment.status, SupplierAssignmentStatus.DECLINED)
        self.assertEqual(assignment.metadata.get("decline_reason"), "Too far")

    def test_cross_tenant_provider_cannot_decline(self):
        cross_tenant_assignment = self.assign_cross_tenant_order_to_supplier()
        self.login_as_provider()
        response = self.client.post(
            f"/provider/assignments/{self.other_tenant_order.id}/decline/", {"reason": "Too far"},
        )
        self.assertEqual(response.status_code, 404)

        cross_tenant_assignment.refresh_from_db()
        self.assertEqual(cross_tenant_assignment.status, SupplierAssignmentStatus.ASSIGNED)
        self.assertNotIn("decline_reason", cross_tenant_assignment.metadata)


class VisitExecutionViewTest(ProviderPortalTestCase):
    def setUp(self):
        super().setUp()
        self.assignment = self.assign_order_to_supplier()
        self.login_as_provider()
        self.client.post(f"/provider/assignments/{self.order.id}/confirm/")

    def test_start_visit_transitions_session(self):
        response = self.client.post(f"/provider/assignments/{self.order.id}/start/")
        self.assertRedirects(response, f"/provider/assignments/{self.order.id}/")

        from apps.execution.models import ExecutionSession

        session = ExecutionSession.objects.get(order=self.order)
        self.assertEqual(session.status, ExecutionSessionStatus.IN_PROGRESS)

    def test_complete_visit_transitions_session(self):
        self.client.post(f"/provider/assignments/{self.order.id}/start/")
        response = self.client.post(f"/provider/assignments/{self.order.id}/complete/")
        self.assertRedirects(response, f"/provider/assignments/{self.order.id}/")

        from apps.execution.models import ExecutionSession

        session = ExecutionSession.objects.get(order=self.order)
        self.assertEqual(session.status, ExecutionSessionStatus.PROVIDER_COMPLETED)

    def test_other_provider_cannot_start(self):
        self.client.force_login(self.other_provider_user)
        response = self.client.post(f"/provider/assignments/{self.order.id}/start/")
        self.assertEqual(response.status_code, 404)


class CrossTenantVisitExecutionViewTest(ProviderPortalTestCase):
    """self.provider_user (tenant A) attempting to view or act on an
    ExecutionSession that only exists in tenant B — via the actual URLs a
    browser would hit, not just the service layer directly."""

    def setUp(self):
        super().setUp()
        self.cross_tenant_assignment = self.assign_cross_tenant_order_to_supplier()

        from apps.booking.services.provider_actions import ProviderAssignmentActionService

        ProviderAssignmentActionService.confirm(
            assignment_id=self.cross_tenant_assignment.id, actor=self.other_tenant_provider_user,
        )
        from apps.execution.models import ExecutionSource
        from apps.execution.services.session_service import ExecutionService

        self.cross_tenant_assignment.refresh_from_db()
        self.cross_tenant_session = ExecutionService.create_session(
            supplier_assignment=self.cross_tenant_assignment, execution_source=ExecutionSource.BOOKING,
        )
        self.login_as_provider()

    def test_cannot_view_cross_tenant_assignment_detail(self):
        response = self.client.get(f"/provider/assignments/{self.other_tenant_order.id}/")
        self.assertEqual(response.status_code, 404)

    def test_cannot_start_cross_tenant_session(self):
        response = self.client.post(f"/provider/assignments/{self.other_tenant_order.id}/start/")
        self.assertEqual(response.status_code, 404)

        from apps.execution.models import ExecutionSessionStatus

        self.cross_tenant_session.refresh_from_db()
        self.assertEqual(self.cross_tenant_session.status, ExecutionSessionStatus.SCHEDULED)

    def test_cannot_complete_cross_tenant_session(self):
        from apps.execution.services.provider_actions import ProviderExecutionService

        ProviderExecutionService.start_visit(
            session_id=self.cross_tenant_session.id, actor=self.other_tenant_provider_user,
        )
        response = self.client.post(f"/provider/assignments/{self.other_tenant_order.id}/complete/")
        self.assertEqual(response.status_code, 404)

        from apps.execution.models import ExecutionSessionStatus

        self.cross_tenant_session.refresh_from_db()
        self.assertEqual(self.cross_tenant_session.status, ExecutionSessionStatus.IN_PROGRESS)
