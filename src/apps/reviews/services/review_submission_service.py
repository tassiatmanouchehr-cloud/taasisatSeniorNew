"""
ReviewSubmissionService — Module 13 foundation.

The only code that creates Review + ReviewRating rows. Reviews are only
allowed for COMPLETED orders, targeting the order's (stable, once final)
assigned_supplier — never a caregiver/organization profile directly.
"""

from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction

from apps.orders.models import OrderStatus

from ..models import RATING_DECIMAL_PLACES, Review, ReviewRating, ReviewRatingDimension
from .errors import ReviewError

QUANT = Decimal("1").scaleb(-RATING_DECIMAL_PLACES)

MIN_SCORE = 1
MAX_SCORE = 5


def _q(value) -> Decimal:
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(QUANT, rounding=ROUND_HALF_UP)


class ReviewSubmissionService:
    """Creates a Review (with its dimension ratings) for a completed order."""

    @classmethod
    @transaction.atomic
    def submit_review(cls, *, order, reviewer_person_id, dimension_scores: dict, written_text="", metadata=None) -> Review:
        if order.status != OrderStatus.COMPLETED:
            raise ReviewError(
                f"Reviews are only allowed for completed orders (order is '{order.status}').",
            )

        if not order.assigned_supplier_id:
            raise ReviewError("Order has no assigned supplier to review.")

        # Epic 05 (Permission-Key Registry & Authorization Hardening)
        # confirmed authorization defect fix, previously documented in
        # technical-debt-register.md: reviewer_person_id was never checked
        # against the order's own customer, so any authenticated user with
        # the reviews.submit permission could review any completed order
        # in the tenant. apps.api.views.reviews.ReviewSubmitView already
        # only ever passes the caller's own person id — the gap was here,
        # not accepting an arbitrary id from the request.
        if order.customer_profile_id is None or order.customer_profile.person_id != reviewer_person_id:
            raise ReviewError("Only the order's own customer may submit a review for it.")

        supplier = order.assigned_supplier

        if Review.objects.filter(order=order, supplier=supplier).exists():
            raise ReviewError("A review for this order and supplier already exists.")

        if not dimension_scores:
            raise ReviewError("At least one rating dimension is required.")

        for dimension, score in dimension_scores.items():
            if dimension not in ReviewRatingDimension.values:
                raise ReviewError(f"Unknown rating dimension: {dimension}")
            if not (MIN_SCORE <= score <= MAX_SCORE):
                raise ReviewError(f"Rating for {dimension} must be between {MIN_SCORE} and {MAX_SCORE}.")

        overall_rating = _q(
            Decimal(sum(dimension_scores.values())) / Decimal(len(dimension_scores)),
        )

        review = Review.objects.create(
            tenant_id=order.tenant_id,
            order=order,
            supplier=supplier,
            reviewer_person_id=reviewer_person_id,
            overall_rating=overall_rating,
            written_text=written_text,
            metadata=metadata or {},
        )

        ReviewRating.objects.bulk_create([
            ReviewRating(tenant_id=order.tenant_id, review=review, dimension=dimension, score=score)
            for dimension, score in dimension_scores.items()
        ])

        return review
