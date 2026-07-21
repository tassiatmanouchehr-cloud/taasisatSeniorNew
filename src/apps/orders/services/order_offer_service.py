"""
OrderOfferService -- Sprint 5.1: Submission Lifecycle Foundation.

The sole writer for OrderOffer state transitions (submit/edit/withdraw).
No other caller may construct or mutate OrderOffer rows directly.

Sprint 5.1 scope: submit_offer(), edit_offer(), withdraw_offer().
Future sprints: select, accept, expire, cancel.

Authorization model:
- submit_offer(): PermissionService.require() with orders.offer.submit,
  PLUS actor-to-supplier identity verification via the repository's
  canonical resolve_supplier_for_user() bridge -- the actor must own
  the supplier identity they are submitting for. A caller-provided
  supplier_id is never trusted as authorization.
- edit_offer(): ownership enforcement (submitted_by == actor)
- withdraw_offer(): ownership enforcement (submitted_by == actor)
All three enforce tenant isolation (offer.tenant == order.tenant).

Concurrency model (lock order: Order row first, then OrderOffer row):
- submit_offer(): locks the Order row before creating the offer
- edit_offer(): locks the Order row, then the OrderOffer row
- withdraw_offer(): locks the Order row, then the OrderOffer row
- UniqueConstraint(order, supplier) prevents duplicate submissions at DB level

Actor-to-supplier authorization rule:
  The actor's own ServiceSupplier (resolved via the canonical
  resolve_supplier_for_user() bridge, which verifies ACTIVE profile
  status and returns the unique supplier for that actor) must equal
  the supplier_id provided in the request. This prevents a permitted
  actor from submitting on behalf of another supplier in the same tenant.
"""

import uuid
from decimal import Decimal

from django.db import IntegrityError, transaction

from apps.accounts.services.provider_identity import resolve_supplier_for_user
from apps.kernel.models.supplier import ServiceSupplier
from apps.kernel.permissions.keys import ORDERS_OFFER_SUBMIT
from apps.kernel.services.audit_service import AuditService
from apps.kernel.services.permission_service import PermissionService

from ..models import Order, OrderOffer, OrderOfferStatus, OrderStatus

SOURCE_MODULE = "M05"

# The database constraint name used for one-offer-per-supplier detection.
_DUPLICATE_OFFER_CONSTRAINT = "uq_order_offer_one_per_supplier"


class OrderOfferError(Exception):
    """Domain error for all OrderOffer lifecycle violations."""


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

        Authorization:
        1. PermissionService.require() with orders.offer.submit
        2. Actor-to-supplier identity: the actor's own resolved supplier
           (via resolve_supplier_for_user) must match the supplier_id.
           This prevents submitting on behalf of another supplier.

        The Order must be in NEW status. One offer per (order, supplier)
        is enforced by a database UniqueConstraint.
        """
        if actor is None:
            raise OrderOfferError("An authenticated actor is required to submit an offer.")

        # Lock the order row -- serializes concurrent submissions
        order = cls._resolve_order(order_id=order_id, tenant_id=tenant_id)

        # Permission enforcement (RBAC)
        PermissionService.require(
            actor,
            ORDERS_OFFER_SUBMIT,
            tenant_id=tenant_id,
            ownership_authorized_by=actor,
        )

        # Actor-to-supplier identity verification
        supplier = cls._verify_actor_supplier_identity(actor=actor, supplier_id=supplier_id, tenant_id=tenant_id)

        # Validate order state
        if order.status != OrderStatus.NEW:
            raise OrderOfferError(
                f"Offers can only be submitted on orders in NEW status (current: {order.get_status_display()})."
            )

        # Validate price
        if price_amount is None or price_amount <= 0:
            raise OrderOfferError("price_amount must be a positive value.")

        # Create the offer
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
            if cls._is_duplicate_offer_violation(exc):
                raise OrderOfferError("This supplier already has an offer on this order.") from None
            raise

        # Audit (safe summary -- no free-form text in payload)
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

        Only the original submitter may edit. The offer must be in SUBMITTED
        status and the parent order must still be in NEW status.

        Lock order: Order row first, then OrderOffer row.
        """
        if actor is None:
            raise OrderOfferError("An authenticated actor is required to edit an offer.")

        # Lock order first (consistent lock ordering)
        offer = cls._resolve_offer_for_owner_with_order_lock(offer_id=offer_id, actor=actor, tenant_id=tenant_id)
        order = offer._locked_order  # attached by the helper

        # Validate offer state
        if not offer.can_edit:
            raise OrderOfferError(f"Offer cannot be edited in {offer.get_status_display()} status.")

        # Validate parent order state
        if order.status != OrderStatus.NEW:
            raise OrderOfferError("Offer cannot be edited because the order is no longer accepting offers.")

        # Determine which fields changed (for audit)
        changes = {}
        if price_amount is not None:
            if price_amount <= 0:
                raise OrderOfferError("price_amount must be a positive value.")
            if offer.price_amount != price_amount:
                changes["price_amount"] = {"before": str(offer.price_amount), "after": str(price_amount)}
                offer.price_amount = price_amount
        if estimated_duration_minutes is not ...:
            if offer.estimated_duration_minutes != estimated_duration_minutes:
                changes["estimated_duration_minutes"] = {
                    "before": offer.estimated_duration_minutes,
                    "after": estimated_duration_minutes,
                }
                offer.estimated_duration_minutes = estimated_duration_minutes
        if terms is not None and offer.terms != terms:
            changes["terms"] = True  # boolean: changed, no content
            offer.terms = terms
        if message is not None and offer.message != message:
            changes["message"] = True  # boolean: changed, no content
            offer.message = message

        if not changes:
            return offer  # no-op

        offer.save(update_fields=["price_amount", "estimated_duration_minutes", "terms", "message", "updated_at"])

        # Audit (safe summary -- field names and numeric values only)
        AuditService.log(
            tenant_id=tenant_id,
            action="orders.offer.edited",
            resource_type="OrderOffer",
            module_id=SOURCE_MODULE,
            resource_id=offer.id,
            actor_id=cls._actor_id(actor),
            actor_type="user",
            after={"changed_fields": list(changes.keys()), **{k: v for k, v in changes.items() if isinstance(v, dict)}},
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

        Only the original submitter may withdraw. The parent Order must still
        be in NEW status (cannot withdraw after the order has left the
        offer-accepting lifecycle). Transitions SUBMITTED -> WITHDRAWN (terminal).

        Lock order: Order row first, then OrderOffer row.
        """
        if actor is None:
            raise OrderOfferError("An authenticated actor is required to withdraw an offer.")

        # Lock order first (consistent lock ordering)
        offer = cls._resolve_offer_for_owner_with_order_lock(offer_id=offer_id, actor=actor, tenant_id=tenant_id)
        order = offer._locked_order

        # Validate offer state
        if not offer.can_withdraw:
            raise OrderOfferError(f"Offer cannot be withdrawn in {offer.get_status_display()} status.")

        # Validate parent order state
        if order.status != OrderStatus.NEW:
            raise OrderOfferError("Offer cannot be withdrawn because the order is no longer accepting offers.")

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
            after={"status": OrderOfferStatus.WITHDRAWN, "previous_status": OrderOfferStatus.SUBMITTED},
        )

        return offer

    # --- internal helpers --------------------------------------------------

    @classmethod
    def _verify_actor_supplier_identity(cls, *, actor, supplier_id: uuid.UUID, tenant_id: uuid.UUID) -> ServiceSupplier:
        """Verify the actor is authorized to act as the given supplier.

        Uses the repository's canonical resolve_supplier_for_user() bridge
        which resolves the actor's OWN supplier from their profile. The
        resolved supplier must match the requested supplier_id. This prevents
        a permitted actor from submitting on behalf of another supplier.

        Raises OrderOfferError if:
        - actor has no provider profile
        - actor's profile is not ACTIVE
        - actor's supplier does not match the requested supplier_id
        - resolved supplier is in a different tenant
        """
        from apps.accounts.services.errors import AccountsError

        try:
            actor_supplier = resolve_supplier_for_user(actor)
        except AccountsError:
            raise OrderOfferError("Actor is not authorized to submit offers (no active supplier identity).") from None

        if actor_supplier.id != supplier_id:
            raise OrderOfferError("Actor is not authorized to submit offers for this supplier.") from None

        if actor_supplier.tenant_id != tenant_id:
            raise OrderOfferError("Supplier not found.") from None

        return actor_supplier

    @classmethod
    def _resolve_order(cls, *, order_id: uuid.UUID, tenant_id: uuid.UUID) -> Order:
        """Lock and retrieve the order, enforcing tenant isolation."""
        try:
            return Order.objects.select_for_update().get(id=order_id, tenant_id=tenant_id)
        except Order.DoesNotExist:
            raise OrderOfferError("Order not found.") from None

    @classmethod
    def _resolve_offer_for_owner_with_order_lock(
        cls, *, offer_id: uuid.UUID, actor, tenant_id: uuid.UUID
    ) -> OrderOffer:
        """Lock the parent Order first, then the offer row.

        Consistent lock ordering (Order -> OrderOffer) across all mutations
        prevents deadlocks. The locked Order is attached as offer._locked_order
        for the caller to use without a second query.
        """
        # First resolve the offer without lock to get the order_id
        try:
            offer_peek = OrderOffer.objects.get(id=offer_id, tenant_id=tenant_id)
        except OrderOffer.DoesNotExist:
            raise OrderOfferError("Offer not found.") from None

        # Ownership check (before acquiring locks)
        if offer_peek.submitted_by_id is None or offer_peek.submitted_by_id != actor.id:
            raise OrderOfferError("Only the original submitter may modify this offer.")

        # Lock order first (consistent ordering)
        order = Order.objects.select_for_update().get(id=offer_peek.order_id)

        # Lock the offer row
        offer = OrderOffer.objects.select_for_update().get(id=offer_id)

        # Re-verify ownership under lock (could have changed concurrently)
        if offer.submitted_by_id != actor.id:
            raise OrderOfferError("Only the original submitter may modify this offer.")

        # Attach locked order for caller
        offer._locked_order = order
        return offer

    @classmethod
    def _is_duplicate_offer_violation(cls, exc: IntegrityError) -> bool:
        """Detect the duplicate-offer UniqueConstraint violation.

        Checks both the constraint name (PostgreSQL) and the field names
        (SQLite fallback) to support the repository's test/development stacks.
        Does not swallow unrelated IntegrityError cases.
        """
        exc_str = str(exc)
        if _DUPLICATE_OFFER_CONSTRAINT in exc_str:
            return True
        # SQLite fallback: reports field names rather than constraint names
        if "order" in exc_str and "supplier" in exc_str and "UNIQUE" in exc_str.upper():
            return True
        return False

    @staticmethod
    def _actor_id(actor) -> uuid.UUID | None:
        """Extract the person_id from a UserAccount for audit attribution."""
        return getattr(actor, "person_id", None)
