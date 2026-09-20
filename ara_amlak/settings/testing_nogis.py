"""
Minimal test settings for running tests without GDAL/PostGIS.
Used in CI and local environments without GIS libraries.
DB-requiring tests are skipped with pytest markers.
"""


SECRET_KEY = "test-secret-key-not-for-production"  # noqa: S105
DEBUG = True
FIELD_ENCRYPTION_KEY = "dGVzdC1rZXktMzItYnl0ZXMtcGFkZGluZy10ZXN0IQ=="

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
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

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
