"""
CustomerDashboardPresentationService — Epic 07 (Customer Experience and
Portal Completion).

Wraps the exact same domain-service calls dashboard_view already made
(OrderQueryService, CareRecipientService, FinancialPartyService,
WalletService, NotificationQueryService — none of this Epic's doing,
all pre-existing) into an immutable CustomerDashboardViewModel, mirroring
Epic 07 Part G's "keep top-level ViewModels role-specific" requirement.
Performs no query of its own beyond what the view already resolved —
this is presentation assembly only.
"""

from apps.notifications.models import NotificationStatus
from apps.orders.models import OrderStatus

from .profile_service import CustomerProfilePresentationService
from .viewmodels import (
    CareRecipientSummaryViewModel,
    CustomerDashboardViewModel,
    NotificationRowViewModel,
    OrderRowViewModel,
)

_ORDER_STATUS_VARIANTS = {
    OrderStatus.COMPLETED: "success",
    OrderStatus.CANCELLED: "danger",
    OrderStatus.IN_PROGRESS: "primary",
    OrderStatus.WAITING_SERVICE: "warning",
    OrderStatus.NEW: "neutral",
    OrderStatus.PENDING_OPERATOR_REVIEW: "neutral",
    OrderStatus.CANCELLATION_REQUESTED: "warning",
}


class CustomerDashboardPresentationService:
    """Read-only: assembles the customer dashboard ViewModel from
    already-fetched domain objects."""

    @classmethod
    def build(
        cls,
        *,
        customer,
        recent_orders,
        upcoming_visits,
        care_recipients,
        wallet,
        recent_notifications,
        unread_notification_count,
    ):
        completion_percent, missing = CustomerProfilePresentationService.compute_completion(customer)

        pending_actions = []
        if not care_recipients:
            pending_actions.append("افزودن اولین گیرنده خدمت")
        if missing:
            pending_actions.append("تکمیل اطلاعات پروفایل")

        return CustomerDashboardViewModel(
            customer_display_name=customer.display_name,
            recent_orders=tuple(cls._order_row(order) for order in recent_orders),
            upcoming_visits=tuple(cls._order_row(order) for order in upcoming_visits),
            care_recipients=tuple(
                CareRecipientSummaryViewModel(
                    id=str(cr.id),
                    full_name=cr.full_name,
                    is_primary=cr.is_primary,
                    detail_url=f"/portal/care-recipients/{cr.id}/",
                )
                for cr in care_recipients
            ),
            wallet_balance_label=f"{wallet.balance:,.0f}" if wallet else "—",
            wallet_currency=wallet.currency if wallet else "",
            has_wallet=wallet is not None,
            recent_notifications=tuple(
                NotificationRowViewModel(
                    channel_label=n.get_channel_display(),
                    created_at_label=n.created_at.strftime("%Y/%m/%d %H:%M"),
                    is_read=n.status != NotificationStatus.PENDING,
                )
                for n in recent_notifications
            ),
            unread_notification_count=unread_notification_count,
            profile_completion_percent=completion_percent,
            pending_actions=tuple(pending_actions),
        )

    @staticmethod
    def _order_row(order) -> OrderRowViewModel:
        return OrderRowViewModel(
            order_id=str(order.id),
            order_number=order.order_number,
            service_category_name=order.service_category.name if order.service_category_id else "",
            status_label=order.get_status_display(),
            status_variant=_ORDER_STATUS_VARIANTS.get(order.status, "neutral"),
            created_at_label=order.created_at.strftime("%Y/%m/%d"),
            scheduled_for_label=order.scheduled_for.strftime("%Y/%m/%d %H:%M") if order.scheduled_for else "",
            detail_url=f"/portal/requests/{order.id}/",
        )
