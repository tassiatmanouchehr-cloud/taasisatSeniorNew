"""Shared exception type for the payments module."""


class PaymentError(Exception):
    """Raised for payment domain-rule violations (invalid state transition, amount/currency mismatch)."""
