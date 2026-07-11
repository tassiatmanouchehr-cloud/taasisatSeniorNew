"""
LedgerService — Module 05 immutable ledger foundation.

The only code allowed to create LedgerEntry rows. Enforces that every
posting is balanced (debit total == credit total) within its
entry_group_id before anything is written, and that every entry
references a document, payment, or obligation — never a bare
ExecutionSession.
"""

import logging
import uuid
from decimal import Decimal

from django.db import transaction

from apps.kernel.services.event_publisher import EventPublisher
from apps.kernel.services.permission_service import PermissionService

from ..models import (
    DEFAULT_CURRENCY,
    FinancialDocument,
    FinancialObligation,
    FinancialParty,
    LedgerEntry,
    LedgerEntryType,
    PaymentTransaction,
)
from ..permission_keys import FINANCE_LEDGER_POST
from .errors import FinanceError

logger = logging.getLogger(__name__)

SOURCE_MODULE = "M05"


class LedgerService:
    """Posts balanced groups of immutable LedgerEntry rows."""

    @classmethod
    @transaction.atomic
    def post_entries(cls, *, tenant_id, entries, entry_group_id=None, actor=None) -> list[LedgerEntry]:
        PermissionService.require(actor, FINANCE_LEDGER_POST, tenant_id=tenant_id)

        if not entries:
            raise FinanceError("post_entries requires at least one entry.")

        entry_group_id = entry_group_id or uuid.uuid4()
        currencies = {entry.get("currency", DEFAULT_CURRENCY) for entry in entries}
        if len(currencies) > 1:
            raise FinanceError(f"Cannot post a mixed-currency ledger group: {currencies}.")
        currency = currencies.pop()

        debit_total = Decimal("0")
        credit_total = Decimal("0")
        prepared = []

        for entry in entries:
            party = FinancialParty.objects.get(id=entry["party_id"])
            if party.tenant_id != tenant_id:
                raise FinanceError("Ledger entry party does not belong to the posting tenant.")

            if not any(entry.get(ref) for ref in ("source_document_id", "payment_transaction_id", "obligation_id")):
                raise FinanceError(
                    "Every ledger entry must reference a source_document, payment_transaction, or obligation.",
                )

            source_document = None
            if entry.get("source_document_id"):
                source_document = FinancialDocument.objects.get(id=entry["source_document_id"])
                if source_document.tenant_id != tenant_id:
                    raise FinanceError("source_document does not belong to the posting tenant.")

            payment_transaction = None
            if entry.get("payment_transaction_id"):
                payment_transaction = PaymentTransaction.objects.get(id=entry["payment_transaction_id"])
                if payment_transaction.tenant_id != tenant_id:
                    raise FinanceError("payment_transaction does not belong to the posting tenant.")

            obligation = None
            if entry.get("obligation_id"):
                obligation = FinancialObligation.objects.get(id=entry["obligation_id"])
                if obligation.tenant_id != tenant_id:
                    raise FinanceError("obligation does not belong to the posting tenant.")

            amount = entry["amount"] if isinstance(entry["amount"], Decimal) else Decimal(str(entry["amount"]))
            entry_type = entry["entry_type"]

            if entry_type == LedgerEntryType.DEBIT:
                debit_total += amount
            elif entry_type == LedgerEntryType.CREDIT:
                credit_total += amount
            else:
                raise FinanceError(f"Unknown ledger entry_type: {entry_type}")

            prepared.append(LedgerEntry(
                tenant_id=tenant_id,
                entry_group_id=entry_group_id,
                party=party,
                source_document=source_document,
                payment_transaction=payment_transaction,
                obligation=obligation,
                entry_type=entry_type,
                account_code=entry["account_code"],
                amount=amount,
                currency=currency,
                description=entry.get("description", ""),
                metadata=entry.get("metadata", {}),
            ))

        if debit_total != credit_total:
            raise FinanceError(
                f"Unbalanced ledger posting: debit total {debit_total} != credit total {credit_total}.",
            )

        created = LedgerEntry.objects.bulk_create(prepared)

        EventPublisher.publish(
            tenant_id=tenant_id,
            event_type="Finance.Ledger.Posted.v1",
            source_module=SOURCE_MODULE,
            source_entity_id=None,
            source_entity_type="LedgerEntry",
            payload={
                "entry_group_id": str(entry_group_id),
                "entry_count": len(created),
                "debit_total": str(debit_total),
                "credit_total": str(credit_total),
                "currency": currency,
            },
        )

        return created
