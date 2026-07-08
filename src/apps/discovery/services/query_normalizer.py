"""
Search query normalization — Module 12 foundation.

No ranking/ML here — just deterministic input cleanup: whitespace
collapsing, casefolding for case-insensitive matching, and clamping
limit/offset to safe, bounded values.
"""

from .configuration import DEFAULT_LIMIT, MAX_LIMIT
from .dto import SearchQuery


def normalize_query(
    *,
    tenant_id,
    text="",
    service_category_id=None,
    supplier_type=None,
    availability_status=None,
    verification_level=None,
    city=None,
    requested_start=None,
    requested_end=None,
    limit=None,
    offset=0,
) -> SearchQuery:
    normalized_text = " ".join((text or "").split()).casefold()
    normalized_city = " ".join((city or "").split()).casefold() or None

    resolved_limit = DEFAULT_LIMIT if limit is None else limit
    bounded_limit = max(1, min(int(resolved_limit), MAX_LIMIT))
    bounded_offset = max(0, int(offset or 0))

    return SearchQuery(
        tenant_id=tenant_id,
        text=normalized_text,
        service_category_id=service_category_id,
        supplier_type=supplier_type,
        availability_status=availability_status,
        verification_level=verification_level,
        city=normalized_city,
        requested_start=requested_start,
        requested_end=requested_end,
        limit=bounded_limit,
        offset=bounded_offset,
    )
