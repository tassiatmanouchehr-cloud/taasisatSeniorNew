"""Shared exception type for the notifications module."""


class NotificationsError(Exception):
    """Raised for notification domain-rule violations (unknown channel, no provider registered)."""
