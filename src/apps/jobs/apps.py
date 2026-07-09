from django.apps import AppConfig


class JobsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.jobs"
    verbose_name = "Background Jobs"

    def ready(self):
        from apps.jobs.handlers import register_handlers

        register_handlers()
