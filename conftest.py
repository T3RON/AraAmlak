"""
Shared pytest fixtures for Ara Amlak test suite.

Imports that require GIS/PostGIS (CustomUser, Agency, etc.) are done lazily
inside fixtures so that no-GIS pure-unit tests can still run.
"""

import pytest


@pytest.fixture
def agency_a(db):
    from apps.agencies.models import Agency
    return Agency.objects.create(name="آژانس الف", slug="agency-a")


@pytest.fixture
def agency_b(db):
    from apps.agencies.models import Agency
    return Agency.objects.create(name="آژانس ب", slug="agency-b")


@pytest.fixture
def user_a(db, agency_a):
    from apps.accounts.models import CustomUser
    user = CustomUser.objects.create_user(phone="09111111111", full_name="کاربر الف")
    user.agency = agency_a
    user.save()
    return user


@pytest.fixture
def user_b(db, agency_b):
    from apps.accounts.models import CustomUser
    user = CustomUser.objects.create_user(phone="09222222222", full_name="کاربر ب")
    user.agency = agency_b
    user.save()
    return user


@pytest.fixture
def superadmin(db):
    from apps.accounts.models import CustomUser
    return CustomUser.objects.create_superuser(
        phone="09000000000",
        password="superadmin-pass",
        full_name="سوپرادمین",
    )
