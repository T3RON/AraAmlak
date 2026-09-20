"""
OTP service tests — send, verify, expiry, max attempts.

No real phone numbers or real SMS are used in these tests.
"""

import pytest
from django.core.cache import cache

from apps.accounts.otp import generate_otp, verify_otp


@pytest.mark.django_db
class TestOTPGeneration:
    def test_otp_length_default(self):
        code = generate_otp()
        assert len(code) == 6

    def test_otp_is_numeric(self):
        code = generate_otp()
        assert code.isdigit()

    def test_otp_codes_are_different(self):
        """Statistical test: 100 codes should not all be the same."""
        codes = {generate_otp() for _ in range(100)}
        assert len(codes) > 1


@pytest.mark.django_db
class TestOTPVerify:
    def setup_method(self):
        cache.clear()

    def test_correct_code_returns_true(self, settings):
        settings.OTP_TTL_SECONDS = 120
        settings.OTP_MAX_ATTEMPTS = 5
        phone = "09300000001"
        # Manually inject the code into cache for testing
        from apps.core.currency import to_persian_digits  # noqa: F401
        cache.set(f"otp:{phone}", "123456", timeout=120)
        assert verify_otp(phone, "123456") is True

    def test_wrong_code_returns_false(self, settings):
        settings.OTP_TTL_SECONDS = 120
        settings.OTP_MAX_ATTEMPTS = 5
        phone = "09300000002"
        cache.set(f"otp:{phone}", "111111", timeout=120)
        assert verify_otp(phone, "999999") is False

    def test_expired_code_returns_false(self):
        """No code in cache → expired/never sent."""
        phone = "09300000003"
        cache.delete(f"otp:{phone}")
        assert verify_otp(phone, "123456") is False

    def test_code_consumed_after_success(self, settings):
        settings.OTP_TTL_SECONDS = 120
        settings.OTP_MAX_ATTEMPTS = 5
        phone = "09300000004"
        cache.set(f"otp:{phone}", "654321", timeout=120)
        assert verify_otp(phone, "654321") is True
        # Second attempt with same code should fail (consumed)
        assert verify_otp(phone, "654321") is False

    def test_max_attempts_locks_out(self, settings):
        settings.OTP_TTL_SECONDS = 120
        settings.OTP_MAX_ATTEMPTS = 3
        phone = "09300000005"
        cache.set(f"otp:{phone}", "777777", timeout=120)
        # 3 wrong attempts
        for _ in range(3):
            verify_otp(phone, "000000")
        # Even correct code should fail now
        assert verify_otp(phone, "777777") is False

    def test_correct_code_clears_attempt_counter(self, settings):
        settings.OTP_TTL_SECONDS = 120
        settings.OTP_MAX_ATTEMPTS = 5
        phone = "09300000006"
        cache.set(f"otp:{phone}", "888888", timeout=120)
        verify_otp(phone, "000000")  # 1 wrong attempt
        assert verify_otp(phone, "888888") is True  # correct — should still work
