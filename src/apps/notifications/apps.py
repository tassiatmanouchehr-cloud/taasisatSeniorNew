from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"
    verbose_name = "Notifications"

    def ready(self):
        from apps.kernel.events.handlers import register_handlers
        from apps.notifications.jobs import register_job_handlers
        from apps.notifications.providers.fake import register_providers

        register_handlers()
        register_providers()
        register_job_handlers()
