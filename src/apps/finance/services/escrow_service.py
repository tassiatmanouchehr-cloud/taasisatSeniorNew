"""
EscrowService — Module 05 escrow foundation.

Holds funds against a document, then releases or refunds them. No real
bank transfer happens here — this only tracks the internal HELD /
RELEASED / REFUNDED state.
"""

import logging

from django.db import transaction
from django.utils import timezone

from apps.kernel.services.event_publisher import EventPublisher

from ..models import DEFAULT_CURRENCY, EscrowRecord, EscrowStatus, FinancialDocument, FinancialParty
from .errors import FinanceError

logger = logging.getLogger(__name__)

SOURCE_MODULE = "M05"


class EscrowService:
    """Creates and transitions EscrowRecord rows."""

    @classmethod
    @transaction.atomic
    def hold(cls, *, source_document_id, payer_party_id, amount, beneficiary_party_id=None, currency=None, metadata=None) -> EscrowRecord:
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
