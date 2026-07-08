"""
FinancialReportService — Module 16 foundation.

Read-only Decimal-safe aggregation over Finance/Wallet. Never mutates
either — no FinancialDocument/PaymentTransaction/Wallet writes.
"""

import uuid
from decimal import Decimal

from django.db.models import Count, Sum

from apps.finance.models import FinancialDocument, FinancialDocumentStatus, FinancialDocumentType, PaymentStatus, PaymentTransaction
from apps.wallet.models import Wallet, WalletTransaction

from ..dto import FinancialSummaryReport

_ZERO = Decimal("0")


class FinancialReportService:
    """Deterministic, tenant-scoped financial summary aggregation."""

    @classmethod
    def get_financial_summary(cls, tenant_id: uuid.UUID) -> FinancialSummaryReport:
        invoices = FinancialDocument.objects.for_tenant(tenant_id).filter(
            document_type=FinancialDocumentType.INVOICE,
        ).exclude(status=FinancialDocumentStatus.DRAFT).aggregate(
            count=Count("id"), total=Sum("total_amount"),
        )

        payments = PaymentTransaction.objects.for_tenant(tenant_id).filter(
            status=PaymentStatus.SUCCEEDED,
        ).aggregate(count=Count("id"), total=Sum("amount"))

        wallets = Wallet.objects.for_tenant(tenant_id).aggregate(total=Sum("balance"))

        wallet_transactions = WalletTransaction.objects.for_tenant(tenant_id).aggregate(
            count=Count("id"), total=Sum("amount"),
        )

        return FinancialSummaryReport(
            tenant_id=tenant_id,
            invoices_issued_count=invoices["count"] or 0,
            invoices_issued_total=invoices["total"] or _ZERO,
            payments_succeeded_count=payments["count"] or 0,
            payments_succeeded_total=payments["total"] or _ZERO,
            wallet_total_balance=wallets["total"] or _ZERO,
            wallet_transaction_count=wallet_transactions["count"] or 0,
            wallet_transaction_total=wallet_transactions["total"] or _ZERO,
        )
