"""
FavoritesService — Phase 4 Sprint 4.1 (Customer Favorites and Saved
Providers).

Owner-authorized read-write for `Favorite`, mirroring
`CaregiverSkillService`'s exact shape: no RBAC permission key (ownership,
not a role, is the authorization boundary — the caller already resolved
their own `CustomerProfile` before reaching here), explicit commands only
(`add_favorite`/`remove_favorite`/`is_favorited`/`list_favorites_for_customer`
— deliberately never a single ambiguous `toggle()`, so retries,
concurrency behavior, and tests stay deterministic), and every mutation
re-scopes by `customer_profile` before touching a row.

`add_favorite()`/`remove_favorite()` are both idempotent by requirement
(unlike `CaregiverSkillService.add_skill()`, where a duplicate is a user
mistake that should raise): favoriting an already-favorited supplier
succeeds without error and returns the existing row; unfavoriting an
already-absent favorite is a no-op. Concurrency is handled the same way
`add_skill()` handles it — the DB `UniqueConstraint`
(`uq_customer_favorite_supplier`) is the real serialization point, not
the `.exists()`/`get_or_create()` call, so a raced concurrent double-add
still resolves to exactly one row: `get_or_create()`'s own internal
`IntegrityError` retry (Django >= 4.1) already normalizes this to the
existing row for us, tested explicitly below.

`supplier_id` is always validated tenant-scoped, active, and
type-scoped (`ServiceSupplier.objects.get(id=..., tenant_id=tenant_id,
status=SupplierStatus.ACTIVE, supplier_type__in=expected_supplier_types)`)
before a favorite can be created — this is what prevents a customer from
favoriting a supplier belonging to a different tenant, and (PR #16
architecture-review remediation, closing merge-blocker F1) what prevents
a supplier of the wrong type from being favorited via the wrong route
(e.g. a caregiver `ServiceSupplier` posted to the organization toggle
route). `expected_supplier_types` is always supplied by the caller (the
view, which knows which route it is) — never inferred from
client-submitted data. A wrong-tenant, wrong-type, or unknown
supplier_id all raise the same `AccountsError`, never disclosing which
case occurred (mirrors this codebase's established 404-over-403/
never-disclose convention for ownership-scoped lookups).
"""

from django.db import IntegrityError

from apps.kernel.models.supplier import ServiceSupplier, SupplierStatus

from ..models.favorites import Favorite
from .errors import AccountsError


class FavoritesService:
    """Read-write: a customer's own favorited suppliers only."""

    @classmethod
    def add_favorite(cls, customer, *, supplier_id, tenant_id, expected_supplier_types) -> Favorite:
        try:
            supplier = ServiceSupplier.objects.get(
                id=supplier_id,
                tenant_id=tenant_id,
                status=SupplierStatus.ACTIVE,
                supplier_type__in=expected_supplier_types,
            )
        except ServiceSupplier.DoesNotExist:
            raise AccountsError("Supplier not found.") from None

        try:
            favorite, _created = Favorite.objects.get_or_create(customer_profile=customer, supplier=supplier)
        except IntegrityError:
            # Belt-and-suspenders: if two concurrent requests both race past
            # get_or_create()'s own internal retry (shouldn't happen, but the
            # unique constraint is the real arbiter either way), resolve to
            # the now-existing row rather than surfacing a 500.
            favorite = Favorite.objects.get(customer_profile=customer, supplier=supplier)
        return favorite

    @classmethod
    def remove_favorite(cls, customer, *, supplier_id) -> None:
        Favorite.objects.filter(customer_profile=customer, supplier_id=supplier_id).delete()

    @classmethod
    def is_favorited(cls, customer, *, supplier_id) -> bool:
        return Favorite.objects.filter(customer_profile=customer, supplier_id=supplier_id).exists()

    @classmethod
    def list_favorites_for_customer(cls, customer):
        """Ordered newest-first, with `supplier` joined in one query
        (`select_related`) so callers can bucket by `supplier.supplier_type`
        without a second query per row."""
        return Favorite.objects.filter(customer_profile=customer).select_related("supplier")
