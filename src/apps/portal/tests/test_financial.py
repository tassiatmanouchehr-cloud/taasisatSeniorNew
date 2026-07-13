"""Financial Core PR-B: minimal customer-portal UI (Section 24) —
payment-required state, Fake pay action, Escrow held status, objection
approval, dispute submission. GET/POST smoke tests through the real
Django test client, not just the underlying services (already covered in
apps.commission.tests)."""

import uuid

from apps.booking.services.assignment_service import AssignmentService
from apps.commission.services.configuration import (
    DEADLINE_ACTIVATION_ENABLED_KEY,
    DISPUTE_RELEASE_ENABLED_KEY,
    ESCROW_PRODUCTION_ENABLED_KEY,
    OBJECTION_AUTOMATION_ENABLED_KEY,
    PRESERVICE_PAYMENT_ENABLED_KEY,
)
from apps.kernel.models.configuration import ConfigurationKey, ConfigurationValue, ScopeLevel, ValueType
from apps.kernel.models.supplier import (
    AvailabilityStatus,
    ServiceSupplier,
    SupplierStatus,
    SupplierType,
    VerificationLevel,
)
from apps.kernel.tests.rbac_helpers import grant_permissions
from apps.orders.models import Order, OrderSource, OrderStatus
from apps.pricing.models import PricingRule, PricingRuleType

from .helpers import PortalTestCase


class CustomerFinancialPageTest(PortalTestCase):
    def setUp(self):
        super().setUp()
        for key in (
            PRESERVICE_PAYMENT_ENABLED_KEY,
            ESCROW_PRODUCTION_ENABLED_KEY,
            OBJECTION_AUTOMATION_ENABLED_KEY,
            DISPUTE_RELEASE_ENABLED_KEY,
            DEADLINE_ACTIVATION_ENABLED_KEY,
        ):
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
        self.order = Order.objects.create(
            tenant=self.tenant,
            source=OrderSource.OPERATOR,
            status=OrderStatus.NEW,
            service_category=self.category,
            customer_profile=self.customer,
            description="Financial UI test order",
            city="tehran",
            address="Addr",
            phone="09120000000",
        )
        self.supplier = ServiceSupplier.objects.create(
            tenant_id=self.tenant.id,
            supplier_type=SupplierType.INDEPENDENT_PROVIDER,
            linked_entity_id=uuid.uuid4(),
            linked_entity_type="TestProfile",
            display_name="Independent Caregiver",
            status=SupplierStatus.ACTIVE,
            availability_status=AvailabilityStatus.AVAILABLE,
            verification_level=VerificationLevel.BASIC,
            service_categories=[str(self.category.id)],
        )
        self.assigner = self.customer.user  # any authenticated actor works for assign() in this test
        grant_permissions(self.tenant, self.assigner, ["booking.assignment.assign"])
        AssignmentService.assign(order_id=self.order.id, supplier=self.supplier, assigned_by=self.assigner)

    def test_financial_page_shows_pay_action_before_payment(self):
        self.login_as_customer()
        response = self.client.get(f"/portal/requests/{self.order.id}/financial/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "شبیه‌سازی پرداخت موفق")

    def test_pay_action_creates_held_escrow(self):
        self.login_as_customer()
        self.client.post(f"/portal/requests/{self.order.id}/financial/pay/", {"outcome": "SUCCEEDED"})

        response = self.client.get(f"/portal/requests/{self.order.id}/financial/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "وجه در امانت")

    def test_other_customer_cannot_view_this_order_financial_page(self):
        self.client.force_login(self.other_customer.user)
        response = self.client.get(f"/portal/requests/{self.order.id}/financial/")
        self.assertEqual(response.status_code, 404)

    def test_anonymous_redirected_or_denied(self):
        response = self.client.get(f"/portal/requests/{self.order.id}/financial/")
        self.assertIn(response.status_code, (302, 403))
