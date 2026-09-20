"""
Minimal test settings for running tests without GDAL/PostGIS.
Used in CI and local environments without GIS libraries.
DB-requiring tests (GIS models) run in Docker with testing.py.
"""

SECRET_KEY = "test-secret-key-not-for-production"  # noqa: S105
DEBUG = True
FIELD_ENCRYPTION_KEY = "dGVzdC1rZXktMzItYnl0ZXMtcGFkZGluZy10ZXN0IQ=="

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.staticfiles",
    "apps.core",
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

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Required for view tests
ROOT_URLCONF = "ara_amlak.urls"

from pathlib import Path  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent.parent.parent

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.static",
            ],
        },
    },
]

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Suppress GDAL-requiring apps by keeping INSTALLED_APPS minimal
# Apps that import from django.contrib.gis are NOT included here
