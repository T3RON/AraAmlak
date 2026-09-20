"""
Health check service for /health endpoint.

Checks: database, Redis, Celery.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def check_db() -> tuple[str, bool]:
    """Check PostgreSQL connection."""
    try:
        from django.db import connection

        connection.ensure_connection()
        return "ok", True
    except Exception as exc:
        logger.warning("Health check: DB failed: %s", exc)
        return f"error: {exc}", False


def check_redis() -> tuple[str, bool]:
    """Check Redis by set/get a sentinel key."""
    try:
        from django.core.cache import cache

        sentinel = "health:ping"
        cache.set(sentinel, "pong", timeout=5)
        result = cache.get(sentinel)
        if result == "pong":
            return "ok", True
        return "error: unexpected value", False
    except Exception as exc:
        logger.warning("Health check: Redis failed: %s", exc)
        return f"error: {exc}", False


def check_celery() -> tuple[str, bool]:
    """Check Celery worker availability with a 1s ping timeout."""
    try:
        from ara_amlak.celery import app as celery_app

        inspector = celery_app.control.inspect(timeout=1.0)
        pong = inspector.ping()
        if pong:
            return "ok", True
        return "error: no workers", False
    except Exception as exc:
        logger.warning("Health check: Celery failed: %s", exc)
        return f"error: {exc}", False


def get_health_status() -> tuple[dict, int]:
    """
    Run all health checks and return (payload, http_status).
    HTTP 200 if all ok, 503 if any fail.
    """
    db_status, db_ok = check_db()
    redis_status, redis_ok = check_redis()
    celery_status, celery_ok = check_celery()

    all_ok = db_ok and redis_ok and celery_ok
    payload = {
        "status": "ok" if all_ok else "degraded",
        "db": db_status,
        "redis": redis_status,
        "celery": celery_status,
    }
    http_status = 200 if all_ok else 503
    return payload, http_status
