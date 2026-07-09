"""
OrderShareLinkService — Customer Experience Phase 1.

Generates and resolves read-only, time-limited, revocable share links for
a single order. A share-link viewer never authenticates as any
UserAccount — the token itself is the only credential, scoped to exactly
one order, and grants nothing beyond viewing it.

Every lifecycle transition (create/revoke/access) publishes a DomainEvent
via apps.kernel.events.publish, mirroring the same pattern
apps.orders.services.order_creation already uses for ORDER_CREATED: the
event is scheduled with transaction.on_commit() so it only fires once the
write actually commits, and publish() itself unconditionally writes an
AuditLog row (apps.kernel.events.publisher.publish), so every share-link
create/revoke/access is now audited even though no notification handler
is registered for these event types yet.
"""

from django.db import transaction
from django.utils import timezone

from apps.kernel.events.base import SHARE_LINK_ACCESSED, SHARE_LINK_CREATED, SHARE_LINK_REVOKED, DomainEvent
from apps.kernel.events.publisher import publish as publish_domain_event

DEFAULT_VALIDITY = timezone.timedelta(days=14)


class OrderShareLinkError(Exception):
    pass


def _actor_id(user):
    """Mirrors apps.orders.services.order_creation._actor_id: a UserAccount's
    Person id, or None for an anonymous/system-initiated action."""
    return getattr(user, "person_id", None)


class OrderShareLinkService:
    """Creates, resolves, and revokes OrderShareLink rows."""

    @classmethod
    @transaction.atomic
    def create(cls, *, order, created_by=None, valid_for=None):
        from ..models import OrderShareLink

        expires_at = timezone.now() + (valid_for or DEFAULT_VALIDITY)
        link = OrderShareLink.objects.create(
            tenant_id=order.tenant_id, order=order, created_by=created_by, expires_at=expires_at,
        )
        event = DomainEvent(
            event_type=SHARE_LINK_CREATED,
            tenant_id=link.tenant_id,
            aggregate_type="OrderShareLink",
            aggregate_id=link.id,
            actor_id=_actor_id(created_by),
            payload={"order_id": str(order.id), "expires_at": link.expires_at.isoformat()},
        )
        transaction.on_commit(lambda: publish_domain_event(event))
        return link

    @classmethod
    @transaction.atomic
    def resolve(cls, token: str):
        """Returns the Order for a valid, unexpired, unrevoked token. Records the
        access. Raises OrderShareLinkError for any invalid/expired/revoked/unknown
        token — never distinguishes which, to avoid leaking token existence."""
        from ..models import OrderShareLink

        try:
            link = OrderShareLink.objects.get(token=token)
        except OrderShareLink.DoesNotExist:
            raise OrderShareLinkError("This share link is invalid or has expired.")

        if not link.is_valid():
            raise OrderShareLinkError("This share link is invalid or has expired.")

        link.record_access()
        event = DomainEvent(
            event_type=SHARE_LINK_ACCESSED,
            tenant_id=link.tenant_id,
            aggregate_type="OrderShareLink",
            aggregate_id=link.id,
            payload={"order_id": str(link.order_id)},
        )
        transaction.on_commit(lambda: publish_domain_event(event))
        return link.order

    @classmethod
    def list_for_order(cls, order):
        return order.share_links.order_by("-created_at")

    @classmethod
    @transaction.atomic
    def revoke(cls, *, order, link_id, revoked_by=None):
        from ..models import OrderShareLink

        try:
            link = order.share_links.get(id=link_id)
        except OrderShareLink.DoesNotExist:
            raise OrderShareLinkError("Share link not found.")
        link.revoke()
        event = DomainEvent(
            event_type=SHARE_LINK_REVOKED,
            tenant_id=link.tenant_id,
            aggregate_type="OrderShareLink",
            aggregate_id=link.id,
            actor_id=_actor_id(revoked_by),
            payload={"order_id": str(order.id)},
        )
        transaction.on_commit(lambda: publish_domain_event(event))
        return link
