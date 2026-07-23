"""
ReleaseConsumerService — Financial Core PR-C.

The canonical, single consumer of ReleaseInstruction rows in READY status.
Transforms a valid ReleaseInstruction into supplier wallet credits and
balanced accounting ledger entries using AllocationCalculator to split the
gross amount by the frozen commission snapshot's rates.

Transaction boundary: one @transaction.atomic enclosing:
  1. Lock ReleaseInstruction (select_for_update)
  2. Verify READY status (idempotency: CONSUMED returns early)
  3. Allocate via AllocationCalculator (platform/company/caregiver split)
  4. LedgerService.post_entries() — balanced escrow-release posting
  5. WalletTransactionService.credit() for the caregiver (net share)
  6. WalletTransactionService.credit() for the company (if applicable)
  7. Mark ReleaseInstruction status = CONSUMED + consumed_at
  8. AuditService.log() with FINANCIAL classification

Ledger and wallet separation:
  WalletTransactionService.credit() does NOT create ledger entries — it
  only creates a WalletTransaction row and mutates Wallet.balance.
  LedgerService.post_entries() is a separate balanced double-entry system.
  Both must be called explicitly — this follows the exact same pattern as
  SettlementOrchestrationService.settle_payment_intent().

Accounting entry semantics (escrow liability release):
  The initial payment INTO escrow was already recorded by
  SettlementOrchestrationService._settle_preservice_to_escrow() as a
  PaymentTransaction (receiver_party = platform). This consumer records
  the RELEASE of that liability:
    DEBIT  platform.escrow.released   (gross: liability leaving platform hold)
    CREDIT provider.receivable.settled (caregiver net share)
    CREDIT company.receivable.settled  (company share, if applicable)
    CREDIT platform.commission.revenue (platform commission retained)
  Balanced by construction: AllocationCalculator guarantees sum == gross.

Operation order (matches direct-settlement convention):
  Ledger posting FIRST, then wallet credit(s). This ensures the accounting
  record exists before the balance mutation, consistent with
  SettlementOrchestrationService._post_ledger_entries() → credit() ordering.

Lock ordering:
  ReleaseInstruction row (select_for_update) — serializes concurrent
  consumers. WalletTransactionService._apply() acquires its own wallet
  lock internally. LedgerService creates immutable rows (no lock needed).

Idempotency:
  - A CONSUMED instruction returns immediately (no-op)
  - select_for_update() serializes concurrent workers — second observes
    CONSUMED after the first commits
  - WalletTransactionService uses (wallet, idempotency_key) unique_together
    as database backstop
  - LedgerService has no native idempotency key for source_document-only
    entries — protection is solely via the instruction status gate + row lock

Security:
  - Tenant derived from locked ReleaseInstruction (authoritative)
  - No caller-supplied tenant_id trusted
  - No public endpoint may invoke this consumer
"""

import uuid
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.commission.services.allocation_calculator import AllocationCalculator
from apps.finance.models import LedgerEntryType
from apps.finance.services import FinancialPartyService, LedgerService
from apps.kernel.models.audit import AuditClassification
from apps.kernel.services.audit_service import AuditService
from apps.wallet.services import WalletService, WalletTransactionService

from ..models.release_instruction import ReleaseInstruction, ReleaseInstructionStatus
from .errors import CommissionError

SOURCE_MODULE = "M05"

# Ledger account codes — consistent with SettlementOrchestrationService
ACCOUNT_ESCROW_RELEASED = "platform.escrow.released"
ACCOUNT_SUPPLIER_EARNINGS = "provider.receivable.settled"
ACCOUNT_COMPANY_EARNINGS = "company.receivable.settled"
ACCOUNT_PLATFORM_COMMISSION = "platform.commission.revenue"


class ReleaseConsumerError(CommissionError):
    """Raised when a ReleaseInstruction cannot be consumed."""


class ReleaseConsumerService:
    """Consumes READY ReleaseInstructions into supplier/company wallet credits."""

    @classmethod
    @transaction.atomic
    def consume(cls, *, release_instruction_id) -> ReleaseInstruction:
        """Consume a single ReleaseInstruction, crediting wallets and posting ledger.

        Atomically: lock -> allocate -> ledger -> wallet credit(s) ->
        mark CONSUMED -> audit. Any failure rolls back everything.

        Idempotent: calling twice returns the already-consumed instruction.

        Raises ReleaseConsumerError if instruction cannot be consumed.
        """
        instruction = ReleaseInstruction.objects.select_for_update().get(id=release_instruction_id)

        # Idempotency: already consumed
        if instruction.status == ReleaseInstructionStatus.CONSUMED:
            return instruction

        # Only READY instructions can be consumed
        if instruction.status != ReleaseInstructionStatus.READY:
            raise ReleaseConsumerError(
                f"ReleaseInstruction {instruction.id} is in '{instruction.status}' status; "
                "only READY instructions can be consumed."
            )

        tenant_id = instruction.tenant_id
        gross_amount_irr = instruction.gross_releasable_amount_irr
        snapshot = instruction.commission_snapshot

        # Resolve allocation using the frozen commission snapshot rates
        if snapshot is not None:
            allocation = AllocationCalculator.allocate(
                base_amount_irr=gross_amount_irr,
                platform_rate_percent=snapshot.platform_rate_percent,
                company_rate_percent=snapshot.company_rate_percent,
                caregiver_rate_percent=snapshot.caregiver_rate_percent,
            )
        else:
            allocation = None

        # Resolve parties
        caregiver_party = snapshot.caregiver_party if snapshot and snapshot.caregiver_party_id else None
        company_party = snapshot.company_party if snapshot and snapshot.company_party_id else None

        # --- Step 1: Post balanced ledger entries (accounting record) ---
        # Follows canonical ordering: ledger FIRST, then wallet credits.
        cls._post_ledger_entries(
            instruction=instruction,
            tenant_id=tenant_id,
            allocation=allocation,
            caregiver_party=caregiver_party,
            company_party=company_party,
        )

        # --- Step 2: Credit wallets ---
        caregiver_credit_amount = Decimal("0")
        if caregiver_party and allocation and allocation.caregiver_amount_irr > 0:
            caregiver_credit_amount = Decimal(str(allocation.caregiver_amount_irr))
            wallet = WalletService.get_or_create_wallet(
                party=caregiver_party,
                currency=instruction.currency,
            )
            WalletTransactionService.credit(
                wallet_id=wallet.id,
                amount=caregiver_credit_amount,
                reason="Escrow release — caregiver share",
                metadata={
                    "release_instruction_id": str(instruction.id),
                    "order_id": str(instruction.order_id),
                    "escrow_id": str(instruction.escrow_id),
                },
                idempotency_key=f"release-consume:{instruction.id}:caregiver",
            )

        company_credit_amount = Decimal("0")
        if company_party and allocation and allocation.company_amount_irr > 0:
            company_credit_amount = Decimal(str(allocation.company_amount_irr))
            wallet = WalletService.get_or_create_wallet(
                party=company_party,
                currency=instruction.currency,
            )
            WalletTransactionService.credit(
                wallet_id=wallet.id,
                amount=company_credit_amount,
                reason="Escrow release — company share",
                metadata={
                    "release_instruction_id": str(instruction.id),
                    "order_id": str(instruction.order_id),
                    "escrow_id": str(instruction.escrow_id),
                },
                idempotency_key=f"release-consume:{instruction.id}:company",
            )

        # Fallback: no snapshot — credit the escrow's beneficiary directly
        if allocation is None:
            escrow = instruction.escrow
            if escrow.beneficiary_party_id:
                beneficiary = escrow.beneficiary_party
                wallet = WalletService.get_or_create_wallet(
                    party=beneficiary,
                    currency=instruction.currency,
                )
                WalletTransactionService.credit(
                    wallet_id=wallet.id,
                    amount=Decimal(str(gross_amount_irr)),
                    reason="Escrow release — full amount (no commission snapshot)",
                    metadata={
                        "release_instruction_id": str(instruction.id),
                        "order_id": str(instruction.order_id),
                    },
                    idempotency_key=f"release-consume:{instruction.id}:beneficiary",
                )

        # --- Step 3: Mark consumed ---
        instruction.status = ReleaseInstructionStatus.CONSUMED
        instruction.consumed_at = timezone.now()
        instruction.save(update_fields=["status", "consumed_at", "updated_at"])

        # --- Step 4: Audit ---
        platform_amount_irr = allocation.platform_amount_irr if allocation else 0
        AuditService.log(
            tenant_id=tenant_id,
            action="commission.release_instruction.consumed",
            resource_type="ReleaseInstruction",
            module_id=SOURCE_MODULE,
            resource_id=instruction.id,
            actor_type="system",
            audit_class=AuditClassification.FINANCIAL,
            after={
                "gross_releasable_amount_irr": gross_amount_irr,
                "caregiver_amount_irr": int(caregiver_credit_amount),
                "company_amount_irr": int(company_credit_amount),
                "platform_amount_irr": platform_amount_irr,
                "caregiver_party_id": str(caregiver_party.id) if caregiver_party else None,
                "company_party_id": str(company_party.id) if company_party else None,
                "order_id": str(instruction.order_id),
                "escrow_id": str(instruction.escrow_id),
            },
            reason="ReleaseInstruction consumed — ledger posted, wallet credits applied.",
        )

        return instruction

    @classmethod
    def consume_all_ready(cls, *, tenant_id=None, batch_size: int = 100) -> list:
        """Consume all READY instructions, optionally scoped to a tenant.

        Mirrors OrderOfferService.expire_held_offers() batch pattern:
        independently callable by any future management command or scheduled
        job. Each instruction is individually locked and consumed — safe for
        concurrent execution. Returns list of consumed instruction IDs.
        """
        qs = ReleaseInstruction.objects.filter(status=ReleaseInstructionStatus.READY)
        if tenant_id is not None:
            qs = qs.filter(tenant_id=tenant_id)
        qs = qs.order_by("created_at")[:batch_size]

        consumed_ids = []
        for instruction_id in qs.values_list("id", flat=True):
            try:
                result = cls.consume(release_instruction_id=instruction_id)
                if result.status == ReleaseInstructionStatus.CONSUMED:
                    consumed_ids.append(instruction_id)
            except (ReleaseConsumerError, ReleaseInstruction.DoesNotExist):
                continue

        return consumed_ids

    # --- internal helpers --------------------------------------------------

    @classmethod
    def _post_ledger_entries(cls, *, instruction, tenant_id, allocation, caregiver_party, company_party):
        """Post balanced double-entry ledger for the escrow release.

        Accounting semantics:
          DEBIT  platform.escrow.released   (gross — escrow liability decrease)
          CREDIT provider.receivable.settled (caregiver net share — earnings)
          CREDIT company.receivable.settled  (company share, if applicable)
          CREDIT platform.commission.revenue (platform commission retained)

        Sum of credits == debit amount, guaranteed by AllocationCalculator.

        Source reference: instruction.invoice_id (the original invoice the
        escrow was held against — this is the canonical source_document for
        escrow-release ledger entries, matching how direct settlement uses
        the resolved document as its source_document_id).

        LedgerService.post_entries() with actor=None triggers the
        system-context path in PermissionService.require().
        """
        platform_party = FinancialPartyService.resolve_platform_party(instruction.order.tenant)
        gross = instruction.gross_releasable_amount_irr

        if allocation is None:
            # No snapshot fallback — simple gross release
            escrow_beneficiary = instruction.escrow.beneficiary_party
            target_party = escrow_beneficiary if escrow_beneficiary else platform_party
            entries = [
                {
                    "party_id": platform_party.id,
                    "entry_type": LedgerEntryType.DEBIT,
                    "account_code": ACCOUNT_ESCROW_RELEASED,
                    "amount": Decimal(str(gross)),
                    "currency": instruction.currency,
                    "source_document_id": instruction.invoice_id,
                    "description": "Escrow release — gross amount.",
                },
                {
                    "party_id": target_party.id,
                    "entry_type": LedgerEntryType.CREDIT,
                    "account_code": ACCOUNT_SUPPLIER_EARNINGS,
                    "amount": Decimal(str(gross)),
                    "currency": instruction.currency,
                    "source_document_id": instruction.invoice_id,
                    "description": "Escrow release — full beneficiary credit.",
                },
            ]
            LedgerService.post_entries(tenant_id=tenant_id, entries=entries, actor=None)
            return

        # Normal allocation path
        entries = [
            {
                "party_id": platform_party.id,
                "entry_type": LedgerEntryType.DEBIT,
                "account_code": ACCOUNT_ESCROW_RELEASED,
                "amount": Decimal(str(gross)),
                "currency": instruction.currency,
                "source_document_id": instruction.invoice_id,
                "description": "Escrow release — gross amount.",
            },
        ]

        if caregiver_party and allocation.caregiver_amount_irr > 0:
            entries.append(
                {
                    "party_id": caregiver_party.id,
                    "entry_type": LedgerEntryType.CREDIT,
                    "account_code": ACCOUNT_SUPPLIER_EARNINGS,
                    "amount": Decimal(str(allocation.caregiver_amount_irr)),
                    "currency": instruction.currency,
                    "source_document_id": instruction.invoice_id,
                    "description": "Escrow release — caregiver share.",
                }
            )

        if company_party and allocation.company_amount_irr > 0:
            entries.append(
                {
                    "party_id": company_party.id,
                    "entry_type": LedgerEntryType.CREDIT,
                    "account_code": ACCOUNT_COMPANY_EARNINGS,
                    "amount": Decimal(str(allocation.company_amount_irr)),
                    "currency": instruction.currency,
                    "source_document_id": instruction.invoice_id,
                    "description": "Escrow release — company share.",
                }
            )

        if allocation.platform_amount_irr > 0:
            entries.append(
                {
                    "party_id": platform_party.id,
                    "entry_type": LedgerEntryType.CREDIT,
                    "account_code": ACCOUNT_PLATFORM_COMMISSION,
                    "amount": Decimal(str(allocation.platform_amount_irr)),
                    "currency": instruction.currency,
                    "source_document_id": instruction.invoice_id,
                    "description": "Escrow release — platform commission.",
                }
            )

        LedgerService.post_entries(
            tenant_id=tenant_id,
            entries=entries,
            entry_group_id=uuid.uuid4(),
            actor=None,
        )
