"""Shared exception type for the finance module."""


class FinanceError(Exception):
    """Raised for finance domain-rule violations (cross-tenant access, invalid transitions, unbalanced postings)."""
