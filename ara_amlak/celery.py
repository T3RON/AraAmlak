"""Celery application for Ara Amlak."""

from celery import Celery

app = Celery("ara_amlak")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
