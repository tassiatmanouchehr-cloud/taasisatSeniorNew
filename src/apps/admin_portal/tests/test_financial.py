"""Financial Core PR-B: minimal admin-portal UI (Section 24) — Escrow
overview/detail, dispute queue/detail/resolve, release/refund overview,
feature-gate visibility."""

from apps.admin_portal import permission_keys
from apps.booking.services.assignment_service import AssignmentService
from apps.commission.models.dispute import DisputeStatus
from apps.commission.services.configuration import (
    DISPUTE_RELEASE_ENABLED_KEY,
    ESCROW_PRODUCTION_ENABLED_KEY,
    PRESERVICE_PAYMENT_ENABLED_KEY,
)
from apps.commission.services.dispute_service import DisputeService
from apps.finance.models import EscrowRecord, EscrowStatus
from apps.finance.services import FinancialPartyService
from apps.kernel.models.configuration import ConfigurationKey, ConfigurationValue, ScopeLevel, ValueType
from apps.payments.services import PaymentCallbackService, PaymentIntentService
from apps.pricing.models import PricingRule, PricingRuleType

from .helpers import AdminPortalTestCase


class AdminFinancialUiTest(AdminPortalTestCase):
    def setUp(self):
        super().setUp()
        for key in (PRESERVICE_PAYMENT_ENABLED_KEY, ESCROW_PRODUCTION_ENABLED_KEY, DISPUTE_RELEASE_ENABLED_KEY):
            config_key, _ = ConfigurationKey.objects.get_or_create(
                key=key,
                defaults={
                    "owner_module": "M05",
                    "scope_level": ScopeLevel.TENANT,
                    "value_type": ValueType.BOOLEAN,
                    "default_value": False,
                },
            )
            ConfigurationValue.objects.update_or_create(
                tenant_id=self.tenant.id,
                config_key=config_key,
                scope_type=ScopeLevel.TENANT,
                defaults={"value": True, "is_active": True},
            )
        PricingRule.objects.create(
            tenant=self.tenant,
            name="Base Rate",
            rule_type=PricingRuleType.FIXED_AMOUNT,
            amount="10000000",
            is_active=True,
            priority=0,
        )
        self._grant(self.actor, self.tenant, ["booking.assignment.assign"])
        AssignmentService.assign(order_id=self.order.id, supplier=self.supplier, assigned_by=self.actor)

        from apps.commission.models.deadline import PaymentDeadline, PaymentDeadlineStatus
        from apps.payments.models import PaymentIntent

        _deadline = PaymentDeadline.objects.get(order=self.order, status=PaymentDeadlineStatus.PENDING)
        intent = PaymentIntent.objects.get(
            tenant_id=self.tenant.id,
            reference_type="Order",
            reference_id=self.order.id,
        )
        attempt = PaymentIntentService.start_attempt(intent_id=intent.id)
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
        self.escrow = EscrowRecord.objects.get(tenant_id=self.tenant.id, order=self.order, status=EscrowStatus.HELD)

        customer_party = FinancialPartyService.resolve_party_for_customer(self.order.customer_profile)
        customer_user = self.customer_profile.user
        self.dispute = DisputeService.open(
            order=self.order,
            customer_party=customer_party,
            disputed_amount_irr=1543000,
            reason_code="SERVICE_QUALITY",
            actor=customer_user,
        )

    def test_escrow_overview_requires_permission(self):
        self.client.force_login(self.actor)
        response = self.client.get("/admin-portal/financial/escrows/")
        self.assertEqual(response.status_code, 403)

    def test_escrow_overview_shows_escrow(self):
        self._grant(self.actor, self.tenant, [permission_keys.COMMISSION_ESCROW_VIEW])
        self.client.force_login(self.actor)
        response = self.client.get("/admin-portal/financial/escrows/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.order.order_number)

    def test_escrow_detail_shows_movements_and_dispute(self):
        self._grant(self.actor, self.tenant, [permission_keys.COMMISSION_ESCROW_VIEW])
        self.client.force_login(self.actor)
        response = self.client.get(f"/admin-portal/financial/escrows/{self.escrow.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1543000")

    def test_dispute_resolve_requires_dispute_resolve_permission(self):
        self._grant(self.actor, self.tenant, [permission_keys.COMMISSION_ESCROW_VIEW])
        self.client.force_login(self.actor)
        response = self.client.post(
            f"/admin-portal/financial/disputes/{self.dispute.id}/resolve/",
            {"customer_refund_amount_irr": "1543000", "reason": "test"},
        )
        self.assertEqual(response.status_code, 403)
        self.dispute.refresh_from_db()
        self.assertEqual(self.dispute.status, DisputeStatus.OPEN)

    def test_dispute_resolve_full_refund(self):
        self._grant(
            self.actor,
            self.tenant,
            [
                permission_keys.COMMISSION_ESCROW_VIEW,
                permission_keys.COMMISSION_DISPUTE_RESOLVE,
            ],
        )
        self.client.force_login(self.actor)
        response = self.client.post(
            f"/admin-portal/financial/disputes/{self.dispute.id}/resolve/",
            {"customer_refund_amount_irr": "1543000", "reason": "verified missed visit"},
        )
        self.assertEqual(response.status_code, 302)
        self.dispute.refresh_from_db()
        self.assertEqual(self.dispute.status, DisputeStatus.RESOLVED)

    def test_feature_gate_overview_shows_current_state(self):
        self._grant(self.actor, self.tenant, [permission_keys.COMMISSION_ESCROW_VIEW])
        self.client.force_login(self.actor)
        response = self.client.get("/admin-portal/financial/feature-gates/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "فعال")

    def test_release_refund_overview_loads(self):
        self._grant(self.actor, self.tenant, [permission_keys.COMMISSION_ESCROW_VIEW])
        self.client.force_login(self.actor)
        response = self.client.get("/admin-portal/financial/instructions/")
        self.assertEqual(response.status_code, 200)
