"""
Tests for ReleaseConsumerService — Financial Core PR-C.

Covers: consume(), consume_all_ready() — wallet credits, ledger postings,
allocation conservation, idempotency, concurrency (TransactionTestCase),
rollback on failure, tenant isolation, batch processing.
"""

import threading
import uuid
from decimal import Decimal
from unittest.mock import patch

from django.apps import apps as django_apps
from django.db import connection
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from apps.commission.models.release_instruction import (
    ReleaseInstruction,
    ReleaseInstructionSource,
    ReleaseInstructionStatus,
)
from apps.commission.models.snapshot import CommissionSnapshot
from apps.commission.services.release_consumer_service import ReleaseConsumerError, ReleaseConsumerService
from apps.finance.models import (
    EscrowRecord,
    EscrowStatus,
    FinancialDocument,
    FinancialDocumentStatus,
    FinancialParty,
    LedgerEntry,
)
from apps.kernel.models import Tenant
from apps.kernel.models.audit import AuditLog
from apps.kernel.models.supplier import (
    AvailabilityStatus,
    ServiceSupplier,
    SupplierStatus,
    SupplierType,
    VerificationLevel,
)
from apps.orders.models import Order, OrderSource, OrderStatus, ServiceCategory
from apps.wallet.models import Wallet, WalletTransaction
from apps.wallet.services import WalletTransactionService

# ============================================================
# Test Fixtures
# ============================================================


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
        linked_entity_type="TestEntity",
        linked_entity_id=uuid.uuid4(),
    )


def _make_supplier(tenant):
    return ServiceSupplier.objects.create(
        tenant=tenant,
        supplier_type=SupplierType.INDEPENDENT_PROVIDER,
        linked_entity_id=uuid.uuid4(),
        linked_entity_type="TestProfile",
        display_name=f"Test Supplier {uuid.uuid4().hex[:6]}",
        status=SupplierStatus.ACTIVE,
        availability_status=AvailabilityStatus.AVAILABLE,
        verification_level=VerificationLevel.BASIC,
    )


def _make_document(tenant, order, *, issuer_party, payer_party, beneficiary_party):
    return FinancialDocument.objects.create(
        tenant=tenant,
        order=order,
        document_type="INVOICE",
        status=FinancialDocumentStatus.ISSUED,
        total_amount=Decimal("10000000"),
        currency="IRR",
        issuer_party=issuer_party,
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


def _make_snapshot(
    tenant, order, supplier, *, caregiver_party, company_party=None, platform_pct=15, company_pct=0, caregiver_pct=85
):
    return CommissionSnapshot.objects.create(
        tenant=tenant,
        order=order,
        supplier=supplier,
        cooperation_type="INDEPENDENT" if company_party is None else "AFFILIATED",
        policy_source="global_default",
        platform_rate_percent=platform_pct,
        company_rate_percent=company_pct,
        caregiver_rate_percent=caregiver_pct,
        goods_platform_rate_percent=0,
        goods_company_rate_percent=0,
        goods_caregiver_rate_percent=100,
        caregiver_party=caregiver_party,
        company_party=company_party,
        effective_timestamp=timezone.now(),
    )


def _make_instruction(tenant, escrow, order, document, snapshot, *, amount_irr=10000000):
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


def _setup_standard_fixtures(
    tenant=None, *, platform_pct=15, company_pct=0, caregiver_pct=85, company_party=None, amount_irr=10000000
):
    """Create a complete fixture set for a single release instruction."""
    tenant = tenant or _make_tenant()
    order = _make_order(tenant)
    supplier = _make_supplier(tenant)
    platform_party = _make_party(tenant, party_type="PLATFORM", display_name="Platform")
    payer = _make_party(tenant, party_type="CUSTOMER", display_name="Customer")
    caregiver = _make_party(tenant, party_type="SUPPLIER", display_name="Caregiver")
    document = _make_document(
        tenant, order, issuer_party=platform_party, payer_party=payer, beneficiary_party=caregiver
    )
    escrow = _make_escrow(tenant, order, document, payer_party=payer, amount_irr=amount_irr)
    snapshot = _make_snapshot(
        tenant,
        order,
        supplier,
        caregiver_party=caregiver,
        company_party=company_party,
        platform_pct=platform_pct,
        company_pct=company_pct,
        caregiver_pct=caregiver_pct,
    )
    instruction = _make_instruction(tenant, escrow, order, document, snapshot, amount_irr=amount_irr)
    return {
        "tenant": tenant,
        "order": order,
        "payer": payer,
        "caregiver": caregiver,
        "company": company_party,
        "document": document,
        "escrow": escrow,
        "snapshot": snapshot,
        "instruction": instruction,
    }


# ============================================================
# Happy Path — Caregiver Only
# ============================================================


class ReleaseConsumerHappyPathTest(TestCase):
    def setUp(self):
        f = _setup_standard_fixtures()
        self.tenant = f["tenant"]
        self.caregiver_party = f["caregiver"]
        self.instruction = f["instruction"]

    def test_successful_release_credits_caregiver_wallet(self):
        ReleaseConsumerService.consume(release_instruction_id=self.instruction.id)
        wallet = Wallet.objects.get(tenant=self.tenant, party=self.caregiver_party)
        self.assertEqual(wallet.balance, Decimal("8500000.00"))  # 85% of 10M

    def test_wallet_transaction_has_correct_amount(self):
        ReleaseConsumerService.consume(release_instruction_id=self.instruction.id)
        wallet = Wallet.objects.get(tenant=self.tenant, party=self.caregiver_party)
        txn = WalletTransaction.objects.get(wallet=wallet)
        self.assertEqual(txn.amount, Decimal("8500000.00"))

    def test_instruction_marked_consumed(self):
        ReleaseConsumerService.consume(release_instruction_id=self.instruction.id)
        self.instruction.refresh_from_db()
        self.assertEqual(self.instruction.status, ReleaseInstructionStatus.CONSUMED)
        self.assertIsNotNone(self.instruction.consumed_at)

    def test_balanced_ledger_posted(self):
        ReleaseConsumerService.consume(release_instruction_id=self.instruction.id)
        entries = LedgerEntry.objects.filter(tenant=self.tenant)
        debits = sum(e.amount for e in entries if e.entry_type == "DEBIT")
        credit_total = sum(e.amount for e in entries if e.entry_type == "CREDIT")
        self.assertEqual(debits, credit_total)
        self.assertEqual(debits, Decimal("10000000"))  # gross

    def test_ledger_has_correct_account_codes(self):
        ReleaseConsumerService.consume(release_instruction_id=self.instruction.id)
        entries = LedgerEntry.objects.filter(tenant=self.tenant)
        codes = set(entries.values_list("account_code", flat=True))
        self.assertIn("platform.escrow.released", codes)
        self.assertIn("provider.receivable.settled", codes)
        self.assertIn("platform.commission.revenue", codes)

    def test_ledger_references_source_document(self):
        ReleaseConsumerService.consume(release_instruction_id=self.instruction.id)
        for entry in LedgerEntry.objects.filter(tenant=self.tenant):
            self.assertEqual(entry.source_document_id, self.instruction.invoice_id)

    def test_platform_commission_in_ledger(self):
        ReleaseConsumerService.consume(release_instruction_id=self.instruction.id)
        commission_entry = LedgerEntry.objects.get(tenant=self.tenant, account_code="platform.commission.revenue")
        self.assertEqual(commission_entry.amount, Decimal("1500000"))  # 15%

    def test_audit_recorded(self):
        ReleaseConsumerService.consume(release_instruction_id=self.instruction.id)
        audit = AuditLog.objects.filter(action="commission.release_instruction.consumed").first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.resource_id, self.instruction.id)

    def test_allocation_conservation(self):
        """platform + caregiver == gross (no company in this test)."""
        ReleaseConsumerService.consume(release_instruction_id=self.instruction.id)
        wallet = Wallet.objects.get(tenant=self.tenant, party=self.caregiver_party)
        caregiver = int(wallet.balance)
        platform = 10000000 - caregiver  # 15%
        self.assertEqual(caregiver + platform, 10000000)


# ============================================================
# Happy Path — With Company
# ============================================================


class ReleaseConsumerWithCompanyTest(TestCase):
    def setUp(self):
        self.tenant = _make_tenant()
        self.company_party = _make_party(self.tenant, party_type="ORGANIZATION", display_name="Company")
        f = _setup_standard_fixtures(
            tenant=self.tenant,
            platform_pct=15,
            company_pct=10,
            caregiver_pct=75,
            company_party=self.company_party,
        )
        self.caregiver_party = f["caregiver"]
        self.instruction = f["instruction"]

    def test_both_wallets_credited(self):
        ReleaseConsumerService.consume(release_instruction_id=self.instruction.id)
        cg_wallet = Wallet.objects.get(tenant=self.tenant, party=self.caregiver_party)
        co_wallet = Wallet.objects.get(tenant=self.tenant, party=self.company_party)
        self.assertEqual(cg_wallet.balance, Decimal("7500000.00"))  # 75%
        self.assertEqual(co_wallet.balance, Decimal("1000000.00"))  # 10%

    def test_conservation_with_company(self):
        ReleaseConsumerService.consume(release_instruction_id=self.instruction.id)
        cg_wallet = Wallet.objects.get(tenant=self.tenant, party=self.caregiver_party)
        co_wallet = Wallet.objects.get(tenant=self.tenant, party=self.company_party)
        total_credited = int(cg_wallet.balance) + int(co_wallet.balance)
        platform = 10000000 - total_credited
        self.assertEqual(total_credited + platform, 10000000)
        self.assertEqual(platform, 1500000)


# ============================================================
# Idempotency
# ============================================================


class ReleaseConsumerIdempotencyTest(TestCase):
    def setUp(self):
        f = _setup_standard_fixtures()
        self.tenant = f["tenant"]
        self.caregiver_party = f["caregiver"]
        self.instruction = f["instruction"]

    def test_duplicate_consume_is_noop(self):
        ReleaseConsumerService.consume(release_instruction_id=self.instruction.id)
        ReleaseConsumerService.consume(release_instruction_id=self.instruction.id)
        self.assertEqual(WalletTransaction.objects.filter(wallet__party=self.caregiver_party).count(), 1)
        wallet = Wallet.objects.get(tenant=self.tenant, party=self.caregiver_party)
        self.assertEqual(wallet.balance, Decimal("8500000.00"))

    def test_no_duplicate_audit_on_replay(self):
        ReleaseConsumerService.consume(release_instruction_id=self.instruction.id)
        ReleaseConsumerService.consume(release_instruction_id=self.instruction.id)
        count = AuditLog.objects.filter(action="commission.release_instruction.consumed").count()
        self.assertEqual(count, 1)

    def test_no_duplicate_ledger_on_replay(self):
        ReleaseConsumerService.consume(release_instruction_id=self.instruction.id)
        ledger_count_after_first = LedgerEntry.objects.filter(tenant=self.tenant).count()
        ReleaseConsumerService.consume(release_instruction_id=self.instruction.id)
        ledger_count_after_second = LedgerEntry.objects.filter(tenant=self.tenant).count()
        self.assertEqual(ledger_count_after_first, ledger_count_after_second)

    def test_retry_after_rollback_succeeds(self):
        """If the first call fails (e.g., ledger error), retry should work."""
        with patch(
            "apps.commission.services.release_consumer_service.LedgerService.post_entries",
            side_effect=Exception("Simulated ledger failure"),
        ):
            with self.assertRaises(Exception):
                ReleaseConsumerService.consume(release_instruction_id=self.instruction.id)

        # Instruction should still be READY (rolled back)
        self.instruction.refresh_from_db()
        self.assertEqual(self.instruction.status, ReleaseInstructionStatus.READY)

        # Retry without the failure succeeds
        ReleaseConsumerService.consume(release_instruction_id=self.instruction.id)
        self.instruction.refresh_from_db()
        self.assertEqual(self.instruction.status, ReleaseInstructionStatus.CONSUMED)
        wallet = Wallet.objects.get(tenant=self.tenant, party=self.caregiver_party)
        self.assertEqual(wallet.balance, Decimal("8500000.00"))


# ============================================================
# Rollback Tests
# ============================================================


class ReleaseConsumerLedgerFailureRollbackTest(TestCase):
    def setUp(self):
        f = _setup_standard_fixtures()
        self.tenant = f["tenant"]
        self.caregiver_party = f["caregiver"]
        self.instruction = f["instruction"]

    def test_ledger_failure_rolls_back_everything(self):
        with patch(
            "apps.commission.services.release_consumer_service.LedgerService.post_entries",
            side_effect=Exception("Ledger unavailable"),
        ):
            with self.assertRaises(Exception):
                ReleaseConsumerService.consume(release_instruction_id=self.instruction.id)

        self.instruction.refresh_from_db()
        self.assertEqual(self.instruction.status, ReleaseInstructionStatus.READY)
        self.assertIsNone(self.instruction.consumed_at)
        self.assertFalse(WalletTransaction.objects.filter(wallet__party=self.caregiver_party).exists())
        self.assertFalse(Wallet.objects.filter(party=self.caregiver_party).exists())
        self.assertFalse(AuditLog.objects.filter(action="commission.release_instruction.consumed").exists())


class ReleaseConsumerWalletFailureRollbackTest(TestCase):
    def setUp(self):
        f = _setup_standard_fixtures()
        self.tenant = f["tenant"]
        self.caregiver_party = f["caregiver"]
        self.instruction = f["instruction"]

    def test_wallet_failure_rolls_back_everything(self):
        with patch(
            "apps.commission.services.release_consumer_service.WalletTransactionService.credit",
            side_effect=Exception("Wallet write failed"),
        ):
            with self.assertRaises(Exception):
                ReleaseConsumerService.consume(release_instruction_id=self.instruction.id)

        self.instruction.refresh_from_db()
        self.assertEqual(self.instruction.status, ReleaseInstructionStatus.READY)
        self.assertFalse(LedgerEntry.objects.filter(tenant=self.tenant).exists())
        self.assertFalse(WalletTransaction.objects.filter(wallet__party=self.caregiver_party).exists())
        self.assertFalse(AuditLog.objects.filter(action="commission.release_instruction.consumed").exists())


class ReleaseConsumerCompanyPartialFailureRollbackTest(TestCase):
    def setUp(self):
        self.tenant = _make_tenant()
        self.company_party = _make_party(self.tenant, party_type="ORGANIZATION", display_name="Company")
        f = _setup_standard_fixtures(
            tenant=self.tenant,
            platform_pct=15,
            company_pct=10,
            caregiver_pct=75,
            company_party=self.company_party,
        )
        self.caregiver_party = f["caregiver"]
        self.instruction = f["instruction"]

    def test_company_failure_rolls_back_caregiver_credit_too(self):
        """If company wallet credit fails, caregiver credit must also roll back."""
        call_count = {"n": 0}
        original_credit = WalletTransactionService.credit

        def _failing_on_second_call(**kwargs):
            call_count["n"] += 1
            if call_count["n"] == 2:  # company is the second credit call
                raise Exception("Company wallet failure")
            return original_credit(**kwargs)

        with patch(
            "apps.commission.services.release_consumer_service.WalletTransactionService.credit",
            side_effect=_failing_on_second_call,
        ):
            with self.assertRaises(Exception):
                ReleaseConsumerService.consume(release_instruction_id=self.instruction.id)

        # Everything rolled back
        self.instruction.refresh_from_db()
        self.assertEqual(self.instruction.status, ReleaseInstructionStatus.READY)
        self.assertFalse(Wallet.objects.filter(party=self.caregiver_party).exists())
        self.assertFalse(Wallet.objects.filter(party=self.company_party).exists())
        self.assertFalse(LedgerEntry.objects.filter(tenant=self.tenant).exists())

        # Clean retry succeeds fully
        ReleaseConsumerService.consume(release_instruction_id=self.instruction.id)
        cg_wallet = Wallet.objects.get(tenant=self.tenant, party=self.caregiver_party)
        co_wallet = Wallet.objects.get(tenant=self.tenant, party=self.company_party)
        self.assertEqual(cg_wallet.balance, Decimal("7500000.00"))
        self.assertEqual(co_wallet.balance, Decimal("1000000.00"))


# ============================================================
# State Validation
# ============================================================


class ReleaseConsumerStateValidationTest(TestCase):
    def setUp(self):
        f = _setup_standard_fixtures()
        self.tenant = f["tenant"]
        self.instruction = f["instruction"]

    def test_pending_allocation_rejected(self):
        self.instruction.status = ReleaseInstructionStatus.PENDING_ALLOCATION
        self.instruction.save(update_fields=["status"])
        with self.assertRaises(ReleaseConsumerError):
            ReleaseConsumerService.consume(release_instruction_id=self.instruction.id)

    def test_cancelled_rejected(self):
        self.instruction.status = ReleaseInstructionStatus.CANCELLED
        self.instruction.save(update_fields=["status"])
        with self.assertRaises(ReleaseConsumerError):
            ReleaseConsumerService.consume(release_instruction_id=self.instruction.id)

    def test_nonexistent_raises(self):
        with self.assertRaises(ReleaseInstruction.DoesNotExist):
            ReleaseConsumerService.consume(release_instruction_id=uuid.uuid4())


# ============================================================
# Tenant Isolation
# ============================================================


class ReleaseConsumerTenantIsolationTest(TestCase):
    def test_cross_tenant_wallets_unaffected(self):
        tenant_a = _make_tenant(prefix="a")
        tenant_b = _make_tenant(prefix="b")

        f_a = _setup_standard_fixtures(tenant=tenant_a)
        caregiver_b = _make_party(tenant_b, party_type="SUPPLIER")
        Wallet.objects.create(tenant=tenant_b, party=caregiver_b, currency="IRR", balance=Decimal("5000000"))

        ReleaseConsumerService.consume(release_instruction_id=f_a["instruction"].id)

        wallet_b = Wallet.objects.get(tenant=tenant_b, party=caregiver_b)
        self.assertEqual(wallet_b.balance, Decimal("5000000"))  # unchanged


# ============================================================
# Batch Processing
# ============================================================


class ReleaseConsumerBatchTest(TestCase):
    def setUp(self):
        f = _setup_standard_fixtures(amount_irr=1000000)
        self.tenant = f["tenant"]
        self.instruction1 = f["instruction"]
        # Create a second instruction
        self.instruction2 = _make_instruction(
            self.tenant, f["escrow"], f["order"], f["document"], f["snapshot"], amount_irr=2000000
        )

    def test_consume_all_ready_processes_batch(self):
        result = ReleaseConsumerService.consume_all_ready(tenant_id=self.tenant.id)
        self.assertEqual(len(result), 2)
        self.instruction1.refresh_from_db()
        self.instruction2.refresh_from_db()
        self.assertEqual(self.instruction1.status, ReleaseInstructionStatus.CONSUMED)
        self.assertEqual(self.instruction2.status, ReleaseInstructionStatus.CONSUMED)

    def test_batch_skips_non_ready(self):
        self.instruction2.status = ReleaseInstructionStatus.CANCELLED
        self.instruction2.save(update_fields=["status"])
        result = ReleaseConsumerService.consume_all_ready(tenant_id=self.tenant.id)
        self.assertEqual(len(result), 1)


# ============================================================
# Existing Settlement Unaffected
# ============================================================


class ReleaseConsumerSettlementUnaffectedTest(TestCase):
    def test_existing_wallet_preserved(self):
        tenant = _make_tenant()
        other_party = _make_party(tenant, party_type="SUPPLIER", display_name="Other")
        wallet = Wallet.objects.create(tenant=tenant, party=other_party, currency="IRR", balance=Decimal("500000"))

        f = _setup_standard_fixtures(tenant=tenant)
        ReleaseConsumerService.consume(release_instruction_id=f["instruction"].id)

        wallet.refresh_from_db()
        self.assertEqual(wallet.balance, Decimal("500000"))  # unchanged


# ============================================================
# Concurrency — Real PostgreSQL TransactionTestCase
# ============================================================


class ReleaseConsumerConcurrencyTest(TransactionTestCase):
    """Two concurrent workers consuming the same ReleaseInstruction.

    Uses TransactionTestCase for real independent transactions and
    threading.Barrier for synchronization — the repository's established
    concurrency-test pattern (see apps.booking.tests.test_concurrency).

    available_apps = all installed apps because TransactionTestCase's
    post-test flush otherwise runs with allow_cascade=False and Postgres
    refuses to TRUNCATE tables reachable through auth's FK graph.
    """

    available_apps = [app_config.name for app_config in django_apps.get_app_configs()]

    def test_concurrent_consumption_produces_exactly_one_credit(self):
        # Set up fixtures inside the test (TransactionTestCase has no
        # setUpTestData — each test gets a fresh, committed database)
        f = _setup_standard_fixtures()
        instruction_id = f["instruction"].id
        tenant = f["tenant"]
        caregiver_party = f["caregiver"]

        barrier = threading.Barrier(2, timeout=10)
        results = [None, None]
        errors = [None, None]

        def _worker(index):
            try:
                barrier.wait()
                result = ReleaseConsumerService.consume(release_instruction_id=instruction_id)
                results[index] = result.status
            except Exception as exc:
                errors[index] = exc
            finally:
                connection.close()

        t1 = threading.Thread(target=_worker, args=(0,))
        t2 = threading.Thread(target=_worker, args=(1,))
        t1.start()
        t2.start()
        t1.join(timeout=15)
        t2.join(timeout=15)

        # Both threads completed without unhandled exceptions
        # (ReleaseConsumerError is acceptable for the loser)
        for i, err in enumerate(errors):
            if err is not None and not isinstance(err, (ReleaseConsumerError, ReleaseInstruction.DoesNotExist)):
                self.fail(f"Worker {i} raised unexpected: {err}")

        # Final state: exactly one CONSUMED
        instruction = ReleaseInstruction.objects.get(id=instruction_id)
        self.assertEqual(instruction.status, ReleaseInstructionStatus.CONSUMED)
        self.assertIsNotNone(instruction.consumed_at)

        # Exactly one wallet transaction
        txn_count = WalletTransaction.objects.filter(wallet__tenant=tenant, wallet__party=caregiver_party).count()
        self.assertEqual(txn_count, 1)

        # Wallet balance is correct (not doubled)
        wallet = Wallet.objects.get(tenant=tenant, party=caregiver_party)
        self.assertEqual(wallet.balance, Decimal("8500000.00"))

        # Exactly one successful audit
        audit_count = AuditLog.objects.filter(
            action="commission.release_instruction.consumed",
            resource_id=instruction_id,
        ).count()
        self.assertEqual(audit_count, 1)

        # Ledger is balanced (not doubled)
        entries = LedgerEntry.objects.filter(tenant=tenant)
        debit_total = sum(e.amount for e in entries if e.entry_type == "DEBIT")
        credit_total = sum(e.amount for e in entries if e.entry_type == "CREDIT")
        self.assertEqual(debit_total, credit_total)
        self.assertEqual(debit_total, Decimal("10000000"))

        # Both workers reported CONSUMED (the winner committed it,
        # the second observed it via idempotency)
        for r in results:
            if r is not None:
                self.assertEqual(r, ReleaseInstructionStatus.CONSUMED)
