"""
API-layer exception type — Module 17A foundation.

Raised directly by API views/utilities for API-specific failures
(authentication required, tenant missing, pagination limits, etc.).
Domain/service exceptions from business modules are mapped separately by
apps.api.views.ApiView.dispatch() — see that module's docstring.
"""


class ApiError(Exception):
    """Carries everything needed to render the standard error envelope."""

    def __init__(self, *, code: str, message: str, status_code: int = 400, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
