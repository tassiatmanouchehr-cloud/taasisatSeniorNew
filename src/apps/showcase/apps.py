"""Django app configuration for the UI Component Showcase."""

from django.apps import AppConfig


class ShowcaseConfig(AppConfig):
    """UI Component Showcase — development-only design system browser."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.showcase"
    verbose_name = "UI Showcase"
