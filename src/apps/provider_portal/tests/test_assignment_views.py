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
