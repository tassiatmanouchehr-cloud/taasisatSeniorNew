"""Shared exception type for the availability module."""


class AvailabilityError(Exception):
    """Raised for availability domain-rule violations (invalid ranges, invalid input)."""
