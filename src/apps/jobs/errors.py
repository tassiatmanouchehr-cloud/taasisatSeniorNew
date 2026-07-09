"""Shared exception type for the background jobs module."""


class JobsError(Exception):
    """Raised for job domain-rule violations (unknown job_type, bad idempotency usage)."""
