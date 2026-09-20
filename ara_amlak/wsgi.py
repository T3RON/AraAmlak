"""WSGI config for Ara Amlak."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ara_amlak.settings.development")

application = get_wsgi_application()
