"""
Phone number validation and normalization for Iranian mobile numbers.

Accepted formats:
- 09xxxxxxxxx (11 digits, starts with 09)
- +989xxxxxxxxx (13 chars with +98 prefix)
- 989xxxxxxxxx (12 digits without +)

All are normalized to: 09xxxxxxxxx (domestic format).
"""

import re

# Iranian mobile: starts with 09, followed by 9 digits
IRAN_MOBILE_REGEX = re.compile(r"^09\d{9}$")


def validate_iranian_phone(phone: str) -> bool:
    """
    Validate an Iranian mobile phone number.

    Returns True if the phone (after normalization) matches 09xxxxxxxxx pattern.
    """
    normalized = normalize_phone(phone)
    return bool(IRAN_MOBILE_REGEX.match(normalized))


def normalize_phone(phone: str) -> str:
    """
    Normalize phone to domestic format: 09xxxxxxxxx.

    Handles:
    - +989xxxxxxxxx → 09xxxxxxxxx
    - 989xxxxxxxxx → 09xxxxxxxxx
    - 09xxxxxxxxx → 09xxxxxxxxx
    - Strips spaces, dashes, parens
    """
    # Strip whitespace and common separators
    cleaned = re.sub(r"[\s\-\(\)\+]", "", phone)

    # Handle +98 or 98 prefix
    if cleaned.startswith("98") and len(cleaned) == 12:
        cleaned = "0" + cleaned[2:]
    elif cleaned.startswith("098") and len(cleaned) == 13:
        cleaned = cleaned[1:]  # Remove leading 0 from 098...

    return cleaned
