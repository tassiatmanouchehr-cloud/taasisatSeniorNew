"""
OrderOfferService — Sprint 5.1: Submission Lifecycle Foundation.

The sole writer for OrderOffer state transitions (submit/edit/withdraw).
No other caller may construct or mutate OrderOffer rows directly — every
submission, edit, and withdrawal goes through this service.

Sprint 5.1 scope: submit_offer(), edit_offer(), withdraw_offer().
Future sprints: select, accept, expire, cancel (see architecture assessment
project docs/assessments/2026-07-21_MARKETPLACE_ORDER_WORKFLOW_ARCHITECTURE_ASSESSMENT.md).

Authorization model:
- submit_offer(): PermissionService.require() with orders.offer.submit
- edit_offer(): ownership enforcement (submitted_by == actor)
- withdraw_offer(): ownership enforcement (submitted_by == actor)
All three enforce tenant isolation (offer.tenant == order.tenant == supplier.tenant).

Concurrency model:
- submit_offer(): locks the Order row before creating the offer
- edit_offer(): locks the OrderOffer row before mutating
- withdraw_offer(): locks the OrderOffer row before transitioning
- UniqueConstraint(order, supplier) prevents duplicate submissions at DB level
"""

import uuid
from decimal import Decimal

from django.db import IntegrityError, transaction

from apps.kernel.models.supplier import ServiceSupplier, SupplierStatus
from apps.kernel.permissions.keys import ORDERS_OFFER_SUBMIT
from apps.kernel.services.audit_service import AuditService
from apps.kernel.services.permission_service import PermissionService

from ..models import Order, OrderOffer, OrderOfferStatus, OrderStatus

SOURCE_MODULE = "M05"


class OrderOfferError(Exception):
    """Domain error for all OrderOffer lifecycle violations."""

    pass


class OrderOfferService:
    """Sole writer for OrderOffer lifecycle transitions (Sprint 5.1: submission lifecycle)."""

    # --- public API --------------------------------------------------------

    @classmethod
    @transaction.atomic
    def submit_offer(
        cls,
        *,
        order_id: uuid.UUID,
        supplier_id: uuid.UUID,
        actor,
        tenant_id: uuid.UUID,
        price_amount: Decimal,
        currency: str = "IRR",
        estimated_duration_minutes: int | None = None,
        terms: str = "",
        message: str = "",
    ) -> OrderOffer:
        """Submit a new commercial offer on an order.

        Requires permission: orders.offer.submit (enforced via PermissionService).
        The Order must be in NEW status. The supplier must be ACTIVE and in the
        same tenant as the order. One offer per (order, supplier) is enforced by
        a database UniqueConstraint — a duplicate submission raises OrderOfferError.
        """
        if actor is None:
            raise OrderOfferError("An authenticated actor is required to submit an offer.")

        # Lock the order row — serializes concurrent submissions for the same order
        order = cls._resolve_order(order_id=order_id, tenant_id=tenant_id)

        # Permission enforcement
        PermissionService.require(
            actor,
            ORDERS_OFFER_SUBMIT,
            tenant_id=tenant_id,
            ownership_authorized_by=actor,
        )

        # Validate order state
        if order.status != OrderStatus.NEW:
            raise OrderOfferError(
                f"Offers can only be submitted on orders in NEW status (current: {order.get_status_display()})."
            )

        # Validate supplier
        supplier = cls._resolve_supplier(supplier_id=supplier_id, tenant_id=tenant_id)

        # Validate price
        if price_amount is None or price_amount <= 0:
            raise OrderOfferError("price_amount must be a positive value.")

        # Create the offer — UniqueConstraint handles duplicate prevention
        try:
            offer = OrderOffer.objects.create(
                tenant_id=tenant_id,
                order=order,
                supplier=supplier,
                price_amount=price_amount,
                currency=currency,
                estimated_duration_minutes=estimated_duration_minutes,
                terms=terms,
                message=message,
                status=OrderOfferStatus.SUBMITTED,
                submitted_by=actor,
            )
        except IntegrityError as exc:
            if "uq_order_offer_one_per_supplier" in str(exc):
                raise OrderOfferError("This supplier already has an offer on this order.") from None
            raise

        # Audit
        AuditService.log(
            tenant_id=tenant_id,
            action="orders.offer.submitted",
            resource_type="OrderOffer",
            module_id=SOURCE_MODULE,
            resource_id=offer.id,
            actor_id=cls._actor_id(actor),
            actor_type="user",
            after={
                "order_id": str(order.id),
                "supplier_id": str(supplier.id),
                "price_amount": str(offer.price_amount),
                "currency": offer.currency,
                "status": offer.status,
            },
        )

        return offer

    @classmethod
    @transaction.atomic
    def edit_offer(
        cls,
        *,
        offer_id: uuid.UUID,
        actor,
        tenant_id: uuid.UUID,
        price_amount: Decimal | None = None,
        estimated_duration_minutes: int | None = ...,  # sentinel: ... means "not provided"
        terms: str | None = None,
        message: str | None = None,
    ) -> OrderOffer:
        """Edit a SUBMITTED offer's mutable fields.

        Only the original submitter may edit. The offer must be in SUBMITTED status
        and the parent order must still be in NEW status.
        """
        if actor is None:
            raise OrderOfferError("An authenticated actor is required to edit an offer.")

        offer = cls._resolve_offer_for_owner(offer_id=offer_id, actor=actor, tenant_id=tenant_id)

        # Validate offer state
        if not offer.can_edit:
            raise OrderOfferError(f"Offer cannot be edited in {offer.get_status_display()} status.")

        # Validate parent order state
        order = Order.objects.select_for_update().get(id=offer.order_id)
        if order.status != OrderStatus.NEW:
            raise OrderOfferError("Offer cannot be edited because the order is no longer accepting offers.")

        # Capture before state for audit
        before = {
            "price_amount": str(offer.price_amount),
            "estimated_duration_minutes": offer.estimated_duration_minutes,
            "terms": offer.terms,
            "message": offer.message,
        }

        # Apply allowed field changes
        changed = False
        if price_amount is not None:
            if price_amount <= 0:
                raise OrderOfferError("price_amount must be a positive value.")
            offer.price_amount = price_amount
            changed = True
        if estimated_duration_minutes is not ...:
            offer.estimated_duration_minutes = estimated_duration_minutes
            changed = True
        if terms is not None:
            offer.terms = terms
            changed = True
        if message is not None:
            offer.message = message
            changed = True

        if not changed:
            return offer  # no-op

        offer.save(update_fields=["price_amount", "estimated_duration_minutes", "terms", "message", "updated_at"])

        # Audit
        after = {
            "price_amount": str(offer.price_amount),
            "estimated_duration_minutes": offer.estimated_duration_minutes,
            "terms": offer.terms,
            "message": offer.message,
        }
        AuditService.log(
            tenant_id=tenant_id,
            action="orders.offer.edited",
            resource_type="OrderOffer",
            module_id=SOURCE_MODULE,
            resource_id=offer.id,
            actor_id=cls._actor_id(actor),
            actor_type="user",
            before=before,
            after=after,
        )

        return offer

    @classmethod
    @transaction.atomic
    def withdraw_offer(
        cls,
        *,
        offer_id: uuid.UUID,
        actor,
        tenant_id: uuid.UUID,
    ) -> OrderOffer:
        """Withdraw a SUBMITTED offer.

        Only the original submitter may withdraw. The offer transitions
        SUBMITTED -> WITHDRAWN. This is a terminal transition.
        """
        if actor is None:
            raise OrderOfferError("An authenticated actor is required to withdraw an offer.")

        offer = cls._resolve_offer_for_owner(offer_id=offer_id, actor=actor, tenant_id=tenant_id)

        # Validate offer state
        if not offer.can_withdraw:
            raise OrderOfferError(f"Offer cannot be withdrawn in {offer.get_status_display()} status.")

        # Transition
        offer.status = OrderOfferStatus.WITHDRAWN
        offer.save(update_fields=["status", "updated_at"])

        # Audit
        AuditService.log(
            tenant_id=tenant_id,
            action="orders.offer.withdrawn",
            resource_type="OrderOffer",
            module_id=SOURCE_MODULE,
            resource_id=offer.id,
            actor_id=cls._actor_id(actor),
            actor_type="user",
            before={"status": OrderOfferStatus.SUBMITTED},
            after={"status": OrderOfferStatus.WITHDRAWN},
        )

        return offer

    # --- internal helpers --------------------------------------------------

    @classmethod
    def _resolve_order(cls, *, order_id: uuid.UUID, tenant_id: uuid.UUID) -> Order:
        """Lock and retrieve the order, enforcing tenant isolation."""
        try:
            return Order.objects.select_for_update().get(id=order_id, tenant_id=tenant_id)
        except Order.DoesNotExist:
            raise OrderOfferError("Order not found.") from None

    @classmethod
    def _resolve_supplier(cls, *, supplier_id: uuid.UUID, tenant_id: uuid.UUID) -> ServiceSupplier:
        """Retrieve and validate the supplier is ACTIVE in the same tenant."""
        try:
            supplier = ServiceSupplier.objects.get(id=supplier_id, tenant_id=tenant_id)
        except ServiceSupplier.DoesNotExist:
            raise OrderOfferError("Supplier not found in this tenant.") from None

        if supplier.status != SupplierStatus.ACTIVE:
            raise OrderOfferError("Supplier must be ACTIVE to submit an offer.")

        return supplier

    @classmethod
    def _resolve_offer_for_owner(cls, *, offer_id: uuid.UUID, actor, tenant_id: uuid.UUID) -> OrderOffer:
        """Lock and retrieve the offer, enforcing tenant isolation and ownership."""
        try:
            offer = OrderOffer.objects.select_for_update().get(id=offer_id, tenant_id=tenant_id)
        except OrderOffer.DoesNotExist:
            raise OrderOfferError("Offer not found.") from None

        # Ownership check
        if offer.submitted_by_id is None or offer.submitted_by_id != actor.id:
            raise OrderOfferError("Only the original submitter may modify this offer.")

        return offer

    @staticmethod
    def _actor_id(actor) -> uuid.UUID | None:
        """Extract the person_id from a UserAccount for audit attribution."""
        return getattr(actor, "person_id", None)
