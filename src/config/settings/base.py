"""
Base Django settings for the Enterprise Service Marketplace Platform.

This file contains shared settings used across all environments.
Environment-specific settings are in development.py, testing.py, and production.py.
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _load_local_env() -> None:
    """Load KEY=VALUE pairs from BASE_DIR/.env for native development.

    This keeps Windows/native runs simple: `python manage.py runserver`
    reads the same .env file that Docker uses, without requiring users to
    manually set PowerShell environment variables. Existing OS environment
    variables still take priority.
    """
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_local_env()

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-change-in-production")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = []

# GIS/PostGIS support — optional for native development
# Set GIS_ENABLED=false on Windows/native dev where GDAL is not available.
# Production and Docker default to GIS_ENABLED=true.
GIS_ENABLED = os.environ.get("GIS_ENABLED", "false").lower() in ("true", "1", "yes")

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Platform apps
    "apps.kernel",
    "apps.accounts",
    "apps.orders",
    "apps.matching",
    "apps.booking",
    "apps.execution",
    "apps.finance",
    "apps.notifications",
    "apps.availability",
    "apps.pricing",
    "apps.discovery",
    "apps.reviews",
    "apps.wallet",
    "apps.payments",
    "apps.reporting",
    "apps.showcase",
    "apps.public_site",
]

# Conditionally add GIS support (requires GDAL + PostGIS)
if GIS_ENABLED:
    INSTALLED_APPS.insert(-1, "django.contrib.gis")  # Before apps.kernel

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.kernel.middleware.correlation.CorrelationMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
            BASE_DIR,
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database — PostgreSQL (with optional PostGIS when GIS_ENABLED=true)
# Native dev (Windows): GIS_ENABLED=false → django.db.backends.postgresql
# Docker/production: GIS_ENABLED=true → django.contrib.gis.db.backends.postgis
_default_db_engine = (
    "django.contrib.gis.db.backends.postgis" if GIS_ENABLED
    else "django.db.backends.postgresql"
)
_database_engine = os.environ.get("DATABASE_ENGINE", _default_db_engine)

if _database_engine in ("sqlite", "sqlite3", "django.db.backends.sqlite3"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.environ.get("SQLITE_NAME", str(BASE_DIR / "db.sqlite3")),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": _database_engine,
            "NAME": os.environ.get("DATABASE_NAME", "marketplace"),
            "USER": os.environ.get("DATABASE_USER", "marketplace"),
            "PASSWORD": os.environ.get("DATABASE_PASSWORD", "marketplace"),
            "HOST": os.environ.get("DATABASE_HOST", "localhost"),
            "PORT": os.environ.get("DATABASE_PORT", "5432"),
            "OPTIONS": {
                "connect_timeout": 5,
            },
            "CONN_MAX_AGE": 60,
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Cache — Redis (default), with fallback to local memory if REDIS_URL not set
_redis_url = os.environ.get("REDIS_URL", "")
if _redis_url:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": _redis_url,
            "KEY_PREFIX": "mkt",
            "TIMEOUT": 300,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "marketplace-cache",
            "KEY_PREFIX": "mkt",
            "TIMEOUT": 300,
        }
    }

# Internationalization
LANGUAGE_CODE = os.environ.get("LANGUAGE_CODE", "fa-ir")
TIME_ZONE = os.environ.get("TIME_ZONE", "Asia/Tehran")
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"
STATICFILES_DIRS = [
    BASE_DIR / "static",
    ("ui", BASE_DIR / "ui"),
]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Custom user model — per ADR-001.01 (Person separate from UserAccount)
AUTH_USER_MODEL = "kernel.UserAccount"

# Celery — Task queue with Redis broker
# Falls back to synchronous execution if no broker configured
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_ENABLE_UTC = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300  # 5 minutes hard limit
CELERY_TASK_SOFT_TIME_LIMIT = 240  # 4 minutes soft limit
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # Fair scheduling
CELERY_TASK_ACKS_LATE = True  # Acknowledge after execution (crash safety)

# Celery Beat schedule — periodic tasks
CELERY_BEAT_SCHEDULE = {
    "publish-outbox-events": {
        "task": "kernel.publish_outbox_events",
        "schedule": 5.0,  # Every 5 seconds
        "kwargs": {"batch_size": 100},
    },
    "cleanup-dead-letter-events": {
        "task": "kernel.cleanup_dead_letter_events",
        "schedule": 86400.0,  # Daily (24 hours)
        "kwargs": {"days_old": 30},
    },
    "refresh-config-cache": {
        "task": "kernel.refresh_config_cache",
        "schedule": 300.0,  # Every 5 minutes
    },
}

# Logging — structured logging with correlation ID support
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} [{name}] {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "json": {
            "format": "{asctime} {levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "celery": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
