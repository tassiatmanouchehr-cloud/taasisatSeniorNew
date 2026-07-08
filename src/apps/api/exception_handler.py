"""
DRF exception handler — Module 17A foundation, extended in Module 17B.

The single place that maps exceptions to the standard error envelope
`{"error": {"code", "message", "details"}}`. Wired via
settings.REST_FRAMEWORK["EXCEPTION_HANDLER"], so every apps.api view gets
it automatically through DRF's own dispatch/handle_exception machinery.

Module 17B adds _DOMAIN_ERROR_CLASSES: a small, explicit allowlist of
per-module exception types (DiscoveryError, PricingError, ReviewError,
WalletError, PaymentError) mapped to a generic 400 "domain_error". Their
messages are already safe, human-written strings (never tracebacks) by
convention across every module — see e.g. apps.wallet.services.errors.
This does not attempt to cover every module; only the ones this module's
endpoints can actually raise.
"""

import logging

from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from apps.discovery.services import DiscoveryError
from apps.kernel.services.errors import PermissionDenied
from apps.payments.services import PaymentError
from apps.pricing.services import PricingError
from apps.reviews.services import ReviewError
from apps.wallet.services import WalletError

from .errors import ApiError

logger = logging.getLogger(__name__)

_DOMAIN_ERROR_CLASSES = (DiscoveryError, PricingError, ReviewError, WalletError, PaymentError)

_STATUS_CODE_DEFAULTS = {
    400: "validation_error",
    401: "authentication_required",
    403: "permission_denied",
    404: "not_found",
    405: "method_not_allowed",
    406: "not_acceptable",
    415: "unsupported_media_type",
    429: "throttled",
}


def api_exception_handler(exc, context):
    """Every exception a Module 17A+ API view can raise passes through here."""

    if isinstance(exc, ApiError):
        return _envelope(code=exc.code, message=exc.message, details=exc.details, status=exc.status_code)

    if isinstance(exc, _DOMAIN_ERROR_CLASSES):
        return _envelope(code="domain_error", message=str(exc), status=400)

    if isinstance(exc, PermissionDenied):
        return _envelope(
            code="permission_denied", message=str(exc) or "Permission denied.", status=403,
        )

    if isinstance(exc, (Http404, ObjectDoesNotExist)):
        return _envelope(code="not_found", message="The requested resource was not found.", status=404)

    response = drf_exception_handler(exc, context)
    if response is not None:
        code = _STATUS_CODE_DEFAULTS.get(response.status_code, "error")
        message, details = _extract_message_and_details(response.data)
        return _envelope(code=code, message=message, details=details, status=response.status_code)

    # DRF's default handler returns None for anything it doesn't recognize
    # (plain Python exceptions) — never let that propagate as an
    # unhandled traceback/HTML page. Always answer with the JSON envelope.
    logger.exception("Unhandled exception in API view", exc_info=exc)
    return _envelope(code="internal_error", message="An unexpected error occurred.", status=500)


def _extract_message_and_details(data):
    if isinstance(data, dict):
        if "detail" in data and len(data) == 1:
            return str(data["detail"]), {}
        return "Request could not be processed.", data
    if isinstance(data, list):
        return "Request could not be processed.", {"errors": data}
    return str(data), {}


def _envelope(*, code: str, message: str, status: int, details: dict | None = None) -> Response:
    return Response({"error": {"code": code, "message": message, "details": details or {}}}, status=status)
