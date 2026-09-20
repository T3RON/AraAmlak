"""Testing settings — in-memory DB, no migrations for speed."""

from .base import *  # noqa: F401, F403

DEBUG = True
SECRET_KEY = "test-secret-key-not-for-production"  # noqa: S105
# Valid 32-byte Fernet key for tests — not used in production
FIELD_ENCRYPTION_KEY = "_Rb6cmq4gjE2pZRi7BalzwZb49Amh9s0NGmxP0dbyW4="  # noqa: S105

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": "test_ara_amlak",
        "USER": "ara",
        "PASSWORD": "ara_secret",
        "HOST": "localhost",
        "PORT": "5432",
        "TEST": {"NAME": "test_ara_amlak"},
    }
}

# Use synchronous cache for tests
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Celery always eager in tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# No static file hashing
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
