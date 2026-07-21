"""
Service Catalog and Order models.
"""

import uuid

from django.conf import settings
from django.db import IntegrityError, models, router, transaction
from django.db.models import F
from django.utils import timezone

from apps.common.managers import TenantScopedManager

# ============================================================
# Service Catalog
# ============================================================


class CatalogStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"


class ServiceCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="service_categories",
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=20, choices=CatalogStatus.choices, default=CatalogStatus.ACTIVE)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "orders_service_category"
        ordering = ["sort_order", "name"]
        verbose_name_plural = "Service Categories"
        unique_together = [("tenant", "slug")]

    def __str__(self):
        return self.name


class ServiceType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="service_types",
    )
    category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, related_name="service_types")
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100)
    description = models.TextField(blank=True)
    base_duration_minutes = models.IntegerField(null=True, blank=True)
    requires_elder_profile = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=CatalogStatus.choices, default=CatalogStatus.ACTIVE)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "orders_service_type"
        ordering = ["sort_order", "name"]
        unique_together = [("tenant", "category", "slug")]

    def __str__(self):
        return f"{self.category.name} / {self.name}"


# ============================================================
# Order
# ============================================================


class OrderSource(models.TextChoices):
    PUBLIC = "public", "Public/Customer"
    OPERATOR = "operator", "Operator/Phone"


class OrderStatus(models.TextChoices):
    PENDING_OPERATOR_REVIEW = "pending_operator_review", "در انتظار تایید اپراتور"
    NEW = "new", "جدید"
    WAITING_SERVICE = "waiting_service", "در انتظار انجام خدمت"
    IN_PROGRESS = "in_progress", "در حال انجام خدمت"
    COMPLETED = "completed", "انجام شده"
    CANCELLATION_REQUESTED = "cancellation_requested", "درخواست لغو"
    CANCELLED = "cancelled", "لغو شده"


FINAL_STATUSES = {OrderStatus.COMPLETED, OrderStatus.CANCELLED}


# order_number is globally unique (not per-tenant) and drawn from a per-day
# random space, so same-day collisions are possible and must be survivable
# (BG-002). 6 digits gives 10^6 numbers/day; Order.save() retries a bounded
# number of times when the database unique constraint rejects a generated
# number. The constraint itself stays the arbiter — generation never checks
# first, so concurrent creators cannot race past each other.
ORDER_NUMBER_SUFFIX_LENGTH = 6
ORDER_NUMBER_MAX_ATTEMPTS = 5


def _generate_order_number():
    """Generate a human-readable order number: ORD-YYYYMMDD-XXXXXX."""
    from django.utils.crypto import get_random_string

    date_part = timezone.now().strftime("%Y%m%d")
    random_part = get_random_string(ORDER_NUMBER_SUFFIX_LENGTH, "0123456789")
    return f"ORD-{date_part}-{random_part}"


def _is_order_number_collision(exc):
    """True when an IntegrityError comes from the order_number unique
    constraint (PostgreSQL: "orders_order_order_number_key"; SQLite:
    "orders_order.order_number") rather than some other constraint."""
    return "order_number" in str(exc)


class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="orders",
    )
    order_number = models.CharField(max_length=30, unique=True, db_index=True)
    source = models.CharField(max_length=20, choices=OrderSource.choices)
    status = models.CharField(max_length=30, choices=OrderStatus.choices, db_index=True)

    # Customer/Elder
    customer_profile = models.ForeignKey(
        "accounts.CustomerProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    elder_profile = models.ForeignKey(
        "accounts.ElderProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    trusted_contact = models.ForeignKey(
        "accounts.TrustedContact",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )

    # Service
    service_category = models.ForeignKey(ServiceCategory, on_delete=models.PROTECT, related_name="orders")
    service_type = models.ForeignKey(
        ServiceType, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders"
    )

    # Details
    description = models.TextField()
    city = models.CharField(max_length=100)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    requested_date = models.DateField(null=True, blank=True)
    requested_time_window = models.CharField(max_length=100, blank=True)

    # Assignment — ServiceSupplier is the single source of truth.
    # See assigned_provider/assigned_organization properties below for
    # read-only, backward-compatible access to the resolved profile.
    assigned_supplier = models.ForeignKey(
        "kernel.ServiceSupplier",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_orders",
    )

    # Actors
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_orders"
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_orders"
    )
    cancellation_requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    # Timestamps
    approved_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    # Notes
    cancellation_reason = models.TextField(blank=True)
    internal_note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "orders_order"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.order_number} [{self.get_status_display()}]"

    def save(self, *args, **kwargs):
        if self.order_number:
            # Caller-supplied numbers are never retried: a duplicate must
            # surface as an IntegrityError, not be silently replaced.
            return super().save(*args, **kwargs)

        # Each attempt runs in its own savepoint so a rejected insert does
        # not poison a caller's surrounding atomic block; a fresh number is
        # drawn only after the database itself reports the collision.
        using = kwargs.get("using") or router.db_for_write(type(self), instance=self)
        for attempt in range(1, ORDER_NUMBER_MAX_ATTEMPTS + 1):
            self.order_number = _generate_order_number()
            try:
                with transaction.atomic(using=using):
                    return super().save(*args, **kwargs)
            except IntegrityError as exc:
                if attempt == ORDER_NUMBER_MAX_ATTEMPTS or not _is_order_number_collision(exc):
                    raise

    @property
    def assigned_provider(self):
        """Read-only: the CaregiverProfile behind assigned_supplier, if any.

        Kept for backward compatibility. ServiceSupplier (assigned_supplier)
        is the only writable assignment field on Order.
        """
        from apps.accounts.models import CaregiverProfile
        from apps.accounts.services.supplier_bridge import resolve_supplier_entity

        entity = resolve_supplier_entity(self.assigned_supplier)
        return entity if isinstance(entity, CaregiverProfile) else None

    @property
    def assigned_organization(self):
        """Read-only: the OrganizationProfile behind assigned_supplier, if any.

        Kept for backward compatibility. ServiceSupplier (assigned_supplier)
        is the only writable assignment field on Order.
        """
        from apps.accounts.models import OrganizationProfile
        from apps.accounts.services.supplier_bridge import resolve_supplier_entity

        entity = resolve_supplier_entity(self.assigned_supplier)
        return entity if isinstance(entity, OrganizationProfile) else None


# ============================================================
# OrderOrganizationEligibility — Epic 04 (Enterprise Organization
# Isolation). Explicit junction between Order and OrganizationProfile:
# an organization may claim/assign an order only if an ACTIVE row exists
# here for that (order, organization) pair, or the order is already
# assigned to a supplier resolving to that organization (the
# post-assignment ownership rule — evaluated in
# apps.orders.services.queries.OrderQueryService, not here).
#
# The ONLY writer is apps.orders.services.eligibility_service
# .OrderEligibilityService — no other caller may construct this model
# directly (enforced by
# apps.orders.tests.test_architecture_guardrails.EligibilityWriterGuardrailTest).
#
# No automatic/implicit grant rule exists anywhere in this Epic — see
# OrderEligibilityService's own module docstring for why (verified: no
# existing business signal at order-creation time identifies an eligible
# organization). Every row is the result of an explicit, actor-attributed
# grant() call.
# ============================================================


class EligibilityStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    WITHDRAWN = "withdrawn", "Withdrawn"


class OrderOrganizationEligibility(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="order_organization_eligibilities",
    )
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="organization_eligibilities")
    organization = models.ForeignKey(
        "accounts.OrganizationProfile",
        on_delete=models.CASCADE,
        related_name="order_eligibilities",
    )
    status = models.CharField(
        max_length=20,
        choices=EligibilityStatus.choices,
        default=EligibilityStatus.ACTIVE,
        db_index=True,
    )
    source = models.CharField(
        max_length=20,
        default="manual",
        help_text="Always 'manual' in this Epic — every row is an explicit grant() call. "
        "Plain string, not an enum: constraining it now would be speculative.",
    )
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    granted_at = models.DateTimeField(auto_now_add=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    revoked_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "orders_organization_eligibility"
        ordering = ["-granted_at"]
        unique_together = [("order", "organization")]
        indexes = [
            models.Index(fields=["tenant", "order", "status"], name="idx_orgelig_tenant_order_st"),
            models.Index(fields=["tenant", "organization", "status"], name="idx_orgelig_tenant_org_st"),
        ]

    def __str__(self):
        return f"Eligibility(order={self.order_id}, org={self.organization_id}) [{self.status}]"


class OrderStatusHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="order_status_history",
    )
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(max_length=30, blank=True)
    to_status = models.CharField(max_length=30)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    reason = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "orders_status_history"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.order.order_number}: {self.from_status} → {self.to_status}"


# ============================================================
# OrderShareLink — Customer Experience Phase 1 / ADR-008
#
# Read-only, invitation-based, single-order visibility for someone who is
# not a platform account holder — the "Order Share Link" ADR-008 scoped as
# future work. The token is an unguessable capability, not a hashed
# credential — the same "unguessable token is the entire security model"
# pattern already used by the fake payment callback's provider_reference
# (see docs/architecture/technical-debt-register.md). Hashing the stored
# token would be a real future hardening step, same as that callback's
# still-deferred signature verification — not done here, and noted so a
# reviewer doesn't mistake the omission for an oversight.
# ============================================================


def _generate_share_token():
    import secrets

    return secrets.token_urlsafe(32)


class OrderShareLink(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="order_share_links",
    )
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="share_links")
    token = models.CharField(max_length=64, unique=True, db_index=True, default=_generate_share_token)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    expires_at = models.DateTimeField(help_text="Link stops working after this time, even if never revoked.")
    revoked_at = models.DateTimeField(null=True, blank=True)
    access_count = models.IntegerField(default=0)
    last_accessed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "orders_share_link"
        ordering = ["-created_at"]

    def __str__(self):
        return f"ShareLink({self.order.order_number}) [{'revoked' if self.revoked_at else 'active'}]"

    def is_valid(self) -> bool:
        return self.revoked_at is None and self.expires_at > timezone.now()

    def revoke(self):
        self.revoked_at = timezone.now()
        self.save(update_fields=["revoked_at"])

    def record_access(self):
        """Atomic, race-free increment — two concurrent accesses to the same
        link (e.g. opened from two devices at once) never lose an update,
        unlike a read-modify-write `self.access_count += 1`."""
        type(self).objects.filter(pk=self.pk).update(
            access_count=F("access_count") + 1,
            last_accessed_at=timezone.now(),
        )
        self.refresh_from_db(fields=["access_count", "last_accessed_at"])


# ============================================================
# Order Offers (Offer Marketplace — Phase 1)
# ============================================================


class OrderOfferStatus(models.TextChoices):
    """Lifecycle states for a supplier-submitted offer on an order."""

    SUBMITTED = "submitted", "Submitted"
    SELECTED = "selected", "Selected"  # 30-minute hold active
    ACCEPTED = "accepted", "Accepted"  # Finalized (payment success in later phases)
    EXPIRED = "expired", "Expired"  # Hold timed out
    WITHDRAWN = "withdrawn", "Withdrawn"  # Supplier withdrew
    REJECTED = "rejected", "Rejected"  # Superseded by another selection
    CANCELLED = "cancelled", "Cancelled"  # Order cancelled while offer was active


# Terminal states — no further transitions allowed.
OFFER_TERMINAL_STATUSES = frozenset(
    {
        OrderOfferStatus.ACCEPTED,
        OrderOfferStatus.EXPIRED,
        OrderOfferStatus.WITHDRAWN,
        OrderOfferStatus.REJECTED,
        OrderOfferStatus.CANCELLED,
    }
)


class OrderOffer(models.Model):
    """A supplier-submitted commercial offer for an order.

    One OrderOffer per (order, supplier). At most one OrderOffer per order
    may be SELECTED at any time.

    Payment, assignment, deadline, and settlement integrations are
    introduced in later implementation phases.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="order_offers",
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="offers",
    )
    supplier = models.ForeignKey(
        "kernel.ServiceSupplier",
        on_delete=models.CASCADE,
        related_name="order_offers",
    )

    # Offer content — DecimalField(14,2) matches repository canonical money representation
    price_amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=10, default="IRR")
    estimated_duration_minutes = models.IntegerField(null=True, blank=True)
    terms = models.TextField(blank=True)
    message = models.TextField(blank=True)

    # Lifecycle
    status = models.CharField(
        max_length=20,
        choices=OrderOfferStatus.choices,
        default=OrderOfferStatus.SUBMITTED,
        db_index=True,
    )

    # Ownership
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="+",
    )

    # Hold tracking (only meaningful when status=SELECTED)
    selected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    selected_at = models.DateTimeField(null=True, blank=True)
    hold_expires_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "orders_order_offer"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["order", "supplier"],
                name="uq_order_offer_one_per_supplier",
            ),
            models.UniqueConstraint(
                fields=["order"],
                condition=models.Q(status="selected"),
                name="uq_order_offer_one_selected_per_order",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "order", "status"], name="idx_offer_tenant_order_st"),
            models.Index(fields=["tenant", "supplier", "status"], name="idx_offer_tenant_supplier_st"),
        ]

    def __str__(self):
        return f"OrderOffer(order={self.order_id}, supplier={self.supplier_id}) [{self.status}]"

    @property
    def is_terminal(self) -> bool:
        return self.status in OFFER_TERMINAL_STATUSES

    @property
    def is_active(self) -> bool:
        return self.status in (OrderOfferStatus.SUBMITTED, OrderOfferStatus.SELECTED)

    @property
    def hold_active(self) -> bool:
        """True if the offer is SELECTED and the hold has not expired."""
        if self.status != OrderOfferStatus.SELECTED:
            return False
        if self.hold_expires_at is None:
            return False
        return self.hold_expires_at > timezone.now()

    @property
    def can_edit(self) -> bool:
        """True only when the offer is SUBMITTED."""
        return self.status == OrderOfferStatus.SUBMITTED

    @property
    def can_withdraw(self) -> bool:
        """True only when the offer is SUBMITTED."""
        return self.status == OrderOfferStatus.SUBMITTED

    @property
    def can_select(self) -> bool:
        """True only when the offer is SUBMITTED."""
        return self.status == OrderOfferStatus.SUBMITTED
