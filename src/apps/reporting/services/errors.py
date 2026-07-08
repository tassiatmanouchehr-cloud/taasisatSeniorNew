"""Shared exception type for the reporting module."""


class ReportingError(Exception):
    """Raised for reporting-layer misuse (e.g. missing tenant_id)."""
