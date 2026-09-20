"""
Local development settings — SQLite, no PostGIS, no external Celery.

Use this when Docker/PostgreSQL is not available.

    python manage.py runserver --settings=ara_amlak.settings.local_sqlite

or set in .env:
    DJANGO_SETTINGS_MODULE=ara_amlak.settings.local_sqlite
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = "local-dev-secret-key-not-for-production-use-only"  # noqa: S105
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # Third party
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "django_jalali",
    # Local apps
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

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.AgencyMiddleware",
]

ROOT_URLCONF = "ara_amlak.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.ui_context",
            ],
        },
    },
]

WSGI_APPLICATION = "ara_amlak.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db_local.sqlite3",
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

AUTH_USER_MODEL = "accounts.CustomUser"

LANGUAGE_CODE = "fa"
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Fernet key for EncryptedCharField — valid 32-byte key for local dev
FIELD_ENCRYPTION_KEY = "_Rb6cmq4gjE2pZRi7BalzwZb49Amh9s0NGmxP0dbyW4="  # noqa: S105

# Celery — run tasks synchronously (no broker needed)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Redis for OTP — fallback to dummy cache if Redis unavailable
REDIS_URL = "redis://localhost:6379/0"

# OTP settings
OTP_TTL_SECONDS = 120
OTP_MAX_ATTEMPTS = 5
OTP_CODE_LENGTH = 6

# Login URL
LOGIN_URL = "/auth/login/"
LOGIN_REDIRECT_URL = "/"

# DRF
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Ara Amlak API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "apps.accounts.otp": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}
