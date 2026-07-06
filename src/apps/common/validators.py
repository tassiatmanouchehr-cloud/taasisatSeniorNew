"""
Common validators for the Enterprise Service Marketplace Platform.

Reusable validation logic shared across modules.
"""

from django.core.exceptions import ValidationError


def validate_non_empty_string(value):
    """Ensure a string field is not empty or whitespace-only."""
    if not value or not value.strip():
        raise ValidationError("This field cannot be empty or whitespace-only.")
