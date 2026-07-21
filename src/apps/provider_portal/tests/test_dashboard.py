from .helpers import ProviderPortalTestCase


class DashboardViewTest(ProviderPortalTestCase):
    def test_dashboard_shows_pending_assignment(self):
        self.assign_order_to_supplier()
        self.login_as_provider()
        response = self.client.get("/provider/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.order.order_number)

    def test_dashboard_never_shows_another_providers_assignment(self):
        from apps.booking.services.assignment_service import AssignmentService

        AssignmentService.assign(order_id=self.order.id, supplier=self.other_supplier)
        self.login_as_provider()
        response = self.client.get("/provider/")
        self.assertNotContains(response, self.order.order_number)


class EarningsViewTest(ProviderPortalTestCase):
    def test_earnings_view_renders_with_no_wallet(self):
        self.login_as_provider()
        response = self.client.get("/provider/earnings/")
        self.assertEqual(response.status_code, 200)


class NotificationsViewTest(ProviderPortalTestCase):
    def test_unread_filter(self):
        from apps.notifications.models import Notification, NotificationChannel, NotificationStatus

        Notification.objects.create(
            tenant=self.tenant,
            recipient=self.provider_user.person_id,
            channel=NotificationChannel.IN_APP,
            status=NotificationStatus.PENDING,
            payload={},
        )
        self.login_as_provider()
        response = self.client.get("/provider/notifications/?filter=unread")
        self.assertEqual(len(response.context["notifications"]), 1)
