"""
Testing settings for the Enterprise Service Marketplace Platform.

Optimized for fast test execution.

Supports two modes:
1. Full integration tests: Use PostgreSQL (set DATABASE_* env vars)
2. Isolated unit tests: Set USE_SQLITE=1 for SQLite-based tests (no PostGIS features)

Redis is replaced with local memory cache for all tests.
"""

import os

from .base import *  # noqa: F401, F403

DEBUG = False

# --- Database Configuration ---
# For unit tests that don't need PostGIS, allow SQLite fallback
if os.environ.get("USE_SQLITE", "0") == "1":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
    # Remove GIS app when using SQLite (no spatial support)
    INSTALLED_APPS = [app for app in INSTALLED_APPS if app != "django.contrib.gis"]  # noqa: F405
else:
    # Use PostgreSQL for integration tests (same as base, different test DB name)
    DATABASES["default"]["TEST"] = {  # noqa: F405
        "NAME": os.environ.get("DATABASE_TEST_NAME", "test_marketplace"),
    }

# --- Cache ---
# Always use local memory cache in tests (no Redis dependency)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-cache",
        "KEY_PREFIX": "mkt_test",
        "TIMEOUT": 300,
    }
}

# --- Celery ---
# Use synchronous task execution in tests (no Redis/broker needed)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"

# --- Performance ---
# Use a faster password hasher in tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# --- Email ---
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# --- Logging ---
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
