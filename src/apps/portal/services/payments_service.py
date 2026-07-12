"""
CustomerPaymentsPresentationService — Epic 07 (Customer Experience and
Portal Completion).

Assembles the customer's payments/invoices summary page. Reuses
apps.finance.services.party_service.FinancialPartyService (already used
by dashboard_view) to resolve the customer's own FinancialParty, and the
new FinancialDocumentService.list_for_payer_party() read-only query
(Epic 07) — no new financial calculation, no mutation, no side effects.
"""

from decimal import Decimal

from apps.finance.models.document import FinancialDocumentStatus, FinancialDocumentType
from apps.finance.services.document_service import FinancialDocumentService
from apps.finance.services.party_service import FinancialPartyService
from apps.wallet.services.wallet_service import WalletService

from .viewmodels import PaymentRowViewModel, PaymentsSummaryViewModel

DOCUMENT_TYPE_LABELS = {
    FinancialDocumentType.INVOICE: "فاکتور",
    FinancialDocumentType.SUPPLEMENTAL_INVOICE: "فاکتور تکمیلی",
    FinancialDocumentType.CREDIT_NOTE: "یادداشت بستانکار",
    FinancialDocumentType.DEBIT_NOTE: "یادداشت بدهکار",
    FinancialDocumentType.REFUND_NOTE: "یادداشت استرداد",
    FinancialDocumentType.MANUAL_ADJUSTMENT: "تعدیل دستی",
}

DOCUMENT_STATUS_LABELS = {
    FinancialDocumentStatus.DRAFT: "پیش‌نویس",
    FinancialDocumentStatus.ISSUED: "صادرشده",
    FinancialDocumentStatus.LOCKED: "قطعی‌شده",
    FinancialDocumentStatus.CANCELLED: "لغوشده",
    FinancialDocumentStatus.VOIDED: "باطل‌شده",
    FinancialDocumentStatus.PAID: "پرداخت‌شده",
    FinancialDocumentStatus.PARTIALLY_PAID: "بخشی پرداخت‌شده",
    FinancialDocumentStatus.DISPUTED: "مورد اختلاف",
}

DOCUMENT_STATUS_VARIANTS = {
    FinancialDocumentStatus.PAID: "success",
    FinancialDocumentStatus.PARTIALLY_PAID: "warning",
    FinancialDocumentStatus.ISSUED: "primary",
    FinancialDocumentStatus.LOCKED: "neutral",
    FinancialDocumentStatus.DRAFT: "neutral",
    FinancialDocumentStatus.CANCELLED: "danger",
    FinancialDocumentStatus.VOIDED: "danger",
    FinancialDocumentStatus.DISPUTED: "danger",
}


class CustomerPaymentsPresentationService:
    """Read-only: assembles the payments/invoices summary page."""

    @classmethod
    def get_summary_view(cls, *, customer, tenant_id) -> PaymentsSummaryViewModel:
        party = FinancialPartyService.resolve_party_for_customer(customer)
        wallet = WalletService.get_wallet_or_none(party=party)
        documents = FinancialDocumentService.list_for_payer_party(tenant_id=tenant_id, party_id=party.id)

        total_paid = sum(
            (doc.total_amount for doc in documents if doc.status == FinancialDocumentStatus.PAID),
            Decimal("0"),
        )
        total_outstanding = sum(
            (
                doc.total_amount
                for doc in documents
                if doc.status in (FinancialDocumentStatus.ISSUED, FinancialDocumentStatus.PARTIALLY_PAID)
            ),
            Decimal("0"),
        )

        return PaymentsSummaryViewModel(
            wallet_balance_label=cls._money_label(wallet.balance) if wallet else "—",
            wallet_currency=wallet.currency if wallet else "",
            total_paid_label=cls._money_label(total_paid),
            total_outstanding_label=cls._money_label(total_outstanding),
            rows=tuple(cls.to_row(doc) for doc in documents),
        )

    @classmethod
    def get_rows_for_order(cls, *, tenant_id, order_id) -> tuple[PaymentRowViewModel, ...]:
        """The order-detail page's price/invoice summary — every
        FinancialDocument for exactly this order, via the dedicated
        FinancialDocumentService.list_for_order() query (never filters a
        customer-wide list client-side)."""
        documents = FinancialDocumentService.list_for_order(tenant_id=tenant_id, order_id=order_id)
        return tuple(cls.to_row(doc) for doc in documents)

    @staticmethod
    def to_row(document) -> PaymentRowViewModel:
        return PaymentRowViewModel(
            id=str(document.id),
            document_type_label=DOCUMENT_TYPE_LABELS.get(document.document_type, document.document_type),
            status_label=DOCUMENT_STATUS_LABELS.get(document.status, document.status),
            status_variant=DOCUMENT_STATUS_VARIANTS.get(document.status, "neutral"),
            total_amount_label=CustomerPaymentsPresentationService._money_label(document.total_amount),
            currency=document.currency,
            order_number=document.order.order_number if document.order_id else "",
            order_detail_url=f"/portal/requests/{document.order_id}/" if document.order_id else "",
            issued_at_label=document.issued_at.strftime("%Y/%m/%d") if document.issued_at else "",
        )

    @staticmethod
    def _money_label(amount) -> str:
        return f"{amount:,.0f}"
