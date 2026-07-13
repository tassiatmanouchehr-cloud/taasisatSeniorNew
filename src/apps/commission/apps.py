from django.apps import AppConfig


class CommissionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.commission"
    verbose_name = "Commission & Financial Policy Engine"

    def ready(self):
        from .jobs import register_handlers

        register_handlers()
