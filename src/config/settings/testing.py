"""
Testing settings for the Enterprise Service Marketplace Platform.

Optimized for fast test execution.
"""

import os

from .base import *  # noqa: F401, F403

DEBUG = False

# Test database — use same engine, different name
DATABASES["default"]["TEST"] = {  # noqa: F405
    "NAME": os.environ.get("DATABASE_TEST_NAME", "test_marketplace"),
}

# Use a faster password hasher in tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Disable migrations in tests for speed (use --create-db when schema changes)
# class DisableMigrations:
#     def __contains__(self, item):
#         return True
#     def __getitem__(self, item):
#         return None
#
# MIGRATION_MODULES = DisableMigrations()

# Email — in-memory backend for testing
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Disable logging noise during tests
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "root": {
        "handlers": ["null"],
        "level": "CRITICAL",
    },
}
