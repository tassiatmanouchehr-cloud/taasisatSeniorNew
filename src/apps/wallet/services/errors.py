"""Shared exception type for the wallet module."""


class WalletError(Exception):
    """Raised for wallet domain-rule violations (insufficient funds, bad amounts, tenant mismatch)."""
