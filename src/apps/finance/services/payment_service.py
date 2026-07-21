"""
PaymentService — Module 05 foundation.

Records internal payment transactions (no real gateway/bank integration —
ONLINE/CASH/CARD_TO_CARD/WALLET/MANUAL are internal statuses only). A
SUCCEEDED payment against an obligation resolves it partially or fully;
nothing here fabricates a payment that wasn't explicitly recorded.
"""

import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.kernel.services.permission_service import PermissionService

from ..models import (
    DEFAULT_CURRENCY,
    FinancialDocument,
    FinancialDocumentStatus,
    FinancialObligation,
    FinancialParty,
    ObligationStatus,
    PaymentStatus,
    PaymentTransaction,
)
from ..permission_keys import FINANCE_PAYMENT_RECORD
from .errors import FinanceError

logger = logging.getLogger(__name__)

SOURCE_MODULE = "M05"


class PaymentService:
    """Creates PaymentTransaction records and resolves obligations they satisfy."""

    @classmethod
    @transaction.atomic
    def record_payment(
        cls,
        *,
        payer_party_id,
        receiver_party_id,
        amount,
        payment_method,
        currency=None,
        source_document_id=None,
        obligation_id=None,
        status=PaymentStatus.SUCCEEDED,
        provider_reference="",
        collected_by_party_id=None,
        occurred_at=None,
        metadata=None,
        recorded_by=None,
    ) -> PaymentTransaction:
        from apps.kernel.services.event_publisher import EventPublisher

        payer_party = FinancialParty.objects.get(id=payer_party_id)
        receiver_party = FinancialParty.objects.get(id=receiver_party_id)
        tenant_id = payer_party.tenant_id

        PermissionService.require(recorded_by, FINANCE_PAYMENT_RECORD, tenant_id=tenant_id)

        if receiver_party.tenant_id != tenant_id:
            raise FinanceError("Payer and receiver parties belong to different tenants.")

        source_document = None
        if source_document_id:
            source_document = FinancialDocument.objects.select_for_update().get(id=source_document_id)
            if source_document.tenant_id != tenant_id:
                raise FinanceError("source_document does not belong to the payer's tenant.")

        obligation = None
        if obligation_id:
            obligation = FinancialObligation.objects.select_for_update().get(id=obligation_id)
            if obligation.tenant_id != tenant_id:
                raise FinanceError("obligation does not belong to the payer's tenant.")

        collected_by_party = None
        if collected_by_party_id:
            collected_by_party = FinancialParty.objects.get(id=collected_by_party_id)
            if collected_by_party.tenant_id != tenant_id:
                raise FinanceError("collected_by_party does not belong to the payer's tenant.")

        resolved_currency = (
            currency
            or (source_document.currency if source_document else None)
            or (obligation.currency if obligation else None)
            or DEFAULT_CURRENCY
        )

        payment = PaymentTransaction.objects.create(
            tenant_id=tenant_id,
            source_document=source_document,
            obligation=obligation,
            payer_party=payer_party,
            receiver_party=receiver_party,
            amount=amount,
            currency=resolved_currency,
            payment_method=payment_method,
            status=status,
            provider_reference=provider_reference,
            collected_by_party=collected_by_party,
            occurred_at=occurred_at or (timezone.now() if status == PaymentStatus.SUCCEEDED else None),
            metadata=metadata or {},
        )

        if status == PaymentStatus.SUCCEEDED and obligation is not None:
            cls._apply_payment_to_obligation(obligation, source_document)

        EventPublisher.publish(
            tenant_id=tenant_id,
            event_type="Finance.Payment.Recorded.v1",
            source_module=SOURCE_MODULE,
            source_entity_id=payment.id,
            source_entity_type="PaymentTransaction",
            payload={
                "amount": str(payment.amount),
                "currency": payment.currency,
                "payment_method": payment.payment_method,
                "status": payment.status,
                "obligation_id": str(obligation.id) if obligation else None,
                "source_document_id": str(source_document.id) if source_document else None,
            },
            actor_id=getattr(recorded_by, "person_id", None),
        )

        return payment

    # --- internal helpers -------------------------------------------------

    @staticmethod
    def _apply_payment_to_obligation(obligation: FinancialObligation, source_document):
        total_paid = obligation.payments.filter(status=PaymentStatus.SUCCEEDED).aggregate(
            total=Sum("amount"),
        )["total"] or Decimal("0")

        if total_paid >= obligation.amount:
            obligation.status = ObligationStatus.RESOLVED
            obligation.resolved_at = timezone.now()
        elif total_paid > 0:
            obligation.status = ObligationStatus.PARTIALLY_RESOLVED
        obligation.save(update_fields=["status", "resolved_at", "updated_at"])

        document = source_document or obligation.source_document
        if document is not None:
            if obligation.status == ObligationStatus.RESOLVED:
                document.status = FinancialDocumentStatus.PAID
                document.paid_at = timezone.now()
                document.save(update_fields=["status", "paid_at", "updated_at"])
            elif obligation.status == ObligationStatus.PARTIALLY_RESOLVED:
                document.status = FinancialDocumentStatus.PARTIALLY_PAID
                document.save(update_fields=["status", "updated_at"])
