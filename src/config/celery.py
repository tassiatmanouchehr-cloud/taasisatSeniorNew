"""
Celery configuration for the Enterprise Service Marketplace Platform.

This module configures the Celery application with Redis as broker
and result backend. Tasks are auto-discovered from all apps in apps/.
"""

import os

from celery import Celery

# Set the default Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("marketplace")

# Load task settings from Django settings, using the CELERY_ namespace
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks from all registered Django apps
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for verifying Celery connectivity."""
    print(f"Request: {self.request!r}")
