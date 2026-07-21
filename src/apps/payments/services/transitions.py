"""Explicit, validated PaymentStatus state machine — shared by PaymentIntentService and PaymentCallbackService."""

from ..models import PaymentStatus

ALLOWED_TRANSITIONS = {
    PaymentStatus.CREATED: {PaymentStatus.PENDING, PaymentStatus.CANCELLED, PaymentStatus.EXPIRED},
    PaymentStatus.PENDING: {
        PaymentStatus.AUTHORIZED,
        PaymentStatus.SUCCEEDED,
        PaymentStatus.FAILED,
        PaymentStatus.CANCELLED,
        PaymentStatus.EXPIRED,
    },
    PaymentStatus.AUTHORIZED: {
        PaymentStatus.SUCCEEDED,
        PaymentStatus.FAILED,
        PaymentStatus.CANCELLED,
        PaymentStatus.EXPIRED,
    },
    # SUCCEEDED/FAILED/CANCELLED/EXPIRED are terminal: no further transitions.
}


def is_transition_allowed(current: str, target: str) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, frozenset())
