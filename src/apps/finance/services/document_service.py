"""
FinancialDocumentService (InvoiceService) — Module 05 foundation.

Builds FinancialDocument + FinancialDocumentItem rows from a CLOSED
ExecutionSession. This is the entry point into the financial flow:

    ExecutionSession CLOSED -> FinancialDocument -> FinancialObligation -> ...

Never mutates ExecutionSession or Order — only reads them to resolve
context and parties.
"""

import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.execution.models import ExecutionSession, ExecutionSessionStatus
from apps.kernel.services.event_publisher import EventPublisher
from apps.kernel.services.permission_service import PermissionService
from apps.orders.models import Order

from ..models import (
    FinancialDocument,
    FinancialDocumentItem,
    FinancialDocumentItemType,
    FinancialDocumentStatus,
    FinancialDocumentType,
)
from .errors import FinanceError
from .party_service import FinancialPartyService

logger = logging.getLogger(__name__)

SOURCE_MODULE = "M05"

_NON_SUBTOTAL_ITEM_TYPES = (FinancialDocumentItemType.DISCOUNT, FinancialDocumentItemType.TAX)

_EDITABLE_STATUSES = (FinancialDocumentStatus.DRAFT, FinancialDocumentStatus.ISSUED)


def _to_decimal(value) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


class FinancialDocumentService:
    """Creates and transitions FinancialDocument records."""

    @classmethod
    @transaction.atomic
    def create_invoice_from_execution(cls, *, execution_session_id, items, issued_by=None) -> FinancialDocument:
        execution_session = ExecutionSession.objects.select_related("order").get(id=execution_session_id)

        if execution_session.status != ExecutionSessionStatus.CLOSED:
            raise FinanceError(
                f"Cannot create an invoice from an ExecutionSession in '{execution_session.status}' status; "
                "it must be CLOSED.",
            )

        return cls._create_document(
            document_type=FinancialDocumentType.INVOICE,
            tenant_id=execution_session.tenant_id,
            order=execution_session.order,
            execution_session=execution_session,
            items=items,
            issued_by=issued_by,
        )

    @classmethod
    @transaction.atomic
    def create_supplemental_invoice(
        cls, *, items, execution_session_id=None, order_id=None, issued_by=None,
    ) -> FinancialDocument:
        execution_session = None
        if execution_session_id:
            execution_session = ExecutionSession.objects.select_related("order").get(id=execution_session_id)
            order = execution_session.order
        elif order_id:
            order = Order.objects.get(id=order_id)
        else:
            raise FinanceError("create_supplemental_invoice requires execution_session_id or order_id.")

        return cls._create_document(
            document_type=FinancialDocumentType.SUPPLEMENTAL_INVOICE,
            tenant_id=order.tenant_id,
            order=order,
            execution_session=execution_session,
            items=items,
            issued_by=issued_by,
        )

    @classmethod
    @transaction.atomic
    def issue_document(cls, *, document_id, changed_by=None) -> FinancialDocument:
        document = FinancialDocument.objects.select_for_update().get(id=document_id)

        PermissionService.require(changed_by, "finance.document.issue", tenant_id=document.tenant_id)

        if document.status != FinancialDocumentStatus.DRAFT:
            raise FinanceError(f"Cannot issue a document in '{document.status}' status.")

        document.status = FinancialDocumentStatus.ISSUED
        document.issued_at = timezone.now()
        document.save(update_fields=["status", "issued_at", "updated_at"])

        EventPublisher.publish(
            tenant_id=document.tenant_id,
            event_type="Finance.Document.Issued.v1",
            source_module=SOURCE_MODULE,
            source_entity_id=document.id,
            source_entity_type="FinancialDocument",
            payload={"document_type": document.document_type, "total_amount": str(document.total_amount)},
            actor_id=cls._actor_id(changed_by),
        )

        return document

    @classmethod
    @transaction.atomic
    def lock_document(cls, *, document_id, changed_by=None) -> FinancialDocument:
        document = FinancialDocument.objects.select_for_update().get(id=document_id)

        PermissionService.require(changed_by, "finance.document.lock", tenant_id=document.tenant_id)

        if document.status not in _EDITABLE_STATUSES:
            raise FinanceError(f"Cannot lock a document in '{document.status}' status.")

        document.status = FinancialDocumentStatus.LOCKED
        document.locked_at = timezone.now()
        document.save(update_fields=["status", "locked_at", "updated_at"])

        EventPublisher.publish(
            tenant_id=document.tenant_id,
            event_type="Finance.Document.Locked.v1",
            source_module=SOURCE_MODULE,
            source_entity_id=document.id,
            source_entity_type="FinancialDocument",
            payload={"document_type": document.document_type, "total_amount": str(document.total_amount)},
            actor_id=cls._actor_id(changed_by),
        )

        return document

    @classmethod
    @transaction.atomic
    def cancel_document(cls, *, document_id, changed_by=None) -> FinancialDocument:
        document = FinancialDocument.objects.select_for_update().get(id=document_id)

        if document.status not in _EDITABLE_STATUSES:
            raise FinanceError(f"Cannot cancel a document in '{document.status}' status.")

        document.status = FinancialDocumentStatus.CANCELLED
        document.save(update_fields=["status", "updated_at"])

        return document

    # --- internal helpers -------------------------------------------------

    @classmethod
    def _create_document(cls, *, document_type, tenant_id, order, execution_session, items, issued_by) -> FinancialDocument:
        if order.tenant_id != tenant_id:
            raise FinanceError("Order tenant does not match the resolved tenant for this document.")
        if not order.customer_profile_id:
            raise FinanceError("Cannot create a financial document: order has no linked customer to bill.")

        issuer_party = FinancialPartyService.resolve_platform_party(_tenant(tenant_id))
        payer_party = FinancialPartyService.resolve_party_for_customer(order.customer_profile)
        beneficiary_party = None
        if order.assigned_supplier_id:
            beneficiary_party = FinancialPartyService.resolve_party_for_supplier(order.assigned_supplier)

        prepared_items, subtotal, discount, tax, total = cls._build_items(items)

        document = FinancialDocument.objects.create(
            tenant_id=tenant_id,
            document_type=document_type,
            order=order,
            execution_session=execution_session,
            issuer_party=issuer_party,
            payer_party=payer_party,
            beneficiary_party=beneficiary_party,
            status=FinancialDocumentStatus.DRAFT,
            subtotal_amount=subtotal,
            discount_amount=discount,
            tax_amount=tax,
            total_amount=total,
            pricing_snapshot={
                "items": [
                    {
                        "item_type": item["item_type"],
                        "description": item["description"],
                        "quantity": str(item["quantity"]),
                        "unit_price": str(item["unit_price"]),
                        "total_amount": str(item["total_amount"]),
                    }
                    for item in prepared_items
                ],
                "subtotal_amount": str(subtotal),
                "discount_amount": str(discount),
                "tax_amount": str(tax),
                "total_amount": str(total),
                "computed_at": timezone.now().isoformat(),
                "issued_by": str(issued_by) if issued_by else None,
            },
        )

        FinancialDocumentItem.objects.bulk_create([
            FinancialDocumentItem(
                tenant_id=tenant_id,
                document=document,
                item_type=item["item_type"],
                description=item["description"],
                quantity=item["quantity"],
                unit_price=item["unit_price"],
                total_amount=item["total_amount"],
                metadata=item.get("metadata", {}),
            )
            for item in prepared_items
        ])

        EventPublisher.publish(
            tenant_id=tenant_id,
            event_type="Finance.Document.Created.v1",
            source_module=SOURCE_MODULE,
            source_entity_id=document.id,
            source_entity_type="FinancialDocument",
            payload={
                "document_type": document_type,
                "order_id": str(order.id),
                "total_amount": str(total),
            },
            actor_id=cls._actor_id(issued_by),
        )

        return document

    @staticmethod
    def _build_items(items):
        prepared = []
        subtotal = Decimal("0")
        discount = Decimal("0")
        tax = Decimal("0")

        for raw in items:
            quantity = _to_decimal(raw.get("quantity", 1))
            unit_price = _to_decimal(raw["unit_price"])
            line_total = (quantity * unit_price).quantize(Decimal("0.01"))
            item_type = raw["item_type"]

            prepared.append({
                "item_type": item_type,
                "description": raw.get("description", ""),
                "quantity": quantity,
                "unit_price": unit_price,
                "total_amount": line_total,
                "metadata": raw.get("metadata", {}),
            })

            if item_type == FinancialDocumentItemType.DISCOUNT:
                discount += abs(line_total)
            elif item_type == FinancialDocumentItemType.TAX:
                tax += line_total
            else:
                subtotal += line_total

        total = subtotal - discount + tax
        return prepared, subtotal, discount, tax, total

    @staticmethod
    def _actor_id(user):
        return getattr(user, "person_id", None)


def _tenant(tenant_id):
    from apps.kernel.models.tenant import Tenant

    return Tenant.objects.get(id=tenant_id)


# Alias per the Module 05 spec ("InvoiceService / FinancialDocumentService").
InvoiceService = FinancialDocumentService
