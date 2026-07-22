"""
OrderOfferService -- Sprint 5.1 + 5.2: Submission Lifecycle + Selection/Expiration.

The sole writer for OrderOffer state transitions.
No other caller may construct or mutate OrderOffer rows directly.

Sprint 5.1 scope: submit_offer(), edit_offer(), withdraw_offer().
Sprint 5.2 scope: select_offer(), expire_held_offers().
Future sprints: accept, cancel.

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
from datetime import timedelta
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.services.provider_identity import resolve_supplier_for_user
from apps.kernel.models.supplier import ServiceSupplier
from apps.kernel.permissions.keys import ORDERS_OFFER_SUBMIT
from apps.kernel.services.audit_service import AuditService
from apps.kernel.services.permission_service import PermissionService

from ..models import Order, OrderOffer, OrderOfferStatus, OrderStatus

SOURCE_MODULE = "M05"

# The database constraint name used for one-offer-per-supplier detection.
_DUPLICATE_OFFER_CONSTRAINT = "uq_order_offer_one_per_supplier"

# The database constraint name for one-selected-per-order detection.
_ONE_SELECTED_CONSTRAINT = "uq_order_offer_one_selected_per_order"

# Hold duration for a selected offer. 30 minutes per the approved state
# machine design. Not currently tenant-configurable — documented known
# limitation (Sprint 5.2).
SELECTION_HOLD_DURATION = timedelta(minutes=30)


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

    # --- Sprint 5.2: Selection and Hold Expiration -------------------------

    @classmethod
    @transaction.atomic
    def select_offer(
        cls,
        *,
        offer_id: uuid.UUID,
        actor,
        tenant_id: uuid.UUID,
    ) -> OrderOffer:
        """Select an offer for a time-limited hold (30 minutes).

        Only the order owner (customer) may select. The offer must be SUBMITTED
        and the parent order must be in NEW status. All other SUBMITTED offers
        for the same order are bulk-rejected (terminal, irreversible).

        Authorization: order ownership (order.customer_profile.user == actor
        OR order.created_by == actor). No RBAC permission key — ownership is
        the boundary, consistent with edit_offer/withdraw_offer's pattern.

        Lock order: Order row first, then target offer row.
        DB invariant: uq_order_offer_one_selected_per_order ensures at most
        one SELECTED offer per order. IntegrityError caught as race backstop.

        Idempotency: selecting an already-SELECTED offer (same offer, same
        actor) is an error — the caller must check state before retrying.
        """
        if actor is None:
            raise OrderOfferError("An authenticated actor is required to select an offer.")

        # Resolve offer (peek without lock to get order_id and tenant check)
        try:
            offer_peek = OrderOffer.objects.get(id=offer_id, tenant_id=tenant_id)
        except OrderOffer.DoesNotExist:
            raise OrderOfferError("Offer not found.") from None

        # Lock the parent order first (consistent lock ordering)
        try:
            order = Order.objects.select_for_update().get(
                id=offer_peek.order_id, tenant_id=tenant_id
            )
        except Order.DoesNotExist:
            raise OrderOfferError("Order not found.") from None

        # Authorization: order ownership check
        cls._verify_order_ownership(order=order, actor=actor)

        # Validate order state
        if order.status != OrderStatus.NEW:
            raise OrderOfferError(
                "Offers can only be selected on orders in NEW status "
                f"(current: {order.get_status_display()})."
            )

        # Lock the target offer row
        offer = OrderOffer.objects.select_for_update().get(id=offer_id)

        # Validate offer state
        if not offer.can_select:
            raise OrderOfferError(
                f"Offer cannot be selected in {offer.get_status_display()} status."
            )

        # Transition target offer to SELECTED
        now = timezone.now()
        offer.status = OrderOfferStatus.SELECTED
        offer.selected_by = actor
        offer.selected_at = now
        offer.hold_expires_at = now + SELECTION_HOLD_DURATION

        try:
            offer.save(update_fields=[
                "status", "selected_by", "selected_at", "hold_expires_at", "updated_at",
            ])
        except IntegrityError as exc:
            if _ONE_SELECTED_CONSTRAINT in str(exc) or (
                "order" in str(exc).lower() and "selected" in str(exc).lower()
            ):
                raise OrderOfferError(
                    "Another offer has already been selected for this order."
                ) from None
            raise

        # Bulk-reject all other SUBMITTED offers for this order
        competing = (
            OrderOffer.objects
            .select_for_update()
            .filter(order=order, status=OrderOfferStatus.SUBMITTED)
            .exclude(id=offer.id)
        )
        rejected_ids = list(competing.values_list("id", flat=True))
        if rejected_ids:
            competing.update(status=OrderOfferStatus.REJECTED, updated_at=now)

        # Audit — selection
        AuditService.log(
            tenant_id=tenant_id,
            action="orders.offer.selected",
            resource_type="OrderOffer",
            module_id=SOURCE_MODULE,
            resource_id=offer.id,
            actor_id=cls._actor_id(actor),
            actor_type="user",
            after={
                "order_id": str(order.id),
                "supplier_id": str(offer.supplier_id),
                "status": OrderOfferStatus.SELECTED,
                "hold_expires_at": offer.hold_expires_at.isoformat(),
                "rejected_offer_count": len(rejected_ids),
            },
        )

        # Audit — per rejected offer (batch — one entry summarizing all)
        if rejected_ids:
            AuditService.log(
                tenant_id=tenant_id,
                action="orders.offer.rejected",
                resource_type="OrderOffer",
                module_id=SOURCE_MODULE,
                resource_id=order.id,
                actor_id=cls._actor_id(actor),
                actor_type="user",
                after={
                    "order_id": str(order.id),
                    "rejected_offer_ids": [str(rid) for rid in rejected_ids],
                    "reason": "competing_offer_selection",
                },
            )

        return offer

    @classmethod
    def expire_held_offers(
        cls,
        *,
        tenant_id: uuid.UUID | None = None,
        now: "timezone.datetime | None" = None,
        batch_size: int = 100,
    ) -> list[uuid.UUID]:
        """Expire SELECTED offers whose hold has timed out.

        This method is independently callable by any future scheduler
        (management command, Celery task, cron). It is:
        - idempotent (re-running with no time change is a no-op),
        - safe for concurrent execution (skip_locked),
        - bounded by batch_size.

        Args:
            tenant_id: If provided, scope to this tenant only. If None, process all.
            now: Injection point for testability. Defaults to timezone.now().
            batch_size: Maximum offers to process per invocation.

        Returns:
            List of offer IDs that were expired.
        """
        if now is None:
            now = timezone.now()

        # Build the queryset for expired holds
        qs = OrderOffer.objects.filter(
            status=OrderOfferStatus.SELECTED,
            hold_expires_at__isnull=False,
            hold_expires_at__lte=now,
        )
        if tenant_id is not None:
            qs = qs.filter(tenant_id=tenant_id)

        # Limit batch size
        qs = qs[:batch_size]

        expired_ids = []

        for offer_id in qs.values_list("id", flat=True):
            expired = cls._expire_single_offer(offer_id=offer_id, now=now)
            if expired:
                expired_ids.append(offer_id)

        return expired_ids

    @classmethod
    @transaction.atomic
    def _expire_single_offer(cls, *, offer_id: uuid.UUID, now) -> bool:
        """Expire a single offer under row lock. Returns True if expired."""
        try:
            offer = (
                OrderOffer.objects
                .select_for_update(skip_locked=True)
                .get(id=offer_id, status=OrderOfferStatus.SELECTED)
            )
        except OrderOffer.DoesNotExist:
            # Already transitioned (accepted, cancelled, or processed by another worker)
            return False

        # Re-verify expiry under lock
        if offer.hold_expires_at is None or offer.hold_expires_at > now:
            return False

        offer.status = OrderOfferStatus.EXPIRED
        offer.save(update_fields=["status", "updated_at"])

        AuditService.log(
            tenant_id=offer.tenant_id,
            action="orders.offer.expired",
            resource_type="OrderOffer",
            module_id=SOURCE_MODULE,
            resource_id=offer.id,
            actor_id=None,
            actor_type="system",
            after={
                "order_id": str(offer.order_id),
                "status": OrderOfferStatus.EXPIRED,
                "hold_expires_at": offer.hold_expires_at.isoformat(),
            },
        )

        return True

    # --- internal helpers --------------------------------------------------

    @classmethod
    def _verify_order_ownership(cls, *, order: Order, actor) -> None:
        """Verify the actor owns (or is authorized for) the parent order.

        Uses the same customer-ownership pattern as the portal layer:
        the actor must be either the customer_profile's user or the
        order's created_by user.
        """
        is_owner = False
        if order.customer_profile_id and hasattr(actor, "person"):
            # Check if actor's person owns the customer_profile
            from apps.accounts.models.profiles import CustomerProfile
            try:
                cp = CustomerProfile.objects.get(id=order.customer_profile_id)
                if cp.person_id == actor.person_id:
                    is_owner = True
            except CustomerProfile.DoesNotExist:
                pass
        if not is_owner and order.created_by_id == actor.id:
            is_owner = True
        if not is_owner:
            raise OrderOfferError("Only the order owner may select an offer.")

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
