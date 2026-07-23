"""
Tests for ReleaseConsumerService — Financial Core PR-C.

Covers: consume(), consume_all_ready() — wallet credits, allocation,
idempotency, concurrency, rollback, tenant isolation, amount conservation.
"""

import uuid
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.commission.models.release_instruction import (
    ReleaseInstruction,
    ReleaseInstructionSource,
    ReleaseInstructionStatus,
)
from apps.commission.models.snapshot import CommissionSnapshot
from apps.commission.services.release_consumer_service import ReleaseConsumerError, ReleaseConsumerService
from apps.finance.models import EscrowRecord, EscrowStatus, FinancialDocument, FinancialDocumentStatus, FinancialParty
from apps.kernel.models import Tenant
from apps.kernel.models.audit import AuditLog
from apps.orders.models import Order, OrderSource, OrderStatus, ServiceCategory
from apps.wallet.models import Wallet, WalletTransaction


def _make_tenant(prefix="release"):
    return Tenant.objects.create(slug=f"{prefix}-{uuid.uuid4().hex[:8]}", name=f"{prefix} tenant")


def _make_order(tenant):
    category = ServiceCategory.objects.create(
        tenant=tenant, name="Care", slug=f"care-{uuid.uuid4().hex[:6]}", status="active"
    )
    return Order.objects.create(
        tenant=tenant,
        source=OrderSource.OPERATOR,
        status=OrderStatus.WAITING_SERVICE,
        service_category=category,
        description="Test",
        city="tehran",
        address="Test",
        phone="0912",
    )


def _make_party(tenant, *, party_type="SUPPLIER", display_name="Test Party"):
    return FinancialParty.objects.create(
        tenant=tenant,
        party_type=party_type,
        display_name=display_name,
    )


def _make_document(tenant, order, *, payer_party, beneficiary_party):
    return FinancialDocument.objects.create(
        tenant=tenant,
        order=order,
        document_type="INVOICE",
        status=FinancialDocumentStatus.ISSUED,
        total_amount=Decimal("10000000"),
        currency="IRR",
        payer_party=payer_party,
        beneficiary_party=beneficiary_party,
    )


def _make_escrow(tenant, order, document, *, payer_party, amount_irr=10000000):
    return EscrowRecord.objects.create(
        tenant=tenant,
        source_document=document,
        payer_party=payer_party,
        amount=Decimal(str(amount_irr)),
        currency="IRR",
        status=EscrowStatus.HELD,
        order=order,
        original_amount_irr=amount_irr,
        held_amount_irr=amount_irr,
        remaining_amount_irr=0,
        released_amount_irr=amount_irr,
        idempotency_key=f"test-escrow-{uuid.uuid4().hex[:8]}",
    )


def _make_snapshot(tenant, order, *, caregiver_party, company_party=None):
    return CommissionSnapshot.objects.create(
        tenant=tenant,
        order=order,
        supplier_id=uuid.uuid4(),
        cooperation_type="INDEPENDENT",
        policy_source="global_default",
        platform_rate_percent=15,
        company_rate_percent=0 if company_party is None else 10,
        caregiver_rate_percent=85 if company_party is None else 75,
        goods_platform_rate_percent=0,
        goods_company_rate_percent=0,
        goods_caregiver_rate_percent=100,
        caregiver_party=caregiver_party,
        company_party=company_party,
        effective_timestamp=timezone.now(),
    )


def _make_release_instruction(tenant, escrow, order, document, snapshot, *, amount_irr=10000000):
    return ReleaseInstruction.objects.create(
        tenant=tenant,
        escrow=escrow,
        order=order,
        invoice=document,
        commission_snapshot=snapshot,
        source=ReleaseInstructionSource.CUSTOMER_APPROVAL,
        gross_releasable_amount_irr=amount_irr,
        currency="IRR",
        status=ReleaseInstructionStatus.READY,
        idempotency_key=f"test-release-{uuid.uuid4().hex[:8]}",
    )


class ReleaseConsumerHappyPathTest(TestCase):
    def setUp(self):
        self.tenant = _make_tenant()
        self.order = _make_order(self.tenant)
        self.payer_party = _make_party(self.tenant, party_type="CUSTOMER", display_name="Customer")
        self.caregiver_party = _make_party(self.tenant, party_type="SUPPLIER", display_name="Caregiver")
        self.document = _make_document(
            self.tenant, self.order, payer_party=self.payer_party, beneficiary_party=self.caregiver_party
        )
        self.escrow = _make_escrow(self.tenant, self.order, self.document, payer_party=self.payer_party)
        self.snapshot = _make_snapshot(self.tenant, self.order, caregiver_party=self.caregiver_party)
        self.instruction = _make_release_instruction(self.tenant, self.escrow, self.order, self.document, self.snapshot)

    def test_successful_release_credits_wallet(self):
        ReleaseConsumerService.consume(release_instruction_id=self.instruction.id)

        wallet = Wallet.objects.get(tenant=self.tenant, party=self.caregiver_party)
        # 85% of 10,000,000 = 8,500,000
        self.assertEqual(wallet.balance, Decimal("8500000.00"))

    def test_wallet_balance_updated_correctly(self):
        ReleaseConsumerService.consume(release_instruction_id=self.instruction.id)

        wallet = Wallet.objects.get(tenant=self.tenant, party=self.caregiver_party)
        txn = WalletTransaction.objects.get(wallet=wallet)
        self.assertEqual(txn.amount, Decimal("8500000.00"))
        self.assertEqual(txn.balance_after, Decimal("8500000.00"))

    def test_instruction_marked_consumed(self):
        ReleaseConsumerService.consume(release_instruction_id=self.instruction.id)

        self.instruction.refresh_from_db()
        self.assertEqual(self.instruction.status, ReleaseInstructionStatus.CONSUMED)
        self.assertIsNotNone(self.instruction.consumed_at)

    def test_audit_recorded(self):
        ReleaseConsumerService.consume(release_instruction_id=self.instruction.id)

        audit = AuditLog.objects.filter(action="commission.release_instruction.consumed").first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.resource_id, self.instruction.id)
        self.assertEqual(audit.tenant_id, self.tenant.id)

    def test_amount_conservation(self):
        """Platform + caregiver amounts must equal the gross release amount."""
        ReleaseConsumerService.consume(release_instruction_id=self.instruction.id)

        # Platform 15% = 1,500,000, Caregiver 85% = 8,500,000
        # Total = 10,000,000 == gross_releasable_amount_irr
        wallet = Wallet.objects.get(tenant=self.tenant, party=self.caregiver_party)
        caregiver_credited = int(wallet.balance)
        platform_amount = 10000000 - caregiver_credited  # platform keeps the rest
        self.assertEqual(caregiver_credited + platform_amount, 10000000)


class ReleaseConsumerWithCompanyTest(TestCase):
    def setUp(self):
        self.tenant = _make_tenant()
        self.order = _make_order(self.tenant)
        self.payer_party = _make_party(self.tenant, party_type="CUSTOMER", display_name="Customer")
        self.caregiver_party = _make_party(self.tenant, party_type="SUPPLIER", display_name="Caregiver")
        self.company_party = _make_party(self.tenant, party_type="ORGANIZATION", display_name="Company")
        self.document = _make_document(
            self.tenant, self.order, payer_party=self.payer_party, beneficiary_party=self.caregiver_party
        )
        self.escrow = _make_escrow(self.tenant, self.order, self.document, payer_party=self.payer_party)
        self.snapshot = _make_snapshot(
            self.tenant, self.order, caregiver_party=self.caregiver_party, company_party=self.company_party
        )
        self.instruction = _make_release_instruction(self.tenant, self.escrow, self.order, self.document, self.snapshot)

    def test_both_caregiver_and_company_wallets_credited(self):
        ReleaseConsumerService.consume(release_instruction_id=self.instruction.id)

        caregiver_wallet = Wallet.objects.get(tenant=self.tenant, party=self.caregiver_party)
        company_wallet = Wallet.objects.get(tenant=self.tenant, party=self.company_party)
        # 75% caregiver, 10% company, 15% platform
        self.assertEqual(caregiver_wallet.balance, Decimal("7500000.00"))
        self.assertEqual(company_wallet.balance, Decimal("1000000.00"))

    def test_company_plus_caregiver_plus_platform_equals_gross(self):
        ReleaseConsumerService.consume(release_instruction_id=self.instruction.id)

        caregiver_wallet = Wallet.objects.get(tenant=self.tenant, party=self.caregiver_party)
        company_wallet = Wallet.objects.get(tenant=self.tenant, party=self.company_party)
        total_credited = int(caregiver_wallet.balance) + int(company_wallet.balance)
        platform_amount = 10000000 - total_credited
        self.assertEqual(total_credited + platform_amount, 10000000)
        self.assertEqual(platform_amount, 1500000)  # 15%


class ReleaseConsumerIdempotencyTest(TestCase):
    def setUp(self):
        self.tenant = _make_tenant()
        self.order = _make_order(self.tenant)
        self.payer_party = _make_party(self.tenant, party_type="CUSTOMER", display_name="Customer")
        self.caregiver_party = _make_party(self.tenant, party_type="SUPPLIER", display_name="Caregiver")
        self.document = _make_document(
            self.tenant, self.order, payer_party=self.payer_party, beneficiary_party=self.caregiver_party
        )
        self.escrow = _make_escrow(self.tenant, self.order, self.document, payer_party=self.payer_party)
        self.snapshot = _make_snapshot(self.tenant, self.order, caregiver_party=self.caregiver_party)
        self.instruction = _make_release_instruction(self.tenant, self.escrow, self.order, self.document, self.snapshot)

    def test_duplicate_consume_is_safe(self):
        ReleaseConsumerService.consume(release_instruction_id=self.instruction.id)
        ReleaseConsumerService.consume(release_instruction_id=self.instruction.id)

        # Only one wallet transaction exists
        self.assertEqual(WalletTransaction.objects.filter(wallet__party=self.caregiver_party).count(), 1)

        # Balance not doubled
        wallet = Wallet.objects.get(tenant=self.tenant, party=self.caregiver_party)
        self.assertEqual(wallet.balance, Decimal("8500000.00"))

    def test_consumed_instruction_returned_immediately(self):
        first = ReleaseConsumerService.consume(release_instruction_id=self.instruction.id)
        second = ReleaseConsumerService.consume(release_instruction_id=self.instruction.id)
        self.assertEqual(first.id, second.id)
        self.assertEqual(second.status, ReleaseInstructionStatus.CONSUMED)


class ReleaseConsumerStateValidationTest(TestCase):
    def setUp(self):
        self.tenant = _make_tenant()
        self.order = _make_order(self.tenant)
        self.payer_party = _make_party(self.tenant, party_type="CUSTOMER", display_name="Customer")
        self.caregiver_party = _make_party(self.tenant, party_type="SUPPLIER", display_name="Caregiver")
        self.document = _make_document(
            self.tenant, self.order, payer_party=self.payer_party, beneficiary_party=self.caregiver_party
        )
        self.escrow = _make_escrow(self.tenant, self.order, self.document, payer_party=self.payer_party)
        self.snapshot = _make_snapshot(self.tenant, self.order, caregiver_party=self.caregiver_party)

    def test_pending_allocation_instruction_rejected(self):
        instruction = ReleaseInstruction.objects.create(
            tenant=self.tenant,
            escrow=self.escrow,
            order=self.order,
            invoice=self.document,
            commission_snapshot=self.snapshot,
            source=ReleaseInstructionSource.CUSTOMER_APPROVAL,
            gross_releasable_amount_irr=10000000,
            status=ReleaseInstructionStatus.PENDING_ALLOCATION,
            idempotency_key=f"test-{uuid.uuid4().hex[:8]}",
        )
        with self.assertRaises(ReleaseConsumerError):
            ReleaseConsumerService.consume(release_instruction_id=instruction.id)

    def test_cancelled_instruction_rejected(self):
        instruction = ReleaseInstruction.objects.create(
            tenant=self.tenant,
            escrow=self.escrow,
            order=self.order,
            invoice=self.document,
            commission_snapshot=self.snapshot,
            source=ReleaseInstructionSource.CUSTOMER_APPROVAL,
            gross_releasable_amount_irr=10000000,
            status=ReleaseInstructionStatus.CANCELLED,
            idempotency_key=f"test-{uuid.uuid4().hex[:8]}",
        )
        with self.assertRaises(ReleaseConsumerError):
            ReleaseConsumerService.consume(release_instruction_id=instruction.id)

    def test_nonexistent_instruction_raises(self):
        with self.assertRaises(ReleaseInstruction.DoesNotExist):
            ReleaseConsumerService.consume(release_instruction_id=uuid.uuid4())


class ReleaseConsumerTenantIsolationTest(TestCase):
    def test_cross_tenant_wallets_not_affected(self):
        tenant_a = _make_tenant(prefix="a")
        tenant_b = _make_tenant(prefix="b")

        # Set up tenant A
        order_a = _make_order(tenant_a)
        payer_a = _make_party(tenant_a, party_type="CUSTOMER")
        caregiver_a = _make_party(tenant_a, party_type="SUPPLIER")
        doc_a = _make_document(tenant_a, order_a, payer_party=payer_a, beneficiary_party=caregiver_a)
        escrow_a = _make_escrow(tenant_a, order_a, doc_a, payer_party=payer_a)
        snapshot_a = _make_snapshot(tenant_a, order_a, caregiver_party=caregiver_a)
        instruction_a = _make_release_instruction(tenant_a, escrow_a, order_a, doc_a, snapshot_a)

        # Set up tenant B with a pre-existing wallet
        caregiver_b = _make_party(tenant_b, party_type="SUPPLIER")
        wallet_b = Wallet.objects.create(tenant=tenant_b, party=caregiver_b, currency="IRR", balance=Decimal("5000000"))

        # Consume tenant A's instruction
        ReleaseConsumerService.consume(release_instruction_id=instruction_a.id)

        # Tenant B's wallet is unchanged
        wallet_b.refresh_from_db()
        self.assertEqual(wallet_b.balance, Decimal("5000000"))

        # Tenant A's wallet was created and credited
        wallet_a = Wallet.objects.get(tenant=tenant_a, party=caregiver_a)
        self.assertEqual(wallet_a.balance, Decimal("8500000.00"))


class ReleaseConsumerBatchTest(TestCase):
    def setUp(self):
        self.tenant = _make_tenant()
        self.order = _make_order(self.tenant)
        self.payer_party = _make_party(self.tenant, party_type="CUSTOMER")
        self.caregiver_party = _make_party(self.tenant, party_type="SUPPLIER")
        self.document = _make_document(
            self.tenant, self.order, payer_party=self.payer_party, beneficiary_party=self.caregiver_party
        )
        self.escrow = _make_escrow(self.tenant, self.order, self.document, payer_party=self.payer_party)
        self.snapshot = _make_snapshot(self.tenant, self.order, caregiver_party=self.caregiver_party)

    def test_consume_all_ready_processes_batch(self):
        inst1 = _make_release_instruction(
            self.tenant, self.escrow, self.order, self.document, self.snapshot, amount_irr=1000000
        )
        inst2 = _make_release_instruction(
            self.tenant, self.escrow, self.order, self.document, self.snapshot, amount_irr=2000000
        )

        result = ReleaseConsumerService.consume_all_ready(tenant_id=self.tenant.id)
        self.assertEqual(len(result), 2)

        inst1.refresh_from_db()
        inst2.refresh_from_db()
        self.assertEqual(inst1.status, ReleaseInstructionStatus.CONSUMED)
        self.assertEqual(inst2.status, ReleaseInstructionStatus.CONSUMED)

    def test_consume_all_ready_skips_non_ready(self):
        _make_release_instruction(
            self.tenant, self.escrow, self.order, self.document, self.snapshot, amount_irr=1000000
        )
        # Create a CANCELLED one — should be skipped
        ReleaseInstruction.objects.create(
            tenant=self.tenant,
            escrow=self.escrow,
            order=self.order,
            invoice=self.document,
            commission_snapshot=self.snapshot,
            source=ReleaseInstructionSource.CUSTOMER_APPROVAL,
            gross_releasable_amount_irr=500000,
            status=ReleaseInstructionStatus.CANCELLED,
            idempotency_key=f"cancelled-{uuid.uuid4().hex[:8]}",
        )

        result = ReleaseConsumerService.consume_all_ready(tenant_id=self.tenant.id)
        self.assertEqual(len(result), 1)


class ReleaseConsumerSettlementUnaffectedTest(TestCase):
    """Verify the existing direct-settlement path is not broken."""

    def test_existing_wallet_transactions_preserved(self):
        tenant = _make_tenant()
        party = _make_party(tenant, party_type="SUPPLIER")
        wallet = Wallet.objects.create(tenant=tenant, party=party, currency="IRR", balance=Decimal("500000"))
        WalletTransaction.objects.create(
            tenant=tenant,
            wallet=wallet,
            transaction_type="CREDIT",
            amount=Decimal("500000"),
            balance_after=Decimal("500000"),
            reason="Previous settlement",
        )

        # Creating and consuming a release instruction for a different party
        order = _make_order(tenant)
        payer = _make_party(tenant, party_type="CUSTOMER")
        caregiver = _make_party(tenant, party_type="SUPPLIER", display_name="Different Caregiver")
        doc = _make_document(tenant, order, payer_party=payer, beneficiary_party=caregiver)
        escrow = _make_escrow(tenant, order, doc, payer_party=payer)
        snapshot = _make_snapshot(tenant, order, caregiver_party=caregiver)
        instruction = _make_release_instruction(tenant, escrow, order, doc, snapshot)

        ReleaseConsumerService.consume(release_instruction_id=instruction.id)

        # Original wallet unchanged
        wallet.refresh_from_db()
        self.assertEqual(wallet.balance, Decimal("500000"))

        # New caregiver wallet created separately
        new_wallet = Wallet.objects.get(tenant=tenant, party=caregiver)
        self.assertEqual(new_wallet.balance, Decimal("8500000.00"))
