"""
OrderShareLinkService — Customer Experience Phase 1.

Generates and resolves read-only, time-limited, revocable share links for
a single order. A share-link viewer never authenticates as any
UserAccount — the token itself is the only credential, scoped to exactly
one order, and grants nothing beyond viewing it.
"""

from django.db import transaction
from django.utils import timezone

DEFAULT_VALIDITY = timezone.timedelta(days=14)


class OrderShareLinkError(Exception):
    pass


class OrderShareLinkService:
    """Creates, resolves, and revokes OrderShareLink rows."""

    @classmethod
    @transaction.atomic
    def create(cls, *, order, created_by=None, valid_for=None):
        from ..models import OrderShareLink

        expires_at = timezone.now() + (valid_for or DEFAULT_VALIDITY)
        return OrderShareLink.objects.create(
            tenant_id=order.tenant_id, order=order, created_by=created_by, expires_at=expires_at,
        )

    @classmethod
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
        return link.order

    @classmethod
    def list_for_order(cls, order):
        return order.share_links.order_by("-created_at")

    @classmethod
    @transaction.atomic
    def revoke(cls, *, order, link_id):
        from ..models import OrderShareLink

        try:
            link = order.share_links.get(id=link_id)
        except OrderShareLink.DoesNotExist:
            raise OrderShareLinkError("Share link not found.")
        link.revoke()
        return link
