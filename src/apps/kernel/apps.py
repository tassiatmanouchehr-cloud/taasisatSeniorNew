"""Django app configuration for the Kernel module (Module 25)."""

from django.apps import AppConfig


class KernelConfig(AppConfig):
    """Platform Kernel — shared contracts, tenant, identity, supplier, audit, events."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.kernel"
    verbose_name = "Platform Kernel"
