"""
Minimal test settings for running tests without GDAL/PostGIS.
Used in CI and local environments without GIS libraries.

Run tests with:
  pytest --ds=ara_amlak.settings.testing_nogis tests/test_listings_nogis.py ...
"""

SECRET_KEY = "test-secret-key-not-for-production"  # noqa: S105
DEBUG = True
# Valid 32-byte Fernet key for tests — not used in production
FIELD_ENCRYPTION_KEY = "_Rb6cmq4gjE2pZRi7BalzwZb49Amh9s0NGmxP0dbyW4="  # noqa: S105

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admin",
    # Project apps (no GIS)
    "apps.core",
    "apps.accounts",
    "apps.agencies",
    "apps.listings",
    "apps.crm",
    "apps.matching",
    "apps.messaging",
    "apps.ai",
    "apps.publishing",
    "apps.rendering",
    "apps.accounting",
    "apps.dashboard",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

USE_TZ = True
TIME_ZONE = "Asia/Tehran"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LANGUAGE_CODE = "fa"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

# Auth
AUTH_USER_MODEL = "accounts.CustomUser"

# Media (not needed in tests but avoids missing setting errors)
MEDIA_URL = "/media/"
MEDIA_ROOT = "test_media"  # noqa: S108

# Static (not needed in tests)
STATIC_URL = "/static/"

# Celery — run tasks synchronously in tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Redis mock for OTP tests
REDIS_URL = "redis://localhost:6379/1"

# URL configuration for view tests
ROOT_URLCONF = "ara_amlak.urls"

# Disable GIS requirement in agencies.Branch
# (Branch.location uses PointField which requires GDAL)
# The model is still importable; the PointField just won't work in SQLite
