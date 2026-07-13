"""
RefundInstructionService — Financial Core PR-B (Section 16).

Held-Escrow refund: money that never left Escrow being returned to the
customer, distinct from a post-settlement clawback (reserved for PR-E — no
wallet has ever been credited for PR-B money, so there is nothing to claw
back). Consumes the refunded amount out of Escrow's remaining_amount_irr
via EscrowService.apply_refund() in the same transaction the
RefundInstruction row is created in. Actual PSP refund execution is a
separate, later step (initiate()) behind a narrow adapter boundary — the
Fake provider's refund simulation, when available, is the only adapter
wired up in PR-B.
"""

from django.db import transaction

from apps.finance.services import EscrowService
from apps.kernel.events.base import (
    REFUND_INSTRUCTION_COMPLETED,
    REFUND_INSTRUCTION_FAILED,
    REFUND_INSTRUCTION_INITIATED,
    DomainEvent,
)
from apps.kernel.events.publisher import publish as publish_domain_event
from apps.kernel.models.audit import AuditClassification
from apps.kernel.services.audit_service import AuditService
from apps.kernel.services.permission_service import PermissionService

from ..models.release_instruction import RefundInstruction, RefundInstructionStatus
from ..permission_keys import COMMISSION_REFUND_AUTHORIZE
from .configuration import CommissionConfiguration
from .errors import CommissionError

SOURCE_MODULE = "M05"


class RefundInstructionService:
    @classmethod
    @transaction.atomic
    def create(
        cls,
        *,
        escrow,
        order,
        invoice,
        amount_irr: int,
        source: str,
        reason: str,
        actor=None,
        idempotency_key: str,
        dispute_resolution=None,
    ) -> RefundInstruction:
        """Internal entry point shared by DisputeResolutionService and
        create_manual() below — does not itself enforce a permission check
        (the caller already did, with the appropriate key for its own
        action: COMMISSION_DISPUTE_RESOLVE for a dispute-driven refund,
        COMMISSION_REFUND_AUTHORIZE for a manual one)."""
        if not CommissionConfiguration.get_dispute_release_enabled(tenant_id=escrow.tenant_id):
            raise CommissionError(
                f"Dispute/release is not enabled for tenant {escrow.tenant_id}; cannot create a RefundInstruction.",
            )
        if amount_irr <= 0:
            raise CommissionError("RefundInstruction amount must be positive.")

        existing = RefundInstruction.objects.filter(
            tenant_id=escrow.tenant_id,
            idempotency_key=idempotency_key,
        ).first()
        if existing is not None:
            return existing

        EscrowService.apply_refund(
            escrow_id=escrow.id,
            amount_irr=amount_irr,
            source_type="RefundInstruction",
            source_id=None,
            actor=actor,
            reason=reason,
            idempotency_key=f"refund-apply:{idempotency_key}",
        )

        instruction = RefundInstruction.objects.create(
            tenant_id=escrow.tenant_id,
            escrow=escrow,
            order=order,
            invoice=invoice,
            dispute_resolution=dispute_resolution,
            amount_irr=amount_irr,
            reason=reason,
            source=source,
            status=RefundInstructionStatus.PENDING,
            idempotency_key=idempotency_key,
        )

        AuditService.log(
            tenant_id=escrow.tenant_id,
            action="commission.refund_instruction.create",
            resource_type="RefundInstruction",
            module_id=SOURCE_MODULE,
            actor_id=getattr(actor, "person_id", None),
            actor_type="system" if actor is None else "user",
            resource_id=instruction.id,
            reason=reason,
            audit_class=AuditClassification.FINANCIAL,
            after={"order_id": str(order.id), "source": source, "amount_irr": amount_irr},
        )

        return instruction

    @classmethod
    @transaction.atomic
    def create_manual(cls, *, escrow, order, invoice, amount_irr: int, reason: str, actor, idempotency_key: str):
        PermissionService.require(actor, COMMISSION_REFUND_AUTHORIZE, tenant_id=escrow.tenant_id)
        from ..models.release_instruction import RefundInstructionSource

        return cls.create(
            escrow=escrow,
            order=order,
            invoice=invoice,
            amount_irr=amount_irr,
            source=RefundInstructionSource.MANUAL,
            reason=reason,
            actor=actor,
            idempotency_key=idempotency_key,
        )

    @classmethod
    @transaction.atomic
    def initiate(cls, *, refund_instruction_id, actor=None) -> RefundInstruction:
        """Calls the registered PSP adapter's refund simulation (Fake
        provider only, in PR-B) and marks the instruction INITIATED then
        COMPLETED/FAILED based on the (synchronous, Fake-only) result. A
        real async PSP refund callback path is deferred — out of scope for
        PR-B, matching Section 16's own 'PSP refund adapter boundary' framing
        as a boundary to establish, not a real gateway integration to
        complete here."""
        instruction = RefundInstruction.objects.select_for_update().get(id=refund_instruction_id)
        if instruction.status != RefundInstructionStatus.PENDING:
            return instruction

        instruction.status = RefundInstructionStatus.INITIATED
        instruction.save(update_fields=["status"])

        from apps.payments.services.provider_registry import PaymentProviderRegistry

        try:
            adapter = PaymentProviderRegistry.get_adapter("FAKE")
            result = adapter.refund_payment(
                amount=instruction.amount_irr, metadata={"instruction_id": str(instruction.id)}
            )
            instruction.psp_reference = result.get("provider_reference", "")
            instruction.status = RefundInstructionStatus.COMPLETED
        except Exception:  # noqa: BLE001 — recorded, not swallowed
            instruction.status = RefundInstructionStatus.FAILED
        finally:
            from django.utils import timezone

            instruction.completed_at = timezone.now()
            instruction.save(update_fields=["status", "psp_reference", "completed_at"])

        AuditService.log(
            tenant_id=instruction.tenant_id,
            action="commission.refund_instruction.initiate",
            resource_type="RefundInstruction",
            module_id=SOURCE_MODULE,
            actor_id=getattr(actor, "person_id", None),
            actor_type="system" if actor is None else "user",
            resource_id=instruction.id,
            audit_class=AuditClassification.FINANCIAL,
            after={"status": instruction.status, "psp_reference": instruction.psp_reference},
        )

        cls._publish_customer_event(event_type=REFUND_INSTRUCTION_INITIATED, instruction=instruction, actor=actor)
        if instruction.status == RefundInstructionStatus.COMPLETED:
            cls._publish_customer_event(event_type=REFUND_INSTRUCTION_COMPLETED, instruction=instruction, actor=actor)
        elif instruction.status == RefundInstructionStatus.FAILED:
            cls._publish_customer_event(event_type=REFUND_INSTRUCTION_FAILED, instruction=instruction, actor=actor)

        return instruction

    @staticmethod
    def _publish_customer_event(*, event_type, instruction, actor) -> None:
        order = instruction.order
        if not order.customer_profile_id:
            return
        domain_event = DomainEvent(
            event_type=event_type,
            tenant_id=instruction.tenant_id,
            aggregate_type="Order",
            aggregate_id=order.id,
            actor_id=getattr(actor, "person_id", None),
            payload={"recipient_id": str(order.customer_profile.person_id), "amount_irr": instruction.amount_irr},
        )
        transaction.on_commit(lambda: publish_domain_event(domain_event))
