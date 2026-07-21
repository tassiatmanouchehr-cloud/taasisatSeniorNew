"""
ObligationService — Module 05 foundation.

Turns an ISSUED/LOCKED FinancialDocument into a FinancialObligation (the
customer owes the issuer the document total). Never posts to the ledger —
that only happens when PaymentService/LedgerService are invoked explicitly.
"""

import logging

from django.db import transaction

from ..models import FinancialDocument, FinancialDocumentStatus, FinancialObligation, ObligationStatus, ObligationType
from .errors import FinanceError

logger = logging.getLogger(__name__)

SOURCE_MODULE = "M05"

_OBLIGATION_ELIGIBLE_STATUSES = (
    FinancialDocumentStatus.ISSUED,
    FinancialDocumentStatus.LOCKED,
    FinancialDocumentStatus.PARTIALLY_PAID,
)


class ObligationService:
    """Creates FinancialObligation records from FinancialDocument totals."""

    @classmethod
    @transaction.atomic
    def create_obligations_for_document(cls, *, document_id) -> FinancialObligation:
        from apps.kernel.services.event_publisher import EventPublisher

        document = (
            FinancialDocument.objects.select_related("payer_party", "issuer_party")
            .select_for_update()
            .get(
                id=document_id,
            )
        )

        if document.status not in _OBLIGATION_ELIGIBLE_STATUSES:
            raise FinanceError(
                f"Cannot create obligations for a document in '{document.status}' status; it must be ISSUED or LOCKED.",
            )

        if (
            document.payer_party.tenant_id != document.tenant_id
            or document.issuer_party.tenant_id != document.tenant_id
        ):
            raise FinanceError("Document parties do not belong to the document's tenant.")

        obligation = FinancialObligation.objects.create(
            tenant_id=document.tenant_id,
            source_document=document,
            debtor_party=document.payer_party,
            creditor_party=document.issuer_party,
            amount=document.total_amount,
            currency=document.currency,
            obligation_type=ObligationType.INVOICE_PAYMENT,
            status=ObligationStatus.CREATED,
        )

        EventPublisher.publish(
            tenant_id=document.tenant_id,
            event_type="Finance.Obligation.Created.v1",
            source_module=SOURCE_MODULE,
            source_entity_id=obligation.id,
            source_entity_type="FinancialObligation",
            payload={
                "source_document_id": str(document.id),
                "debtor_party_id": str(obligation.debtor_party_id),
                "creditor_party_id": str(obligation.creditor_party_id),
                "amount": str(obligation.amount),
            },
        )

        return obligation
