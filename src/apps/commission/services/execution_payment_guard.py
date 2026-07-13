"""
ExecutionPaymentGuardService — Financial Core PR-B (Section 20).

Called from apps.execution.services.session_service.ExecutionService
.start_session() before it starts an execution session. When pre-service
payment is enabled for the tenant, execution must not start until the
order's payment is held in Escrow — a provider attempting to start
execution without paid Escrow gets an explicit domain error, no
ExecutionSession is created, no financial mutation happens.

A no-op (returns silently) when pre-service payment is disabled for the
tenant — preserves the exact pre-PR-B behavior for every tenant that has
not adopted the new flow, matching every other PR-B feature gate's own
"disabled means unchanged legacy behavior" contract."""

from apps.finance.models import EscrowRecord, EscrowStatus

from .configuration import CommissionConfiguration
from .errors import ExecutionPaymentGuardError


class ExecutionPaymentGuardService:
    @classmethod
    def assert_can_start_execution(cls, *, order) -> None:
        if not CommissionConfiguration.get_preservice_payment_enabled(tenant_id=order.tenant_id):
            return

        escrow = EscrowRecord.objects.filter(tenant_id=order.tenant_id, order=order).order_by("-created_at").first()
        if escrow is None or escrow.status not in (
            EscrowStatus.HELD,
            EscrowStatus.PARTIALLY_RELEASED,
            EscrowStatus.PARTIALLY_REFUNDED,
        ):
            raise ExecutionPaymentGuardError(
                f"Order {order.id} has no Escrow-held payment; execution cannot start until "
                "the pre-service payment is captured and held.",
            )
