"""
CaregiverDashboardPresentationService — Sprint 2.5 (Caregiver Professional
Dashboard).

build() mirrors apps.portal.services.dashboard_service
.CustomerDashboardPresentationService's own, pre-existing shape exactly:
wraps already-fetched domain objects into an immutable ViewModel, performing
no query of its own — pure presentation assembly, never a new financial/
order calculation.

build_for_supplier() is the one entry point apps/provider_portal/views.py
calls — it resolves every section's data via its own canonical,
already-existing selector (apps.orders.services.queries.OrderQueryService,
apps.finance.services.document_service.FinancialDocumentService,
apps.wallet.services.{wallet_service,wallet_transaction_service},
apps.reviews.services.reputation_service.ReputationService,
apps.accounts.services.public_credential_selector.PublicCredentialSelector),
then calls build(). Kept here rather than in views.py so that file stays
entirely free of direct model/ORM access, matching its own module
docstring's "no ORM access of any kind" rule — views.py passes only an
already-resolved supplier/tenant_id/caregiver (never accepted from the
request; resolved by _guard_with_caregiver()).

Bonus/penalty (Section E): no canonical bonus/penalty representation exists
anywhere in this repository (confirmed by inspection — apps.wallet's own
WalletTransactionType has CREDIT/DEBIT/REFUND/PROMOTION/ADJUSTMENT/MANUAL,
none of them semantically "bonus" or "penalty", and no dedicated
adjustment/bonus model exists in apps.commission or elsewhere). Per this
sprint's own governance ("if no canonical representation exists, do not
invent one"), no bonus/penalty section was built — recent wallet movements
already show every CREDIT/DEBIT/ADJUSTMENT regardless of category, and
FinancialOverviewViewModel.bonus_penalty_note documents this gap explicitly
rather than presenting an invented classification as fact. See
traceability/ARCHITECTURE_DECISION_LOG.md ADM-021.
"""

from apps.accounts.services.public_credential_selector import PublicCredentialSelector
from apps.finance.services.document_service import FinancialDocumentService
from apps.finance.services.party_service import FinancialPartyService
from apps.orders.services.queries import OrderQueryService
from apps.reviews.services.reputation_service import ReputationService
from apps.wallet.services.wallet_service import WalletService
from apps.wallet.services.wallet_transaction_service import WalletTransactionService

from .viewmodels import (
    CaregiverDashboardViewModel,
    DashboardOrderRowViewModel,
    DashboardReviewRowViewModel,
    FinancialOverviewViewModel,
    InvoiceRowViewModel,
    InvoiceSummaryViewModel,
    ProfessionalStatisticsViewModel,
    ReputationOverviewViewModel,
    WalletMovementRowViewModel,
    WorkSummaryViewModel,
)

BONUS_PENALTY_NOT_MODELED_NOTE = (
    "پاداش و جریمه به صورت دسته‌بندی جداگانه در پلتفرم ثبت نمی‌شود — تراکنش‌های کیف پول بالا شامل تمام واریز/برداشت‌ها است."
)

RECENT_ITEMS_LIMIT = 5
RECENT_MOVEMENTS_LIMIT = 10
RECENT_INVOICES_LIMIT = 5
RECENT_REVIEWS_LIMIT = 5


class CaregiverDashboardPresentationService:
    """Read-only: assembles the Sprint 2.5 dashboard sections from
    already-fetched domain objects."""

    @classmethod
    def build_for_supplier(
        cls, *, supplier, tenant_id, caregiver, reputation, performance
    ) -> CaregiverDashboardViewModel:
        """Resolves every section's data via its own canonical,
        already-existing selector — no query invented here that a domain
        service doesn't already own — then hands the raw data to build().
        Kept here (not in provider_portal/views.py) so that file stays
        entirely free of direct model/ORM access, per its own
        "no ORM access of any kind" rule."""
        work_counts = OrderQueryService.count_by_status_for_supplier(supplier=supplier, tenant_id=tenant_id)
        current_orders = list(
            OrderQueryService.list_for_supplier(
                supplier=supplier,
                tenant_id=tenant_id,
                only="current",
                limit=RECENT_ITEMS_LIMIT,
            ),
        )
        upcoming_orders = list(
            OrderQueryService.list_for_supplier(
                supplier=supplier,
                tenant_id=tenant_id,
                only="upcoming",
                limit=RECENT_ITEMS_LIMIT,
            ),
        )
        recent_completed_orders = list(
            OrderQueryService.list_for_supplier(
                supplier=supplier,
                tenant_id=tenant_id,
                only="completed",
                limit=RECENT_ITEMS_LIMIT,
            ),
        )

        party = FinancialPartyService.resolve_party_for_supplier(supplier)
        wallet = WalletService.get_wallet_or_none(party=party)
        recent_wallet_transactions = (
            list(WalletTransactionService.list_transactions(wallet)[:RECENT_MOVEMENTS_LIMIT]) if wallet else []
        )

        invoice_counts = FinancialDocumentService.count_by_status_for_beneficiary_party(
            tenant_id=tenant_id,
            party_id=party.id,
        )
        recent_invoices = list(
            FinancialDocumentService.list_for_beneficiary_party(
                tenant_id=tenant_id,
                party_id=party.id,
                limit=RECENT_INVOICES_LIMIT,
            ),
        )

        recent_reviews = ReputationService.list_recent_reviews_with_reviewer_names(
            supplier,
            limit=RECENT_REVIEWS_LIMIT,
        )

        credentials = PublicCredentialSelector.for_caregiver(caregiver)

        return cls.build(
            work_counts=work_counts,
            current_orders=current_orders,
            upcoming_orders=upcoming_orders,
            recent_completed_orders=recent_completed_orders,
            wallet=wallet,
            recent_wallet_transactions=recent_wallet_transactions,
            invoice_counts=invoice_counts,
            recent_invoices=recent_invoices,
            reputation_summary=reputation,
            recent_reviews=recent_reviews,
            performance=performance,
            verified_credential_count=len(credentials),
            visible_skill_count=caregiver.skills.filter(is_visible=True).count(),
            visible_gallery_item_count=caregiver.gallery_items.filter(is_visible=True).count(),
        )

    @classmethod
    def build(
        cls,
        *,
        work_counts,
        current_orders,
        upcoming_orders,
        recent_completed_orders,
        wallet,
        recent_wallet_transactions,
        invoice_counts,
        recent_invoices,
        reputation_summary,
        recent_reviews,
        performance,
        verified_credential_count,
        visible_skill_count,
        visible_gallery_item_count,
    ) -> CaregiverDashboardViewModel:
        return CaregiverDashboardViewModel(
            work_summary=cls._work_summary(
                work_counts,
                current_orders,
                upcoming_orders,
                recent_completed_orders,
            ),
            financial_overview=cls._financial_overview(wallet, recent_wallet_transactions),
            invoice_summary=cls._invoice_summary(invoice_counts, recent_invoices),
            reputation=cls._reputation_overview(reputation_summary, recent_reviews),
            statistics=cls._statistics(
                performance=performance,
                cancelled_orders=work_counts.get("cancelled", 0),
                average_rating=reputation_summary.get("average_score"),
                verified_credential_count=verified_credential_count,
                visible_skill_count=visible_skill_count,
                visible_gallery_item_count=visible_gallery_item_count,
            ),
        )

    # ------------------------------------------------------------------

    @classmethod
    def _work_summary(cls, counts, current_orders, upcoming_orders, recent_completed_orders) -> WorkSummaryViewModel:
        return WorkSummaryViewModel(
            current_count=counts.get("current", 0),
            upcoming_count=counts.get("upcoming", 0),
            completed_count=counts.get("completed", 0),
            cancelled_count=counts.get("cancelled", 0),
            current_items=tuple(cls._order_row(o) for o in current_orders[:RECENT_ITEMS_LIMIT]),
            upcoming_items=tuple(cls._order_row(o) for o in upcoming_orders[:RECENT_ITEMS_LIMIT]),
            recent_completed_items=tuple(cls._order_row(o) for o in recent_completed_orders[:RECENT_ITEMS_LIMIT]),
        )

    @staticmethod
    def _order_row(order) -> DashboardOrderRowViewModel:
        return DashboardOrderRowViewModel(
            order_id=str(order.id),
            order_number=order.order_number,
            service_category_name=order.service_category.name if order.service_category_id else "",
            status_label=order.get_status_display(),
            scheduled_for_label=order.scheduled_for.strftime("%Y/%m/%d %H:%M") if order.scheduled_for else "",
            detail_url=f"/provider/assignments/{order.id}/",
        )

    @classmethod
    def _financial_overview(cls, wallet, recent_transactions) -> FinancialOverviewViewModel:
        return FinancialOverviewViewModel(
            has_wallet=wallet is not None,
            available_balance_label=f"{wallet.balance:,.0f}" if wallet else "—",
            currency=wallet.currency if wallet else "",
            recent_movements=tuple(cls._movement_row(t) for t in recent_transactions[:RECENT_MOVEMENTS_LIMIT]),
            bonus_penalty_note=BONUS_PENALTY_NOT_MODELED_NOTE,
        )

    @staticmethod
    def _movement_row(transaction) -> WalletMovementRowViewModel:
        return WalletMovementRowViewModel(
            transaction_type_label=transaction.get_transaction_type_display(),
            amount_label=f"{transaction.amount:,.0f}",
            reason=transaction.reason,
            created_at_label=transaction.created_at.strftime("%Y/%m/%d %H:%M"),
        )

    @classmethod
    def _invoice_summary(cls, counts_by_status, recent_invoices) -> InvoiceSummaryViewModel:
        return InvoiceSummaryViewModel(
            counts_by_status=counts_by_status,
            recent_invoices=tuple(cls._invoice_row(d) for d in recent_invoices[:RECENT_INVOICES_LIMIT]),
        )

    @staticmethod
    def _invoice_row(document) -> InvoiceRowViewModel:
        return InvoiceRowViewModel(
            document_type_label=document.get_document_type_display(),
            status_label=document.get_status_display(),
            total_amount_label=f"{document.total_amount:,.0f}",
            created_at_label=document.created_at.strftime("%Y/%m/%d"),
            order_number=document.order.order_number if document.order_id else "",
        )

    @classmethod
    def _reputation_overview(cls, summary, recent_reviews) -> ReputationOverviewViewModel:
        return ReputationOverviewViewModel(
            average_score=summary.get("average_score"),
            review_count=summary.get("review_count", 0),
            recent_reviews=tuple(cls._review_row(r) for r in recent_reviews[:RECENT_REVIEWS_LIMIT]),
        )

    @staticmethod
    def _review_row(row) -> DashboardReviewRowViewModel:
        """`row` is the (review, reviewer_name) pair
        ReputationService.list_recent_reviews_with_reviewer_names()
        already resolved."""
        review, reviewer_name = row
        return DashboardReviewRowViewModel(
            reviewer_name=reviewer_name,
            rating=review.overall_rating,
            rating_stars_rounded=max(0, min(5, int(round(review.overall_rating)))),
            written_text=review.written_text,
            created_at_label=review.created_at.strftime("%Y/%m/%d"),
        )

    @staticmethod
    def _statistics(
        *,
        performance,
        cancelled_orders,
        average_rating,
        verified_credential_count,
        visible_skill_count,
        visible_gallery_item_count,
    ) -> ProfessionalStatisticsViewModel:
        return ProfessionalStatisticsViewModel(
            completed_jobs=performance.completed_services,
            active_assignments=performance.active_assignments,
            cancelled_orders=cancelled_orders,
            average_rating=average_rating,
            verified_credential_count=verified_credential_count,
            visible_skill_count=visible_skill_count,
            visible_gallery_item_count=visible_gallery_item_count,
        )
