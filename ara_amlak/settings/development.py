"""Development settings."""

from .base import *  # noqa: F401, F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Show emails in console during dev
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Debug toolbar
INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405
MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE  # noqa: F405
INTERNAL_IPS = ["127.0.0.1"]

# Simpler static storage in dev
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
