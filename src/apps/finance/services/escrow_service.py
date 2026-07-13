"""
EscrowService — Module 05 escrow foundation.

Holds funds against a document, then releases or refunds them. No real
bank transfer happens here — this only tracks the internal HELD /
RELEASED / REFUNDED state.

Financial Core PR-B additions (hold_for_order/mark_releasable/
block_for_dispute/unblock/apply_release/apply_refund): the real production
Escrow path — every real balance change to an EscrowRecord's PR-B fields
goes through exactly one of these methods, each creating exactly one
immutable EscrowMovement row inside the same transaction as the field
update. The legacy hold()/release()/refund() methods above are untouched
(dead code, zero real callers before or after PR-B — see
apps.finance.models.escrow's module docstring) and are not used by the
new methods below."""

import logging
import uuid

from django.db import transaction
from django.utils import timezone

from apps.kernel.models.audit import AuditClassification
from apps.kernel.services.audit_service import AuditService
from apps.kernel.services.event_publisher import EventPublisher

from ..models import (
    DEFAULT_CURRENCY,
    EscrowMovement,
    EscrowMovementType,
    EscrowRecord,
    EscrowStatus,
    FinancialDocument,
    FinancialParty,
)
from .errors import FinanceError

logger = logging.getLogger(__name__)

SOURCE_MODULE = "M05"


class EscrowError(FinanceError):
    pass


class EscrowService:
    """Creates and transitions EscrowRecord rows."""

    @classmethod
    @transaction.atomic
    def hold(
        cls, *, source_document_id, payer_party_id, amount, beneficiary_party_id=None, currency=None, metadata=None
    ) -> EscrowRecord:
        source_document = FinancialDocument.objects.get(id=source_document_id)
        payer_party = FinancialParty.objects.get(id=payer_party_id)

        if payer_party.tenant_id != source_document.tenant_id:
            raise FinanceError("payer_party does not belong to the source_document's tenant.")

        beneficiary_party = None
        if beneficiary_party_id:
            beneficiary_party = FinancialParty.objects.get(id=beneficiary_party_id)
            if beneficiary_party.tenant_id != source_document.tenant_id:
                raise FinanceError("beneficiary_party does not belong to the source_document's tenant.")

        escrow = EscrowRecord.objects.create(
            tenant_id=source_document.tenant_id,
            source_document=source_document,
            payer_party=payer_party,
            beneficiary_party=beneficiary_party,
            amount=amount,
            currency=currency or source_document.currency or DEFAULT_CURRENCY,
            status=EscrowStatus.HELD,
            metadata=metadata or {},
        )

        EventPublisher.publish(
            tenant_id=escrow.tenant_id,
            event_type="Finance.Escrow.Held.v1",
            source_module=SOURCE_MODULE,
            source_entity_id=escrow.id,
            source_entity_type="EscrowRecord",
            payload={
                "source_document_id": str(source_document.id),
                "amount": str(escrow.amount),
                "currency": escrow.currency,
            },
        )

        return escrow

    @classmethod
    @transaction.atomic
    def release(cls, *, escrow_id) -> EscrowRecord:
        escrow = EscrowRecord.objects.select_for_update().get(id=escrow_id)

        if escrow.status != EscrowStatus.HELD:
            raise FinanceError(f"Cannot release escrow in '{escrow.status}' status.")

        escrow.status = EscrowStatus.RELEASED
        escrow.released_at = timezone.now()
        escrow.save(update_fields=["status", "released_at"])

        EventPublisher.publish(
            tenant_id=escrow.tenant_id,
            event_type="Finance.Escrow.Released.v1",
            source_module=SOURCE_MODULE,
            source_entity_id=escrow.id,
            source_entity_type="EscrowRecord",
            payload={"amount": str(escrow.amount), "currency": escrow.currency},
        )

        return escrow

    @classmethod
    @transaction.atomic
    def refund(cls, *, escrow_id) -> EscrowRecord:
        escrow = EscrowRecord.objects.select_for_update().get(id=escrow_id)

        if escrow.status != EscrowStatus.HELD:
            raise FinanceError(f"Cannot refund escrow in '{escrow.status}' status.")

        escrow.status = EscrowStatus.REFUNDED
        escrow.released_at = timezone.now()
        escrow.save(update_fields=["status", "released_at"])

        return escrow

    # --- Financial Core PR-B: real production Escrow path ------------------

    @classmethod
    @transaction.atomic
    def hold_for_order(
        cls,
        *,
        order,
        source_document,
        payment_transaction,
        commission_snapshot=None,
        payer_party,
        amount_irr: int,
        actor=None,
        idempotency_key: str,
        correlation_id: uuid.UUID | None = None,
    ) -> EscrowRecord:
        """Creates exactly one HELD EscrowRecord for a captured pre-service
        payment. Idempotent per (tenant, idempotency_key) — a second call
        with the same key returns the existing record instead of raising or
        double-holding, mirroring apps.jobs.JobService.enqueue()'s own
        (tenant, idempotency_key)-scoped idempotency contract."""
        if amount_irr is None or amount_irr <= 0:
            raise EscrowError("Escrow hold amount must be positive.")
        if not idempotency_key:
            raise EscrowError("hold_for_order requires an idempotency_key.")

        tenant_id = order.tenant_id
        existing = EscrowRecord.objects.filter(tenant_id=tenant_id, idempotency_key=idempotency_key).first()
        if existing is not None:
            return existing

        escrow = EscrowRecord.objects.create(
            tenant_id=tenant_id,
            source_document=source_document,
            payer_party=payer_party,
            beneficiary_party=None,
            amount=amount_irr,
            currency=source_document.currency or DEFAULT_CURRENCY,
            status=EscrowStatus.HELD,
            order=order,
            payment_transaction=payment_transaction,
            commission_snapshot=commission_snapshot,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            original_amount_irr=amount_irr,
            held_amount_irr=amount_irr,
            remaining_amount_irr=amount_irr,
        )

        cls._record_movement(
            escrow=escrow,
            movement_type=EscrowMovementType.HOLD,
            amount_irr=amount_irr,
            before_state=cls._zero_state(),
            after_state=cls._state_of(escrow),
            source_type="PaymentTransaction",
            source_id=payment_transaction.id if payment_transaction else None,
            actor=actor,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            reason="Pre-service payment captured.",
        )
        cls._audit(
            escrow=escrow,
            action="commission.escrow.hold",
            actor=actor,
            reason="Pre-service payment captured.",
            before=None,
            after=cls._state_of(escrow),
        )
        cls._publish(escrow, event_type="Finance.Escrow.Held.v1", extra={"order_id": str(order.id)})

        return escrow

    @classmethod
    @transaction.atomic
    def mark_releasable(
        cls,
        *,
        escrow_id,
        amount_irr: int,
        source_type: str,
        source_id=None,
        actor=None,
        reason: str,
        idempotency_key: str,
        correlation_id: uuid.UUID | None = None,
    ) -> EscrowRecord:
        """Moves `amount_irr` of an escrow's currently non-releasable
        `remaining_amount_irr` into `releasable_amount_irr` — does not
        change the conservation-equation buckets (remaining/blocked/
        released/refunded), since releasable is always a subset of
        remaining. Idempotent per (tenant, idempotency_key)."""
        escrow = EscrowRecord.objects.select_for_update().get(id=escrow_id)
        if cls._movement_already_applied(escrow.tenant_id, idempotency_key):
            return escrow
        if amount_irr is None or amount_irr <= 0:
            raise EscrowError("mark_releasable amount must be positive.")

        available = escrow.remaining_amount_irr - escrow.releasable_amount_irr
        if amount_irr > available:
            raise EscrowError(
                f"Cannot mark {amount_irr} releasable: only {available} of remaining escrow is not yet releasable.",
            )

        before = cls._state_of(escrow)
        escrow.releasable_amount_irr += amount_irr
        escrow.save(update_fields=["releasable_amount_irr"])

        cls._record_movement(
            escrow=escrow,
            movement_type=EscrowMovementType.MARK_RELEASABLE,
            amount_irr=amount_irr,
            before_state=before,
            after_state=cls._state_of(escrow),
            source_type=source_type,
            source_id=source_id,
            actor=actor,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            reason=reason,
        )
        cls._audit(
            escrow=escrow,
            action="commission.escrow.mark_releasable",
            actor=actor,
            reason=reason,
            before=before,
            after=cls._state_of(escrow),
        )
        return escrow

    @classmethod
    @transaction.atomic
    def block_for_dispute(
        cls,
        *,
        escrow_id,
        amount_irr: int,
        dispute_id,
        actor=None,
        reason: str,
        idempotency_key: str,
        correlation_id: uuid.UUID | None = None,
    ) -> EscrowRecord:
        """Blocks exactly `amount_irr` for an open dispute — moves that
        amount out of remaining_amount_irr (and, if it had already been
        marked releasable, out of releasable_amount_irr too) and into
        blocked_amount_irr. Idempotent per (tenant, idempotency_key), so
        opening the same dispute command twice never double-blocks."""
        escrow = EscrowRecord.objects.select_for_update().get(id=escrow_id)
        if cls._movement_already_applied(escrow.tenant_id, idempotency_key):
            return escrow
        if amount_irr is None or amount_irr <= 0:
            raise EscrowError("block_for_dispute amount must be positive.")
        if amount_irr > escrow.remaining_amount_irr:
            raise EscrowError(
                f"Cannot block {amount_irr}: only {escrow.remaining_amount_irr} remains un-blocked in escrow "
                f"(escrow {escrow.id}).",
            )

        before = cls._state_of(escrow)
        escrow.blocked_amount_irr += amount_irr
        escrow.remaining_amount_irr -= amount_irr
        escrow.releasable_amount_irr = min(escrow.releasable_amount_irr, escrow.remaining_amount_irr)
        escrow.save(update_fields=["blocked_amount_irr", "remaining_amount_irr", "releasable_amount_irr"])

        cls._record_movement(
            escrow=escrow,
            movement_type=EscrowMovementType.BLOCK_FOR_DISPUTE,
            amount_irr=amount_irr,
            before_state=before,
            after_state=cls._state_of(escrow),
            source_type="Dispute",
            source_id=dispute_id,
            actor=actor,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            reason=reason,
        )
        cls._audit(
            escrow=escrow,
            action="commission.escrow.block_for_dispute",
            actor=actor,
            reason=reason,
            before=before,
            after=cls._state_of(escrow),
        )
        cls._publish(escrow, event_type="Finance.Escrow.Blocked.v1", extra={"amount_irr": amount_irr})
        return escrow

    @classmethod
    @transaction.atomic
    def unblock(
        cls,
        *,
        escrow_id,
        amount_irr: int,
        dispute_id,
        actor=None,
        reason: str,
        idempotency_key: str,
        correlation_id: uuid.UUID | None = None,
    ) -> EscrowRecord:
        """The inverse of block_for_dispute — a dispute was rejected or
        cancelled, so its blocked amount returns to remaining (not
        releasable; a fresh objection/approval decision governs that)."""
        escrow = EscrowRecord.objects.select_for_update().get(id=escrow_id)
        if cls._movement_already_applied(escrow.tenant_id, idempotency_key):
            return escrow
        if amount_irr is None or amount_irr <= 0:
            raise EscrowError("unblock amount must be positive.")
        if amount_irr > escrow.blocked_amount_irr:
            raise EscrowError(f"Cannot unblock {amount_irr}: only {escrow.blocked_amount_irr} is blocked.")

        before = cls._state_of(escrow)
        escrow.blocked_amount_irr -= amount_irr
        escrow.remaining_amount_irr += amount_irr
        escrow.save(update_fields=["blocked_amount_irr", "remaining_amount_irr"])

        cls._record_movement(
            escrow=escrow,
            movement_type=EscrowMovementType.UNBLOCK,
            amount_irr=amount_irr,
            before_state=before,
            after_state=cls._state_of(escrow),
            source_type="Dispute",
            source_id=dispute_id,
            actor=actor,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            reason=reason,
        )
        cls._audit(
            escrow=escrow,
            action="commission.escrow.unblock",
            actor=actor,
            reason=reason,
            before=before,
            after=cls._state_of(escrow),
        )
        return escrow

    @classmethod
    @transaction.atomic
    def apply_release(
        cls,
        *,
        escrow_id,
        amount_irr: int,
        source_type: str,
        source_id=None,
        actor=None,
        reason: str,
        idempotency_key: str,
        correlation_id: uuid.UUID | None = None,
    ) -> EscrowRecord:
        """Consumes `amount_irr` of remaining (and releasable, if any) into
        released_amount_irr — called once per exact release event (a
        ReleaseInstruction being created), never twice for the same
        instruction (idempotent per (tenant, idempotency_key)). Does not
        credit any wallet — see apps.commission.models.release_instruction
        .ReleaseInstruction's own docstring for the PR-C consumption
        boundary."""
        escrow = EscrowRecord.objects.select_for_update().get(id=escrow_id)
        if cls._movement_already_applied(escrow.tenant_id, idempotency_key):
            return escrow
        if amount_irr is None or amount_irr <= 0:
            raise EscrowError("apply_release amount must be positive.")
        if amount_irr > escrow.remaining_amount_irr:
            raise EscrowError(
                f"Cannot release {amount_irr}: only {escrow.remaining_amount_irr} remains in escrow {escrow.id}.",
            )

        before = cls._state_of(escrow)
        escrow.released_amount_irr += amount_irr
        escrow.remaining_amount_irr -= amount_irr
        escrow.held_amount_irr -= amount_irr
        escrow.releasable_amount_irr = min(escrow.releasable_amount_irr, escrow.remaining_amount_irr)
        escrow.status = cls._status_after_release_or_refund(escrow)
        if escrow.status in (EscrowStatus.FULLY_RELEASED, EscrowStatus.CLOSED):
            escrow.released_at = timezone.now()
        escrow.save(
            update_fields=[
                "released_amount_irr",
                "remaining_amount_irr",
                "held_amount_irr",
                "releasable_amount_irr",
                "status",
                "released_at",
            ]
        )

        cls._record_movement(
            escrow=escrow,
            movement_type=EscrowMovementType.RELEASE,
            amount_irr=amount_irr,
            before_state=before,
            after_state=cls._state_of(escrow),
            source_type=source_type,
            source_id=source_id,
            actor=actor,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            reason=reason,
        )
        cls._audit(
            escrow=escrow,
            action="commission.escrow.release",
            actor=actor,
            reason=reason,
            before=before,
            after=cls._state_of(escrow),
        )
        cls._publish(escrow, event_type="Finance.Escrow.Released.v1", extra={"amount_irr": amount_irr})
        return escrow

    @classmethod
    @transaction.atomic
    def apply_refund(
        cls,
        *,
        escrow_id,
        amount_irr: int,
        source_type: str,
        source_id=None,
        actor=None,
        reason: str,
        idempotency_key: str,
        correlation_id: uuid.UUID | None = None,
    ) -> EscrowRecord:
        """Consumes `amount_irr` of remaining into refunded_amount_irr —
        called once per exact refund instruction. Does not itself call a
        PSP; RefundInstructionService owns that boundary (Section 16)."""
        escrow = EscrowRecord.objects.select_for_update().get(id=escrow_id)
        if cls._movement_already_applied(escrow.tenant_id, idempotency_key):
            return escrow
        if amount_irr is None or amount_irr <= 0:
            raise EscrowError("apply_refund amount must be positive.")
        if amount_irr > escrow.remaining_amount_irr:
            raise EscrowError(
                f"Cannot refund {amount_irr}: only {escrow.remaining_amount_irr} remains in escrow {escrow.id}.",
            )

        before = cls._state_of(escrow)
        escrow.refunded_amount_irr += amount_irr
        escrow.remaining_amount_irr -= amount_irr
        escrow.held_amount_irr -= amount_irr
        escrow.releasable_amount_irr = min(escrow.releasable_amount_irr, escrow.remaining_amount_irr)
        escrow.status = cls._status_after_release_or_refund(escrow)
        if escrow.status in (EscrowStatus.FULLY_REFUNDED, EscrowStatus.CLOSED):
            escrow.released_at = timezone.now()
        escrow.save(
            update_fields=[
                "refunded_amount_irr",
                "remaining_amount_irr",
                "held_amount_irr",
                "releasable_amount_irr",
                "status",
                "released_at",
            ]
        )

        cls._record_movement(
            escrow=escrow,
            movement_type=EscrowMovementType.REFUND,
            amount_irr=amount_irr,
            before_state=before,
            after_state=cls._state_of(escrow),
            source_type=source_type,
            source_id=source_id,
            actor=actor,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            reason=reason,
        )
        cls._audit(
            escrow=escrow,
            action="commission.escrow.refund",
            actor=actor,
            reason=reason,
            before=before,
            after=cls._state_of(escrow),
        )
        cls._publish(escrow, event_type="Finance.Escrow.Refunded.v1", extra={"amount_irr": amount_irr})
        return escrow

    # --- internal helpers -------------------------------------------------

    @staticmethod
    def _status_after_release_or_refund(escrow: EscrowRecord) -> str:
        if escrow.remaining_amount_irr > 0 or escrow.blocked_amount_irr > 0:
            # Still open: classify by whichever payout type has occurred so
            # far. A mix of both release and refund while still open is
            # reported as PARTIALLY_RELEASED (release takes priority in the
            # status label) — the individual *_amount_irr fields, not this
            # status alone, are the source of truth for exact amounts.
            if escrow.released_amount_irr > 0:
                return EscrowStatus.PARTIALLY_RELEASED
            if escrow.refunded_amount_irr > 0:
                return EscrowStatus.PARTIALLY_REFUNDED
            return escrow.status
        # Nothing left in escrow: fully resolved either as release, refund,
        # a mix of both, or (all-zero original, defensively) closed.
        if escrow.released_amount_irr > 0 and escrow.refunded_amount_irr == 0:
            return EscrowStatus.FULLY_RELEASED
        if escrow.refunded_amount_irr > 0 and escrow.released_amount_irr == 0:
            return EscrowStatus.FULLY_REFUNDED
        return EscrowStatus.CLOSED

    @staticmethod
    def _movement_already_applied(tenant_id, idempotency_key: str) -> bool:
        if not idempotency_key:
            raise EscrowError("This operation requires an idempotency_key.")
        return EscrowMovement.objects.filter(tenant_id=tenant_id, idempotency_key=idempotency_key).exists()

    @staticmethod
    def _state_of(escrow: EscrowRecord) -> dict:
        return {
            "original_amount_irr": escrow.original_amount_irr,
            "held_amount_irr": escrow.held_amount_irr,
            "releasable_amount_irr": escrow.releasable_amount_irr,
            "blocked_amount_irr": escrow.blocked_amount_irr,
            "released_amount_irr": escrow.released_amount_irr,
            "refunded_amount_irr": escrow.refunded_amount_irr,
            "remaining_amount_irr": escrow.remaining_amount_irr,
            "status": escrow.status,
        }

    @staticmethod
    def _zero_state() -> dict:
        return {
            "original_amount_irr": 0,
            "held_amount_irr": 0,
            "releasable_amount_irr": 0,
            "blocked_amount_irr": 0,
            "released_amount_irr": 0,
            "refunded_amount_irr": 0,
            "remaining_amount_irr": 0,
            "status": "",
        }

    @staticmethod
    def _record_movement(
        *,
        escrow,
        movement_type,
        amount_irr,
        before_state,
        after_state,
        source_type,
        source_id,
        actor,
        correlation_id,
        idempotency_key,
        reason,
    ) -> EscrowMovement:
        return EscrowMovement.objects.create(
            tenant_id=escrow.tenant_id,
            escrow=escrow,
            movement_type=movement_type,
            amount_irr=amount_irr,
            before_state=before_state,
            after_state=after_state,
            source_type=source_type,
            source_id=source_id,
            actor=actor,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            reason=reason or "",
        )

    @staticmethod
    def _audit(*, escrow, action, actor, reason, before, after) -> None:
        AuditService.log(
            tenant_id=escrow.tenant_id,
            action=action,
            resource_type="EscrowRecord",
            module_id=SOURCE_MODULE,
            actor_id=getattr(actor, "person_id", None),
            actor_type="system" if actor is None else "user",
            resource_id=escrow.id,
            before=before,
            after=after,
            reason=reason or "",
            audit_class=AuditClassification.FINANCIAL,
            metadata={
                "order_id": str(escrow.order_id) if escrow.order_id else None,
                "correlation_id": str(escrow.correlation_id) if escrow.correlation_id else None,
            },
        )

    @staticmethod
    def _publish(escrow: EscrowRecord, *, event_type: str, extra: dict) -> None:
        EventPublisher.publish(
            tenant_id=escrow.tenant_id,
            event_type=event_type,
            source_module=SOURCE_MODULE,
            source_entity_id=escrow.id,
            source_entity_type="EscrowRecord",
            payload={"currency": escrow.currency, **extra},
        )
