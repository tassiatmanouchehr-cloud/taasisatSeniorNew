from apps.notifications.models import Notification, NotificationChannel, NotificationStatus

from .helpers import PortalTestCase


class NotificationsViewTest(PortalTestCase):
    def _create_notification(self, *, recipient_id, status=NotificationStatus.PENDING):
        return Notification.objects.create(
            tenant=self.tenant,
            recipient=recipient_id,
            channel=NotificationChannel.IN_APP,
            status=status,
            payload={},
        )

    def test_notifications_view_lists_only_own_notifications(self):
        self._create_notification(recipient_id=self.customer.person_id)
        self._create_notification(recipient_id=self.other_customer.person_id)
        self.login_as_customer()
        response = self.client.get("/portal/notifications/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["notifications"]), 1)

    def test_unread_filter_excludes_read_notifications(self):
        self._create_notification(recipient_id=self.customer.person_id, status=NotificationStatus.PENDING)
        self._create_notification(recipient_id=self.customer.person_id, status=NotificationStatus.SENT)
        self.login_as_customer()
        response = self.client.get("/portal/notifications/?filter=unread")
        self.assertEqual(len(response.context["notifications"]), 1)
        self.assertEqual(response.context["notifications"][0].status, NotificationStatus.PENDING)
