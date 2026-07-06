"""
Shared enums and choices for the Enterprise Service Marketplace Platform.

These are used across multiple modules for status fields, types, etc.
Domain-specific enums belong in their respective module apps.
"""

from django.db import models


class EntityStatus(models.TextChoices):
    """Generic entity lifecycle status used across modules."""

    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"
    ARCHIVED = "archived", "Archived"


class AuditClass(models.TextChoices):
    """Audit classification per Module 25 Audit Envelope Standard."""

    STANDARD = "standard", "Standard"
    FINANCIAL = "financial", "Financial"
    SECURITY = "security", "Security"
    COMPLIANCE = "compliance", "Compliance"


class PrivacyClass(models.TextChoices):
    """Privacy classification per Module 25 Privacy Classification Standard."""

    PUBLIC = "public", "Public"
    INTERNAL = "internal", "Internal"
    RESTRICTED = "restricted", "Restricted"
    SENSITIVE = "sensitive", "Sensitive"
