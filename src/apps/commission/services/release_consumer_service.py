"""
ReleaseConsumerService — Financial Core PR-C.

The canonical, single consumer of ReleaseInstruction rows in READY status.
Transforms a valid ReleaseInstruction into supplier wallet credits using
AllocationCalculator to split the gross amount by the frozen commission
snapshot's rates.

Transaction boundary: one @transaction.atomic enclosing:
  1. Lock ReleaseInstruction (select_for_update)
  2. Verify READY status (idempotency: CONSUMED returns early)
  3. Resolve beneficiary wallet via FinancialPartyService + WalletService
  4. Allocate via AllocationCalculator (platform/company/caregiver split)
  5. WalletTransactionService.credit() for the caregiver (net share)
  6. WalletTransactionService.credit() for the company (if applicable)
  7. Mark ReleaseInstruction status = CONSUMED + consumed_at
  8. AuditService.log() with FINANCIAL classification

Lock ordering: ReleaseInstruction row only. No wallet row lock is
acquired here — WalletTransactionService._apply() acquires its own
wallet lock internally and handles idempotency via (wallet, idempotency_key)
unique constraint.

Idempotency:
  - A CONSUMED instruction is returned immediately (no-op)
  - WalletTransactionService.credit() uses idempotency_key=f"release-consume:{instruction.id}:{party_role}"
    so a race that passes the status check still cannot double-credit
  - Concurrent workers: the first to lock the row wins; the second
    observes CONSUMED after the lock releases

Security:
  - Tenant is derived from the locked ReleaseInstruction (authoritative)
  - No caller-supplied tenant_id is trusted
  - No public endpoint invokes this — internal financial operation only
"""

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.commission.services.allocation_calculator import AllocationCalculator
from apps.kernel.models.audit import AuditClassification
from apps.kernel.services.audit_service import AuditService
from apps.wallet.services import WalletService, WalletTransactionService

from ..models.release_instruction import ReleaseInstruction, ReleaseInstructionStatus
from .errors import CommissionError

SOURCE_MODULE = "M05"


class ReleaseConsumerError(CommissionError):
    """Raised when a ReleaseInstruction cannot be consumed."""


class ReleaseConsumerService:
    """Consumes READY ReleaseInstructions into supplier/company wallet credits."""

    @classmethod
    @transaction.atomic
    def consume(cls, *, release_instruction_id) -> ReleaseInstruction:
        """Consume a single ReleaseInstruction, crediting the appropriate wallets.

        Idempotent: calling twice for the same instruction returns the
        already-consumed instruction without side effects.

        Raises ReleaseConsumerError if the instruction is in a state that
        cannot be consumed (PENDING_ALLOCATION, CANCELLED).
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
            # No snapshot: entire amount goes to the escrow's beneficiary
            # (fallback for edge cases — should not occur in normal flow)
            allocation = None

        # Credit caregiver wallet
        caregiver_party = None
        caregiver_credit_amount = Decimal("0")
        if snapshot and snapshot.caregiver_party_id:
            caregiver_party = snapshot.caregiver_party
            caregiver_credit_amount = Decimal(str(allocation.caregiver_amount_irr))
            if caregiver_credit_amount > 0:
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

        # Credit company wallet (if applicable — AFFILIATED cooperation type)
        company_party = None
        company_credit_amount = Decimal("0")
        if snapshot and snapshot.company_party_id and allocation and allocation.company_amount_irr > 0:
            company_party = snapshot.company_party
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

        # Fallback: no snapshot — credit the escrow's own beneficiary_party
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

        # Mark consumed
        instruction.status = ReleaseInstructionStatus.CONSUMED
        instruction.consumed_at = timezone.now()
        instruction.save(update_fields=["status", "consumed_at", "updated_at"])

        # Audit
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
            reason="ReleaseInstruction consumed — wallet credits applied.",
        )

        return instruction

    @classmethod
    def consume_all_ready(cls, *, tenant_id=None, batch_size: int = 100) -> list:
        """Consume all READY instructions, optionally scoped to a tenant.

        Intended for batch processing (management command, scheduled job).
        Returns list of consumed instruction IDs. Idempotent and safe for
        concurrent execution (each instruction is individually locked).
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
                # Skip instructions that cannot be consumed or were
                # concurrently consumed by another worker
                continue

        return consumed_ids
