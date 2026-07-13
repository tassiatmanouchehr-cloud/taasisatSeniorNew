"""
DisputeResolutionService — Financial Core PR-B.

Platform-authorized resolution of an OPEN dispute: allocates its exact
blocked amount into customer refund and/or platform/company/caregiver
release, conserving the blocked amount exactly (enforced at the database
level via DisputeResolution's own CheckConstraint). Unblocks the disputed
amount back into the Escrow's remaining bucket first, then creates a
RefundInstruction (if any customer_refund_amount_irr) and/or a
ReleaseInstruction (if any platform/company/caregiver amount) against that
now-unblocked remaining — never crediting a wallet directly.
"""

from django.db import transaction

from apps.finance.models import EscrowRecord
from apps.kernel.events.base import DISPUTE_RESOLVED, DomainEvent
from apps.kernel.events.publisher import publish as publish_domain_event
from apps.kernel.models.audit import AuditClassification
from apps.kernel.services.audit_service import AuditService
from apps.kernel.services.permission_service import PermissionService

from ..models.dispute import OPEN_DISPUTE_STATUSES, Dispute, DisputeResolution, DisputeStatus
from ..models.release_instruction import RefundInstructionSource, ReleaseInstructionSource
from ..permission_keys import COMMISSION_DISPUTE_RESOLVE
from .configuration import CommissionConfiguration
from .errors import DisputeError
from .refund_instruction_service import RefundInstructionService
from .release_instruction_service import ReleaseInstructionService

SOURCE_MODULE = "M05"


class DisputeResolutionService:
    @classmethod
    @transaction.atomic
    def resolve(
        cls,
        *,
        dispute_id,
        reason: str,
        actor,
        idempotency_key: str,
        customer_refund_amount_irr: int = 0,
        platform_amount_irr: int = 0,
        company_amount_irr: int = 0,
        caregiver_amount_irr: int = 0,
    ) -> DisputeResolution:
        dispute = Dispute.objects.select_for_update().get(id=dispute_id)
        PermissionService.require(actor, COMMISSION_DISPUTE_RESOLVE, tenant_id=dispute.tenant_id)

        if not CommissionConfiguration.get_dispute_release_enabled(tenant_id=dispute.tenant_id):
            raise DisputeError(f"Dispute/release is not enabled for tenant {dispute.tenant_id}.")

        existing = DisputeResolution.objects.filter(
            tenant_id=dispute.tenant_id,
            idempotency_key=idempotency_key,
        ).first()
        if existing is not None:
            return existing

        if dispute.status not in OPEN_DISPUTE_STATUSES:
            raise DisputeError(f"Cannot resolve a dispute in '{dispute.status}' status.")

        allocated_total = customer_refund_amount_irr + platform_amount_irr + company_amount_irr + caregiver_amount_irr
        if allocated_total != dispute.disputed_amount_irr:
            raise DisputeError(
                f"Resolution allocation must sum to exactly the disputed amount "
                f"({dispute.disputed_amount_irr}); got {allocated_total}.",
            )
        for label, value in (
            ("customer_refund_amount_irr", customer_refund_amount_irr),
            ("platform_amount_irr", platform_amount_irr),
            ("company_amount_irr", company_amount_irr),
            ("caregiver_amount_irr", caregiver_amount_irr),
        ):
            if value < 0:
                raise DisputeError(f"{label} cannot be negative.")

        commission_snapshot = dispute.escrow.commission_snapshot

        resolution = DisputeResolution.objects.create(
            tenant_id=dispute.tenant_id,
            dispute=dispute,
            commission_snapshot=commission_snapshot,
            total_blocked_amount_irr=dispute.disputed_amount_irr,
            customer_refund_amount_irr=customer_refund_amount_irr,
            platform_amount_irr=platform_amount_irr,
            company_amount_irr=company_amount_irr,
            caregiver_amount_irr=caregiver_amount_irr,
            reason=reason,
            actor=actor,
            idempotency_key=idempotency_key,
        )

        escrow = EscrowRecord.objects.select_for_update().get(id=dispute.escrow_id)

        from apps.finance.services import EscrowService

        EscrowService.unblock(
            escrow_id=escrow.id,
            amount_irr=dispute.disputed_amount_irr,
            dispute_id=dispute.id,
            actor=actor,
            reason=f"Dispute resolved: {reason}",
            idempotency_key=f"dispute-unblock:{resolution.id}",
        )

        if customer_refund_amount_irr > 0:
            RefundInstructionService.create(
                escrow=escrow,
                order=dispute.order,
                invoice=dispute.invoice,
                amount_irr=customer_refund_amount_irr,
                source=RefundInstructionSource.DISPUTE_RESOLUTION,
                reason=reason,
                actor=actor,
                idempotency_key=f"dispute-refund:{resolution.id}",
                dispute_resolution=resolution,
            )

        release_total = platform_amount_irr + company_amount_irr + caregiver_amount_irr
        if release_total > 0:
            ReleaseInstructionService.create(
                escrow=escrow,
                order=dispute.order,
                invoice=dispute.invoice,
                commission_snapshot=commission_snapshot,
                source=ReleaseInstructionSource.DISPUTE_RESOLUTION,
                amount_irr=release_total,
                actor=actor,
                reason=reason,
                idempotency_key=f"dispute-release:{resolution.id}",
                dispute_resolution=resolution,
            )

        dispute.status = DisputeStatus.RESOLVED
        dispute.resolution_type = cls._resolution_type_label(
            customer_refund_amount_irr,
            platform_amount_irr,
            company_amount_irr,
            caregiver_amount_irr,
        )
        from django.utils import timezone

        dispute.resolved_at = timezone.now()
        dispute.resolved_by = actor
        dispute.save(update_fields=["status", "resolution_type", "resolved_at", "resolved_by", "updated_at"])

        AuditService.log(
            tenant_id=dispute.tenant_id,
            action="commission.dispute.resolve",
            resource_type="Dispute",
            module_id=SOURCE_MODULE,
            actor_id=getattr(actor, "person_id", None),
            resource_id=dispute.id,
            reason=reason,
            audit_class=AuditClassification.FINANCIAL,
            after={
                "resolution_id": str(resolution.id),
                "customer_refund_amount_irr": customer_refund_amount_irr,
                "platform_amount_irr": platform_amount_irr,
                "company_amount_irr": company_amount_irr,
                "caregiver_amount_irr": caregiver_amount_irr,
            },
        )

        if dispute.order.customer_profile_id:
            order = dispute.order
            domain_event = DomainEvent(
                event_type=DISPUTE_RESOLVED,
                tenant_id=order.tenant_id,
                aggregate_type="Order",
                aggregate_id=order.id,
                actor_id=getattr(actor, "person_id", None),
                payload={
                    "recipient_id": str(order.customer_profile.person_id),
                    "resolution_type": dispute.resolution_type,
                },
            )
            transaction.on_commit(lambda: publish_domain_event(domain_event))

        return resolution

    @staticmethod
    def _resolution_type_label(refund, platform, company, caregiver) -> str:
        has_refund = refund > 0
        has_release = (platform + company + caregiver) > 0
        if has_refund and has_release:
            return "MIXED"
        if has_refund:
            return "FULL_REFUND"
        return "FULL_RELEASE"
