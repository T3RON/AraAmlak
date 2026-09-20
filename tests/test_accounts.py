"""
Tests for CustomUser model and manager.
"""

import pytest

from apps.accounts.models import CustomUser, UserRole
from tests.factories import AgencyFactory, CustomUserFactory


@pytest.mark.django_db
class TestCustomUserManager:
    def test_create_user_sets_unusable_password(self):
        user = CustomUser.objects.create_user(phone="09400000001", full_name="تست کاربر")
        assert not user.has_usable_password()

    def test_create_superuser_has_password(self):
        user = CustomUser.objects.create_superuser(
            phone="09400000002", password="strongpass123", full_name="ادمین"  # noqa: S106
        )
        assert user.has_usable_password()
        assert user.is_staff
        assert user.is_superuser
        assert user.role == UserRole.SUPERADMIN

    def test_phone_normalization_plus98(self):
        from apps.accounts.models import CustomUserManager
        normalized = CustomUserManager._normalize_phone("+989123456789")
        assert normalized == "09123456789"

    def test_phone_normalization_country_code(self):
        from apps.accounts.models import CustomUserManager
        normalized = CustomUserManager._normalize_phone("989123456789")
        assert normalized == "09123456789"

    def test_superadmin_has_no_agency(self):
        user = CustomUser.objects.create_superuser(
            phone="09400000003", password="pass", full_name="ادمین"  # noqa: S106
        )
        assert user.agency is None

    def test_user_str(self):
        agency = AgencyFactory()
        user = CustomUserFactory(full_name="علی احمدی", agency=agency)
        assert "علی احمدی" in str(user)

    def test_get_short_name(self):
        user = CustomUserFactory(full_name="محمد رضایی")
        assert user.get_short_name() == "محمد"

    def test_get_short_name_no_name(self):
        user = CustomUserFactory(full_name="", phone="09500000001")
        assert user.get_short_name() == "09500000001"
