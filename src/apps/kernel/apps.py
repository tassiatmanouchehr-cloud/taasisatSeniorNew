"""Django app configuration for the Kernel module (Module 25)."""

from django.apps import AppConfig


class KernelConfig(AppConfig):
    """Platform Kernel — shared contracts, tenant, identity, supplier, audit, events."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.kernel"
    verbose_name = "Platform Kernel"

    def ready(self):
        # Epic 05 (Permission-Key Registry & Authorization Hardening):
        # importing this module is what populates
        # apps.kernel.permissions.registry.PermissionRegistry — every
        # register() call at its module scope runs exactly once, here.
        from apps.kernel.permissions import keys  # noqa: F401
