from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.payments"
    verbose_name = "Payment Gateway Integration"

    def ready(self):
        from .jobs import register_handlers

        register_handlers()
