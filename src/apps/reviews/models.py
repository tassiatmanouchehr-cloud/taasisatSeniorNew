"""
Reviews, Ratings & Reputation — Module 13 foundation.

Reviews target apps.kernel.models.supplier.ServiceSupplier only — never
CaregiverProfile/OrganizationProfile directly, the same unification
principle established in Modules 10-12. The reviewer is stored as a
generic kernel.Person id (reviewer_person_id), not a hard FK to
CustomerProfile, mirroring apps.notifications.models.Notification.recipient.

ServiceSupplier.reputation_score already exists (docstring: "cached from
Module 06/14, updated by Module 06/14 events") — this module is that
reserved owner. ReputationService writes through to it; Discovery/Matching
need no code changes since they already read that field directly.
"""

import uuid

from django.db import models

from apps.common.managers import TenantScopedManager

RATING_MAX_DIGITS = 3
RATING_DECIMAL_PLACES = 2


class ReviewModerationStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"


class Review(models.Model):
    """One customer review of a supplier for a (normally) completed Order."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant", on_delete=models.PROTECT, related_name="reviews",
    )
    order = models.ForeignKey(
        "orders.Order", on_delete=models.SET_NULL, null=True, blank=True, related_name="reviews",
    )
    supplier = models.ForeignKey(
        "kernel.ServiceSupplier", on_delete=models.PROTECT, related_name="reviews",
    )
    reviewer_person_id = models.UUIDField(help_text="kernel.Person id of the reviewer.")

    moderation_status = models.CharField(
        max_length=20, choices=ReviewModerationStatus.choices, default=ReviewModerationStatus.PENDING, db_index=True,
    )
    moderation_reason = models.TextField(blank=True)
    moderated_at = models.DateTimeField(null=True, blank=True)

    overall_rating = models.DecimalField(max_digits=RATING_MAX_DIGITS, decimal_places=RATING_DECIMAL_PLACES)
    written_text = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "reviews_review"
        ordering = ["-created_at"]
        unique_together = [("order", "supplier")]
        indexes = [
            models.Index(fields=["tenant", "supplier", "moderation_status"], name="idx_review_tenant_sup_mod"),
        ]

    def __str__(self):
        return f"Review({self.supplier_id}, {self.overall_rating}) [{self.moderation_status}]"


class ReviewRatingDimension(models.TextChoices):
    QUALITY = "QUALITY", "Quality"
    PUNCTUALITY = "PUNCTUALITY", "Punctuality"
    PROFESSIONALISM = "PROFESSIONALISM", "Professionalism"
    COMMUNICATION = "COMMUNICATION", "Communication"


class ReviewRating(models.Model):
    """One rating-dimension score within a Review. Bounds (1-5) are service-validated."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant", on_delete=models.PROTECT, related_name="review_ratings",
    )
    review = models.ForeignKey(
        "reviews.Review", on_delete=models.CASCADE, related_name="ratings",
    )
    dimension = models.CharField(max_length=20, choices=ReviewRatingDimension.choices)
    score = models.IntegerField()

    objects = TenantScopedManager()

    class Meta:
        db_table = "reviews_review_rating"
        unique_together = [("review", "dimension")]

    def __str__(self):
        return f"{self.dimension}={self.score} (review={self.review_id})"


class ReputationSnapshot(models.Model):
    """Denormalized, deterministic aggregate cache — one row per supplier."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant", on_delete=models.PROTECT, related_name="reputation_snapshots",
    )
    supplier = models.OneToOneField(
        "kernel.ServiceSupplier", on_delete=models.CASCADE, related_name="reputation_snapshot",
    )
    review_count = models.PositiveIntegerField(default=0)
    average_score = models.DecimalField(
        max_digits=RATING_MAX_DIGITS, decimal_places=RATING_DECIMAL_PLACES, null=True, blank=True,
    )
    last_calculated_at = models.DateTimeField(auto_now=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "reviews_reputation_snapshot"

    def __str__(self):
        return f"ReputationSnapshot(supplier={self.supplier_id}, avg={self.average_score}, n={self.review_count})"
