"""Shared exception type for the pricing module."""


class PricingError(Exception):
    """Raised for pricing domain-rule violations (invalid rules, unresolvable quotes)."""
