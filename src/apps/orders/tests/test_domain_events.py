"""
Tests proving apps.orders.services.order_creation publishes OrderCreated
domain events after the order is successfully persisted (and only then).
"""

import uuid

from django.test import TestCase

from apps.accounts.models.profiles import CustomerProfile
from apps.kernel.events.base import ORDER_CREATED
from apps.kernel.models import Person, Tenant, UserAccount
from apps.kernel.models.audit import AuditLog
from apps.notifications.models import Notification, NotificationChannel
from apps.orders.models import CatalogStatus, ServiceCategory
from apps.orders.services.order_creation import OrderValidationError, create_operator_order, create_public_order


class OrderDomainEventTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"orderevt-{uuid.uuid4().hex[:8]}", name="Order Event Tenant")
        self.category = ServiceCategory.objects.create(
            tenant=self.tenant,
            name="Home Care",
            slug="home-care",
            status=CatalogStatus.ACTIVE,
        )
        self.customer_profile = self._create_customer()

    def _create_customer(self) -> CustomerProfile:
        phone = f"0912{uuid.uuid4().hex[:7]}"
        person = Person.objects.create(tenant=self.tenant, full_name="Test Customer")
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=self.tenant)
        return CustomerProfile.objects.create(user=user, person=person, phone=phone, display_name="Test Customer")

    def _order_kwargs(self, **overrides):
        defaults = dict(
            service_category_id=self.category.id,
            description="Need home care",
            phone="09121111111",
            address="Some address",
            city="tehran",
            customer_profile=self.customer_profile,
            tenant_id=self.tenant.id,
        )
        defaults.update(overrides)
        return defaults

    def test_create_public_order_publishes_order_created(self):
        with self.captureOnCommitCallbacks(execute=True):
            order = create_public_order(**self._order_kwargs())

        self.assertTrue(
            AuditLog.objects.filter(tenant_id=self.tenant.id, action=f"domain_event.{ORDER_CREATED}").exists(),
        )
        notification = Notification.objects.get(tenant=self.tenant)
        self.assertEqual(notification.channel, NotificationChannel.IN_APP)
        self.assertEqual(notification.recipient, self.customer_profile.person_id)
        self.assertEqual(notification.payload["order_number"], order.order_number)

    def test_create_operator_order_publishes_order_created(self):
        with self.captureOnCommitCallbacks(execute=True):
            create_operator_order(**self._order_kwargs())

        self.assertTrue(
            AuditLog.objects.filter(tenant_id=self.tenant.id, action=f"domain_event.{ORDER_CREATED}").exists(),
        )
        self.assertEqual(Notification.objects.filter(tenant=self.tenant).count(), 1)

    def test_event_is_not_published_until_commit(self):
        """Without capturing on_commit callbacks, nothing fires inside the still-open test transaction."""
        create_public_order(**self._order_kwargs())

        self.assertFalse(
            AuditLog.objects.filter(tenant_id=self.tenant.id, action=f"domain_event.{ORDER_CREATED}").exists(),
        )
        self.assertEqual(Notification.objects.filter(tenant=self.tenant).count(), 0)

    def test_failed_order_creation_does_not_publish_an_event(self):
        with self.captureOnCommitCallbacks(execute=True), self.assertRaises(OrderValidationError):
            create_public_order(**self._order_kwargs(description=""))

        self.assertFalse(
            AuditLog.objects.filter(tenant_id=self.tenant.id, action=f"domain_event.{ORDER_CREATED}").exists(),
        )
        self.assertEqual(Notification.objects.filter(tenant=self.tenant).count(), 0)
