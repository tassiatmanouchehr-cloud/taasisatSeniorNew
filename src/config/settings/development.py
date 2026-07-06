"""
Development settings for the Enterprise Service Marketplace Platform.

DEBUG enabled, verbose logging, console email backend.
"""

from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# Email — console backend for development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Additional development apps (added when installed)
# INSTALLED_APPS += [
#     "django_extensions",
#     "debug_toolbar",
# ]

# Debug toolbar settings (activated when installed)
# INTERNAL_IPS = ["127.0.0.1", "0.0.0.0"]
