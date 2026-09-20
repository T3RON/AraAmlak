"""
Smoke tests for /health and homepage.
Run with: DJANGO_SETTINGS_MODULE=ara_amlak.settings.testing_nogis pytest tests/test_health.py
"""

import json

import pytest


@pytest.fixture(autouse=True)
def use_minimal_urlconf(settings):
    """Override ROOT_URLCONF to avoid GIS/admin import chain."""
    settings.ROOT_URLCONF = "tests.urls_health"


@pytest.mark.django_db
class TestHealthEndpoint:
    def test_health_returns_json(self, client):
        """GET /health/ returns JSON with expected keys."""
        response = client.get("/health/")
        assert response["Content-Type"] == "application/json"
        data = json.loads(response.content)
        assert "status" in data
        assert "db" in data
        assert "redis" in data
        assert "celery" in data

    def test_health_db_key_present(self, client):
        """DB key is always present in health response."""
        response = client.get("/health/")
        data = json.loads(response.content)
        assert data["db"] is not None

    def test_health_status_ok_or_degraded(self, client):
        """Status is either 'ok' or 'degraded'."""
        response = client.get("/health/")
        data = json.loads(response.content)
        assert data["status"] in ("ok", "degraded")

    def test_homepage_returns_200(self, client):
        """GET / returns 200 with RTL Farsi content."""
        response = client.get("/")
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "╪ت╪▒╪د ╪د┘à┘╪د┌ر" in content
        assert 'dir="rtl"' in content
        assert 'lang="fa"' in content
