"""Shared exception type for the accounts module."""


class AccountsError(Exception):
    """Raised for accounts domain-rule violations (e.g. a care recipient
    that does not belong to the requesting customer)."""
