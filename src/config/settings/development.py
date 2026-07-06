"""
Development settings for the Enterprise Service Marketplace Platform.

Supports both Docker and native Python development:
- Docker: all services via docker-compose (env vars set by .env)
- Native: PostgreSQL + Redis running locally (set env vars manually or use .env)

DEBUG enabled, verbose logging, console email backend.
"""

from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "*"]

# Email — console backend for development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Additional development apps (uncomment when installed)
# INSTALLED_APPS += [
#     "django_extensions",
#     "debug_toolbar",
# ]

# Debug toolbar settings (uncomment when installed)
# INTERNAL_IPS = ["127.0.0.1", "0.0.0.0"]
# MIDDLEWARE.insert(2, "debug_toolbar.middleware.DebugToolbarMiddleware")
