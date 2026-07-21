"""
Reusable limit/offset pagination utility — Module 17A foundation.

Works over any sequence (list, tuple, or QuerySet — slicing a QuerySet
still produces a single LIMIT/OFFSET SQL query, so this is safe to use
against real querysets in future modules, not just in-memory sequences).
"""

from dataclasses import dataclass, field
from typing import Any

from django.db.models import QuerySet

from .errors import ApiError

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


@dataclass(frozen=True)
class Page:
    results: tuple[Any, ...] = field(default_factory=tuple)
    limit: int = DEFAULT_LIMIT
    offset: int = 0
    total_count: int = 0
    has_more: bool = False


def parse_pagination_params(
    query_params, *, default_limit: int = DEFAULT_LIMIT, max_limit: int = MAX_LIMIT
) -> tuple[int, int]:
    """Parses limit/offset from a request's GET-style query params, safely bounded."""
    raw_limit = query_params.get("limit")
    raw_offset = query_params.get("offset")

    limit = default_limit
    if raw_limit is not None:
        try:
            limit = int(raw_limit)
        except (TypeError, ValueError):
            raise ApiError(code="validation_error", message="`limit` must be an integer.", status_code=400)
        if limit < 1:
            raise ApiError(code="validation_error", message="`limit` must be at least 1.", status_code=400)
        limit = min(limit, max_limit)

    offset = 0
    if raw_offset is not None:
        try:
            offset = int(raw_offset)
        except (TypeError, ValueError):
            raise ApiError(code="validation_error", message="`offset` must be an integer.", status_code=400)
        if offset < 0:
            raise ApiError(code="validation_error", message="`offset` must be non-negative.", status_code=400)

    return limit, offset


def paginate(items, *, limit: int = DEFAULT_LIMIT, offset: int = 0, max_limit: int = MAX_LIMIT) -> Page:
    """Slices `items` into a Page, applying the safe limit cap.

    Uses .count() for a Django QuerySet so the total is a single COUNT
    query and the slice is a single LIMIT/OFFSET query, rather than
    forcing the whole queryset into memory via len(). Plain lists/tuples
    fall back to len() (list.count(value) has a different signature, so
    this must check the concrete QuerySet type rather than duck-typing).
    """
    limit = min(max(limit, 1), max_limit)
    offset = max(offset, 0)

    total_count = items.count() if isinstance(items, QuerySet) else len(items)
    results = tuple(items[offset : offset + limit])
    has_more = (offset + limit) < total_count

    return Page(results=results, limit=limit, offset=offset, total_count=total_count, has_more=has_more)
