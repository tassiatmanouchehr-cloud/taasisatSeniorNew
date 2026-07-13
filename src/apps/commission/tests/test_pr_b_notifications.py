"""Financial Core PR-B: domain events actually reach the customer as
Notification rows (Section 23) — not just logged. Exercises one
representative event (PaymentHeldInEscrow) end-to-end through the real
publish() -> EventRegistry -> handler -> Notification.objects.create()
pipeline (apps.kernel.events.handlers.register_handlers() is called from
NotificationsConfig.ready(), already wired at app-load time)."""

from apps.booking.services.assignment_service import AssignmentService
from apps.kernel.tests.rbac_helpers import grant_permissions, make_actor
from apps.notifications.models import Notification
from apps.payments.services import PaymentCallbackService, PaymentIntentService

from .helpers import CommissionTestCase


class PrBNotificationTest(CommissionTestCase):
    def setUp(self):
        super().setUp()
        self._enable_all_financial_core_pr_b_gates()
        self._seed_fixed_pricing_rule(amount="10000000")
        self.actor = make_actor(self.tenant, full_name="Assigner")
        grant_permissions(self.tenant, self.actor, ["booking.assignment.assign"])

    def test_payment_held_notifies_customer(self):
        from apps.commission.models.deadline import PaymentDeadline, PaymentDeadlineStatus
        from apps.payments.models import PaymentIntent

        order = self._make_order()
        supplier = self._make_independent_supplier()
        AssignmentService.assign(order_id=order.id, supplier=supplier, assigned_by=self.actor)

        _deadline = PaymentDeadline.objects.get(order=order, status=PaymentDeadlineStatus.PENDING)
        intent = PaymentIntent.objects.get(tenant_id=self.tenant.id, reference_type="Order", reference_id=order.id)
        attempt = PaymentIntentService.start_attempt(intent_id=intent.id)

        # transaction.on_commit callbacks (how PR-B publishes domain events)
        # never fire inside a plain TestCase's wrapping atomic block unless
        # explicitly captured and executed — this is what actually proves
        # the event reaches a real commit boundary, not just that the
        # DomainEvent object was constructed.
        with self.captureOnCommitCallbacks(execute=True):
            PaymentCallbackService.process_callback(
                provider_reference=attempt.provider_reference,
                payload={
                    "provider_reference": attempt.provider_reference,
                    "provider_event_id": "evt-1",
                    "status": "SUCCEEDED",
                    "amount": str(intent.amount),
                    "currency": intent.currency,
                },
            )

        notification = Notification.objects.get(
            tenant_id=self.tenant.id,
            recipient=order.customer_profile.person_id,
            payload__amount_irr=10000000,
        )
        self.assertEqual(notification.subject, "Payment Held")
        self.assertIn(str(order.id), notification.body)
