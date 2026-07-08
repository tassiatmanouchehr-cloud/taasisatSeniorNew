"""Shared exception type for the reviews module."""


class ReviewError(Exception):
    """Raised for review domain-rule violations (invalid order state, duplicate review, bad ratings)."""
