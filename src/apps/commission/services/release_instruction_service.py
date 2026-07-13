"""
ReleaseInstructionService — Financial Core PR-B.

Creates exactly one immutable ReleaseInstruction per exact release event
and, in the same transaction, consumes the released amount out of the
Escrow's remaining_amount_irr into released_amount_irr via
EscrowService.apply_release(). Never credits a wallet — see
apps.commission.models.release_instruction.ReleaseInstruction's own
docstring for the PR-C consumption boundary this stops at.
"""

from django.db import transaction

from apps.finance.services import EscrowService
from apps.kernel.events.base import RELEASE_INSTRUCTION_CREATED, DomainEvent
from apps.kernel.events.publisher import publish as publish_domain_event
from apps.kernel.models.audit import AuditClassification
from apps.kernel.services.audit_service import AuditService

from ..models.release_instruction import ReleaseInstruction, ReleaseInstructionStatus
from .configuration import CommissionConfiguration
from .errors import CommissionError

SOURCE_MODULE = "M05"


class ReleaseInstructionService:
    @classmethod
    @transaction.atomic
    def create(
        cls,
        *,
        escrow,
        order,
        invoice,
        commission_snapshot,
        source: str,
        amount_irr: int,
        actor=None,
        reason: str,
        idempotency_key: str,
        dispute_resolution=None,
    ) -> ReleaseInstruction:
        if not CommissionConfiguration.get_dispute_release_enabled(tenant_id=escrow.tenant_id):
            raise CommissionError(
                f"Dispute/release is not enabled for tenant {escrow.tenant_id}; cannot create a ReleaseInstruction.",
            )
        if amount_irr <= 0:
            raise CommissionError("ReleaseInstruction amount must be positive.")

        existing = ReleaseInstruction.objects.filter(
            tenant_id=escrow.tenant_id,
            idempotency_key=idempotency_key,
        ).first()
        if existing is not None:
            return existing

        EscrowService.apply_release(
            escrow_id=escrow.id,
            amount_irr=amount_irr,
            source_type="ReleaseInstruction",
            source_id=None,
            actor=actor,
            reason=reason,
            idempotency_key=f"release-apply:{idempotency_key}",
        )

        instruction = ReleaseInstruction.objects.create(
            tenant_id=escrow.tenant_id,
            escrow=escrow,
            order=order,
            invoice=invoice,
            commission_snapshot=commission_snapshot,
            dispute_resolution=dispute_resolution,
            source=source,
            gross_releasable_amount_irr=amount_irr,
            currency=escrow.currency,
            status=ReleaseInstructionStatus.READY,
            idempotency_key=idempotency_key,
        )

        AuditService.log(
            tenant_id=escrow.tenant_id,
            action="commission.release_instruction.create",
            resource_type="ReleaseInstruction",
            module_id=SOURCE_MODULE,
            actor_id=getattr(actor, "person_id", None),
            actor_type="system" if actor is None else "user",
            resource_id=instruction.id,
            reason=reason,
            audit_class=AuditClassification.FINANCIAL,
            after={
                "order_id": str(order.id),
                "source": source,
                "gross_releasable_amount_irr": amount_irr,
            },
        )

        if order.customer_profile_id:
            domain_event = DomainEvent(
                event_type=RELEASE_INSTRUCTION_CREATED,
                tenant_id=escrow.tenant_id,
                aggregate_type="Order",
                aggregate_id=order.id,
                actor_id=getattr(actor, "person_id", None),
                payload={
                    "recipient_id": str(order.customer_profile.person_id),
                    "gross_releasable_amount_irr": amount_irr,
                },
            )
            transaction.on_commit(lambda: publish_domain_event(domain_event))

        return instruction
