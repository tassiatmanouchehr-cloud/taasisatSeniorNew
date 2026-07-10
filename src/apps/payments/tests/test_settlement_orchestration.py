"""
Tests for SettlementOrchestrationService — Sprint 1 (Epic 03, Financial
Settlement & Money Flow).

Covers the full money flow wired by Sprint 1: PaymentIntent (SUCCEEDED)
-> FinancialDocument/FinancialObligation resolution -> PaymentTransaction
-> balanced LedgerEntry group -> Wallet credit -> domain events. Also
covers the documented Sprint 1 boundaries: idempotency, escrow
warn-and-fallback, tenant isolation, non-Order references, and a missing
FinancialDocument.
"""

import uuid
from decimal import Decimal

from django.test import TestCase

from apps.accounts.models.profiles import CustomerProfile
from apps.booking.services.assignment_service import AssignmentService
from apps.execution.services.session_service import ExecutionService
from apps.finance.models import (
    FinancialDocument,
    FinancialDocumentStatus,
    FinancialObligation,
    LedgerEntry,
    ObligationStatus,
    PaymentTransaction,
)
from apps.finance.models import PaymentStatus as FinancePaymentStatus
from apps.finance.services import FinancialDocumentService, FinancialPartyService
from apps.kernel.models import Person, Tenant, UserAccount
from apps.kernel.models.audit import AuditLog
from apps.kernel.models.configuration import ConfigurationKey, ConfigurationValue, ScopeLevel, ValueType
from apps.kernel.models.supplier import (
    AvailabilityStatus,
    ServiceSupplier,
    SupplierStatus,
    SupplierType,
    VerificationLevel,
)
from apps.orders.models import CatalogStatus, Order, OrderSource, OrderStatus, ServiceCategory
from apps.payments.models import PaymentStatus as PaymentsPaymentStatus
from apps.payments.services import PaymentCallbackService, PaymentIntentService, SettlementError
from apps.payments.services.settlement_orchestration_service import (
    ACCOUNT_CASH_COLLECTED,
    ACCOUNT_RECEIVABLE_SETTLED,
    SettlementOrchestrationService,
)
from apps.wallet.models import Wallet, WalletTransaction
from apps.wallet.services import WalletService


class SettlementOrchestrationTestCase(TestCase):
    """Tenant, order, assigned supplier, closed execution session, DRAFT invoice, Order-referencing intent."""

    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"settle-{uuid.uuid4().hex[:8]}", name="Settlement Test Tenant")
        self.other_tenant = Tenant.objects.create(slug=f"settle-other-{uuid.uuid4().hex[:8]}", name="Other Tenant")

        self.category = ServiceCategory.objects.create(
            tenant=self.tenant, name="Home Care", slug="home-care", status=CatalogStatus.ACTIVE,
        )
        self.customer_profile = self._create_customer(tenant=self.tenant)
        self.order = Order.objects.create(
            tenant=self.tenant, source=OrderSource.OPERATOR, status=OrderStatus.NEW,
            service_category=self.category, customer_profile=self.customer_profile,
            description="Need home care", city="tehran", address="Some address", phone="09120000000",
        )
        self.supplier = ServiceSupplier.objects.create(
            tenant_id=self.tenant.id, supplier_type=SupplierType.INDEPENDENT_PROVIDER,
            linked_entity_id=uuid.uuid4(), linked_entity_type="TestProfile", display_name="Test Supplier",
            status=SupplierStatus.ACTIVE, availability_status=AvailabilityStatus.AVAILABLE,
            verification_level=VerificationLevel.BASIC, service_categories=[str(self.category.id)],
        )
        self.supplier_assignment = AssignmentService.assign(order_id=self.order.id, supplier=self.supplier)
        self.order.refresh_from_db()

        session = ExecutionService.create_session(supplier_assignment=self.supplier_assignment)
        ExecutionService.start_session(session_id=session.id)
        ExecutionService.complete_session(session_id=session.id)
        self.execution_session = ExecutionService.close_session(session_id=session.id)

        self.document = FinancialDocumentService.create_invoice_from_execution(
            execution_session_id=self.execution_session.id, items=self._invoice_items(),
        )
        self.total_amount = self.document.total_amount

        self.payer_party = FinancialPartyService.resolve_party_for_customer(self.customer_profile)
        self.intent = PaymentIntentService.create_intent(
            payer_party=self.payer_party, amount=self.total_amount,
            idempotency_key=f"intent-{uuid.uuid4().hex[:12]}",
            reference_type="Order", reference_id=self.order.id,
        )

    def _create_customer(self, *, tenant, display_name="Test Customer", phone=None) -> CustomerProfile:
        phone = phone or f"0912{uuid.uuid4().hex[:7]}"
        person = Person.objects.create(tenant=tenant, full_name=display_name)
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)
        return CustomerProfile.objects.create(user=user, person=person, phone=phone, display_name=display_name)

    @staticmethod
    def _invoice_items():
        return [
            {"item_type": "SERVICE", "description": "Home care visit", "quantity": 2, "unit_price": "500000"},
            {"item_type": "TRAVEL", "description": "Travel fee", "quantity": 1, "unit_price": "50000"},
        ]

    def _mark_intent_succeeded_via_callback(self):
        attempt = PaymentIntentService.start_attempt(intent_id=self.intent.id)
        payload = {
            "provider_reference": attempt.provider_reference,
            "provider_event_id": f"evt-{uuid.uuid4().hex[:12]}",
            "status": "SUCCEEDED",
            "amount": str(self.intent.amount),
            "currency": self.intent.currency,
        }
        return PaymentCallbackService.process_callback(
            provider_reference=attempt.provider_reference, payload=payload,
        )

    def _disable_escrow(self):
        config_key = ConfigurationKey.objects.create(
            key="financial.escrow.enabled", owner_module="M05",
            scope_level=ScopeLevel.TENANT, value_type=ValueType.BOOLEAN, default_value=True,
        )
        ConfigurationValue.objects.create(
            tenant_id=self.tenant.id, config_key=config_key, scope_type=ScopeLevel.TENANT,
            value=False, is_active=True,
        )


class SettlementHappyPathTest(SettlementOrchestrationTestCase):
    def test_callback_triggers_full_settlement(self):
        with self.captureOnCommitCallbacks(execute=True):
            self._mark_intent_succeeded_via_callback()

        beneficiary_party = FinancialPartyService.resolve_party_for_supplier(self.supplier)

        payment = PaymentTransaction.objects.get(provider_reference=str(self.intent.id))
        self.assertEqual(payment.status, FinancePaymentStatus.SUCCEEDED)
        self.assertEqual(payment.amount, self.total_amount)
        self.assertEqual(payment.payer_party_id, self.payer_party.id)
        self.assertEqual(payment.receiver_party_id, beneficiary_party.id)

        self.document.refresh_from_db()
        self.assertEqual(self.document.status, FinancialDocumentStatus.PAID)

        obligation = FinancialObligation.objects.get(source_document=self.document)
        self.assertEqual(obligation.status, ObligationStatus.RESOLVED)

        entries = list(LedgerEntry.objects.filter(payment_transaction=payment).order_by("entry_type"))
        self.assertEqual(len(entries), 2)
        by_account = {entry.account_code: entry for entry in entries}
        self.assertEqual(by_account[ACCOUNT_CASH_COLLECTED].amount, self.total_amount)
        self.assertEqual(by_account[ACCOUNT_RECEIVABLE_SETTLED].amount, self.total_amount)
        debit_total = sum(e.amount for e in entries if e.entry_type == "DEBIT")
        credit_total = sum(e.amount for e in entries if e.entry_type == "CREDIT")
        self.assertEqual(debit_total, credit_total)

        wallet = Wallet.objects.get(tenant_id=self.tenant.id, party=beneficiary_party)
        self.assertEqual(wallet.balance, self.total_amount)
        wallet_txn = WalletTransaction.objects.get(wallet=wallet, idempotency_key=f"settlement:{self.intent.id}")
        self.assertEqual(wallet_txn.amount, self.total_amount)

        self.assertTrue(
            AuditLog.objects.filter(tenant_id=self.tenant.id, action="domain_event.PaymentSettled").exists(),
        )
        self.assertTrue(
            AuditLog.objects.filter(
                tenant_id=self.tenant.id, action="domain_event.ProviderEarningsCredited",
            ).exists(),
        )

    def test_settlement_auto_issues_a_draft_document(self):
        self.assertEqual(self.document.status, FinancialDocumentStatus.DRAFT)
        self._mark_intent_succeeded_via_callback()
        self.document.refresh_from_db()
        self.assertIn(self.document.status, (FinancialDocumentStatus.PAID, FinancialDocumentStatus.PARTIALLY_PAID))


class SettlementIdempotencyTest(SettlementOrchestrationTestCase):
    def test_settling_the_same_intent_twice_does_not_duplicate_side_effects(self):
        self.intent.status = PaymentsPaymentStatus.SUCCEEDED
        self.intent.save(update_fields=["status"])

        first = SettlementOrchestrationService.settle_payment_intent(payment_intent_id=self.intent.id)
        second = SettlementOrchestrationService.settle_payment_intent(payment_intent_id=self.intent.id)

        self.assertEqual(first.id, second.id)
        self.assertEqual(PaymentTransaction.objects.filter(provider_reference=str(self.intent.id)).count(), 1)

        beneficiary_party = FinancialPartyService.resolve_party_for_supplier(self.supplier)
        wallet = WalletService.get_or_create_wallet(party=beneficiary_party, currency=self.intent.currency)
        self.assertEqual(wallet.balance, self.total_amount)
        self.assertEqual(WalletTransaction.objects.filter(wallet=wallet).count(), 1)

    def test_duplicate_provider_callback_settles_only_once(self):
        attempt = PaymentIntentService.start_attempt(intent_id=self.intent.id)
        event_id = f"evt-{uuid.uuid4().hex[:12]}"
        payload = {
            "provider_reference": attempt.provider_reference, "provider_event_id": event_id,
            "status": "SUCCEEDED", "amount": str(self.intent.amount), "currency": self.intent.currency,
        }

        PaymentCallbackService.process_callback(provider_reference=attempt.provider_reference, payload=payload)
        result = PaymentCallbackService.process_callback(
            provider_reference=attempt.provider_reference, payload=payload,
        )

        self.assertTrue(result.idempotent_replay)
        self.assertEqual(PaymentTransaction.objects.filter(provider_reference=str(self.intent.id)).count(), 1)


class SettlementEscrowPolicyTest(SettlementOrchestrationTestCase):
    def _mark_intent_succeeded_directly(self):
        self.intent.status = PaymentsPaymentStatus.SUCCEEDED
        self.intent.save(update_fields=["status"])

    def test_escrow_enabled_by_default_logs_warning_and_settles_directly(self):
        self._mark_intent_succeeded_directly()

        with self.assertLogs("apps.payments.services.settlement_orchestration_service", level="WARNING") as logs:
            payment = SettlementOrchestrationService.settle_payment_intent(payment_intent_id=self.intent.id)

        self.assertTrue(any("Escrow" in message for message in logs.output))
        self.assertEqual(payment.status, FinancePaymentStatus.SUCCEEDED)

    def test_escrow_disabled_settles_directly_without_warning(self):
        self._mark_intent_succeeded_directly()
        self._disable_escrow()
        payment = SettlementOrchestrationService.settle_payment_intent(payment_intent_id=self.intent.id)
        self.assertEqual(payment.status, FinancePaymentStatus.SUCCEEDED)


class SettlementFailureModeTest(SettlementOrchestrationTestCase):
    def test_non_order_reference_type_raises_settlement_error(self):
        intent = PaymentIntentService.create_intent(
            payer_party=self.payer_party, amount=Decimal("1000"),
            idempotency_key=f"intent-{uuid.uuid4().hex[:12]}",
        )
        intent.status = PaymentsPaymentStatus.SUCCEEDED
        intent.save(update_fields=["status"])

        with self.assertRaises(SettlementError):
            SettlementOrchestrationService.settle_payment_intent(payment_intent_id=intent.id)

    def test_missing_financial_document_raises_settlement_error(self):
        order = Order.objects.create(
            tenant=self.tenant, source=OrderSource.OPERATOR, status=OrderStatus.NEW,
            service_category=self.category, customer_profile=self.customer_profile,
            description="No invoice yet", city="tehran", address="Some address", phone="09120000000",
        )
        supplier = ServiceSupplier.objects.create(
            tenant_id=self.tenant.id, supplier_type=SupplierType.INDEPENDENT_PROVIDER,
            linked_entity_id=uuid.uuid4(), linked_entity_type="TestProfile", display_name="Other Supplier",
            status=SupplierStatus.ACTIVE, availability_status=AvailabilityStatus.AVAILABLE,
            verification_level=VerificationLevel.BASIC, service_categories=[str(self.category.id)],
        )
        AssignmentService.assign(order_id=order.id, supplier=supplier)
        order.refresh_from_db()

        intent = PaymentIntentService.create_intent(
            payer_party=self.payer_party, amount=Decimal("1000"),
            idempotency_key=f"intent-{uuid.uuid4().hex[:12]}",
            reference_type="Order", reference_id=order.id,
        )
        intent.status = PaymentsPaymentStatus.SUCCEEDED
        intent.save(update_fields=["status"])

        with self.assertRaises(SettlementError):
            SettlementOrchestrationService.settle_payment_intent(payment_intent_id=intent.id)

    def test_callback_settlement_failure_does_not_break_callback_acceptance(self):
        """A settlement failure (e.g. no FinancialDocument) must not surface as a callback error."""
        order = Order.objects.create(
            tenant=self.tenant, source=OrderSource.OPERATOR, status=OrderStatus.NEW,
            service_category=self.category, customer_profile=self.customer_profile,
            description="No invoice yet", city="tehran", address="Some address", phone="09120000000",
        )
        supplier = ServiceSupplier.objects.create(
            tenant_id=self.tenant.id, supplier_type=SupplierType.INDEPENDENT_PROVIDER,
            linked_entity_id=uuid.uuid4(), linked_entity_type="TestProfile", display_name="Other Supplier",
            status=SupplierStatus.ACTIVE, availability_status=AvailabilityStatus.AVAILABLE,
            verification_level=VerificationLevel.BASIC, service_categories=[str(self.category.id)],
        )
        AssignmentService.assign(order_id=order.id, supplier=supplier)
        order.refresh_from_db()

        intent = PaymentIntentService.create_intent(
            payer_party=self.payer_party, amount=Decimal("1000"),
            idempotency_key=f"intent-{uuid.uuid4().hex[:12]}",
            reference_type="Order", reference_id=order.id,
        )
        attempt = PaymentIntentService.start_attempt(intent_id=intent.id)
        payload = {
            "provider_reference": attempt.provider_reference,
            "provider_event_id": f"evt-{uuid.uuid4().hex[:12]}",
            "status": "SUCCEEDED", "amount": str(intent.amount), "currency": intent.currency,
        }

        result = PaymentCallbackService.process_callback(
            provider_reference=attempt.provider_reference, payload=payload,
        )

        self.assertEqual(result.status, PaymentsPaymentStatus.SUCCEEDED)
        self.assertFalse(PaymentTransaction.objects.filter(provider_reference=str(intent.id)).exists())


class SettlementTenantIsolationTest(SettlementOrchestrationTestCase):
    def test_settlement_does_not_leak_across_tenants(self):
        self._mark_intent_succeeded_via_callback()

        self.assertFalse(FinancialDocument.objects.filter(tenant_id=self.other_tenant.id).exists())
        self.assertFalse(PaymentTransaction.objects.filter(tenant_id=self.other_tenant.id).exists())
        self.assertFalse(LedgerEntry.objects.filter(tenant_id=self.other_tenant.id).exists())
        self.assertFalse(Wallet.objects.filter(tenant_id=self.other_tenant.id).exists())


class SettlementAdjustmentPipelineTest(TestCase):
    def test_sprint1_pipeline_returns_zero_adjustments(self):
        from apps.payments.services.settlement_adjustments import SettlementAdjustmentPipeline

        result = SettlementAdjustmentPipeline.run(gross_amount=Decimal("1050000.00"))

        self.assertEqual(result.gross_amount, Decimal("1050000.00"))
        self.assertEqual(result.net_amount, Decimal("1050000.00"))
        self.assertEqual(result.commission_amount, Decimal("0.00"))
        self.assertEqual(result.tax_amount, Decimal("0.00"))
        self.assertEqual(result.discount_recovery_amount, Decimal("0.00"))
        self.assertEqual(result.adjustments, [])


class SettlementLedgerExtensionPointTest(SettlementOrchestrationTestCase):
    """Proves the commission ledger line activates once a future pipeline returns commission > 0."""

    def test_post_ledger_entries_adds_a_third_balanced_line_when_commission_is_non_zero(self):
        from apps.payments.services.settlement_adjustments import SettlementAdjustmentResult
        from apps.payments.services.settlement_orchestration_service import ACCOUNT_COMMISSION_REVENUE

        self._mark_intent_succeeded_via_callback()
        payment = PaymentTransaction.objects.get(provider_reference=str(self.intent.id))
        beneficiary_party = FinancialPartyService.resolve_party_for_supplier(self.supplier)

        gross = Decimal("1000000.00")
        commission = Decimal("100000.00")
        net = gross - commission
        adjustment = SettlementAdjustmentResult(
            gross_amount=gross, net_amount=net, commission_amount=commission,
            tax_amount=Decimal("0.00"), discount_recovery_amount=Decimal("0.00"), adjustments=[],
        )

        entries = SettlementOrchestrationService._post_ledger_entries(
            tenant_id=self.tenant.id, order=self.order, payment=payment,
            adjustment=adjustment, beneficiary_party=beneficiary_party,
        )

        self.assertEqual(len(entries), 3)
        by_account = {entry.account_code: entry for entry in entries}
        self.assertEqual(by_account[ACCOUNT_COMMISSION_REVENUE].amount, commission)
        debit_total = sum(e.amount for e in entries if e.entry_type == "DEBIT")
        credit_total = sum(e.amount for e in entries if e.entry_type == "CREDIT")
        self.assertEqual(debit_total, credit_total)
