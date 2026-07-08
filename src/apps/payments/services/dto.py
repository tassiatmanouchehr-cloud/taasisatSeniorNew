"""Payment result DTO — Module 15 foundation. Mirrors the frozen-dataclass DTO convention
established by apps.matching.services.eligibility.EligibilityResult / apps.kernel.events.base.DomainEvent."""

import uuid
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PaymentResult:
    """Returned by PaymentIntentService/PaymentCallbackService calls."""

    intent_id: uuid.UUID
    attempt_id: uuid.UUID | None
    status: str
    amount: Decimal
    currency: str
    provider_reference: str | None = None
    idempotent_replay: bool = False
    message: str = ""
