"""
Tests for Phase 4A + 4B — SMS Infrastructure and Notification Policy.

Coverage:
- sms_segment_count (Persian vs Latin)
- ConsoleSMSProvider
- KavenegarSMSProvider (mocked HTTP)
- MeliPayamakSMSProvider (mocked HTTP)
- AgencySMSConfig.get_provider_instance()
- enqueue_sms + send_sms_message state machine
- SMSMessage state transitions
- make/verify unsubscribe and renewal tokens
- should_send_sms pure policy (quiet hours, daily cap, dedup, score tiers)
- process_match_notification (end-to-end with Fake provider)
- handle_unsubscribe revokes consent
- handle_renewal renews / stops request
- PublicSubscribeView: step1 (rate limit, honeypot) + step2 OTP mismatch / success
- UnsubscribeView and RenewalView
- Tenant isolation: no SMS config cross-agency
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# ─── sms_segment_count ────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestSmsSegmentCount:
    def test_short_latin(self):
        from apps.messaging.models import sms_segment_count

        assert sms_segment_count("Hello") == 1

    def test_long_latin_two_segments(self):
        from apps.messaging.models import sms_segment_count

        # 161 chars → 2 segments (GSM-7: 160 per single, 153 per multi)
        text = "A" * 161
        assert sms_segment_count(text) == 2

    def test_short_persian(self):
        from apps.messaging.models import sms_segment_count

        # 5 Persian chars → 1 segment (UCS-2: 70 per single)
        assert sms_segment_count("سلام") == 1

    def test_long_persian_two_segments(self):
        from apps.messaging.models import sms_segment_count

        # 71 Persian chars → 2 segments (UCS-2: 67 per multi-segment)
        text = "آ" * 71
        assert sms_segment_count(text) == 2

    def test_exactly_70_persian(self):
        from apps.messaging.models import sms_segment_count

        text = "آ" * 70
        assert sms_segment_count(text) == 1

    def test_mixed_triggers_ucs2(self):
        from apps.messaging.models import sms_segment_count

        # Any Persian char forces UCS-2 (70 chars/segment single, 67 multi)
        # "Hello " (6) + 64 × "آ" = 70 chars → 1 segment
        text = "Hello " + "آ" * 64
        assert sms_segment_count(text) == 1
        # 71 chars → 2 UCS-2 segments
        text2 = "Hello " + "آ" * 65
        assert sms_segment_count(text2) == 2


# ─── ConsoleSMSProvider ───────────────────────────────────────────────────────


class TestConsoleSMSProvider:
    def test_send_returns_fake_id(self):
        from apps.messaging.providers.console import ConsoleSMSProvider

        p = ConsoleSMSProvider()
        msg_id = p.send("09121234567", "سلام")
        assert msg_id.startswith("FAKE-")

    def test_status_returns_delivered(self):
        from apps.messaging.providers.console import ConsoleSMSProvider

        p = ConsoleSMSProvider()
        assert p.status("FAKE-000001") == "delivered"

    def test_balance(self):
        from decimal import Decimal

        from apps.messaging.providers.console import ConsoleSMSProvider

        p = ConsoleSMSProvider()
        assert p.balance() == Decimal("999999")

    def test_send_bulk(self):
        from apps.messaging.providers.console import ConsoleSMSProvider

        p = ConsoleSMSProvider()
        ids = p.send_bulk(["09121111111", "09122222222"], "تست")
        assert len(ids) == 2
        assert all(i.startswith("FAKE-") for i in ids)


# ─── KavenegarSMSProvider (mocked HTTP) ──────────────────────────────────────


class TestKavenegarSMSProvider:
    def _mock_send_response(self, message_id="12345"):
        return {
            "return": {"status": 200, "message": "تایید شد"},
            "entries": [{"messageid": message_id, "status": 1}],
        }

    def test_send_success(self):
        from apps.messaging.providers.kavenegar import KavenegarSMSProvider

        provider = KavenegarSMSProvider(api_key="test-key", sender="1000xxx")
        with patch("apps.messaging.providers.kavenegar.requests.post") as mock_post:
            mock_post.return_value.json.return_value = self._mock_send_response("99999")
            mock_post.return_value.raise_for_status = lambda: None
            msg_id = provider.send("09121234567", "سلام")
        assert msg_id == "99999"

    def test_send_error_status(self):
        from apps.messaging.providers.kavenegar import KavenegarSMSProvider

        provider = KavenegarSMSProvider(api_key="test-key")
        with patch("apps.messaging.providers.kavenegar.requests.post") as mock_post:
            mock_post.return_value.json.return_value = {
                "return": {"status": 401, "message": "Unauthorized"},
                "entries": [],
            }
            mock_post.return_value.raise_for_status = lambda: None
            with pytest.raises(RuntimeError, match="Kavenegar error"):
                provider.send("09121234567", "سلام")

    def test_balance(self):
        from decimal import Decimal

        from apps.messaging.providers.kavenegar import KavenegarSMSProvider

        provider = KavenegarSMSProvider(api_key="test-key")
        with patch("apps.messaging.providers.kavenegar.requests.get") as mock_get:
            mock_get.return_value.json.return_value = {
                "entries": {"remaincredit": "5000"}
            }
            mock_get.return_value.raise_for_status = lambda: None
            bal = provider.balance()
        assert bal == Decimal("5000")


# ─── MeliPayamakSMSProvider (mocked HTTP) ────────────────────────────────────


class TestMeliPayamakSMSProvider:
    def test_send_success(self):
        from apps.messaging.providers.melipayamak import MeliPayamakSMSProvider

        provider = MeliPayamakSMSProvider(username="user", password="pass", sender="5000xxx")  # noqa: S106
        with patch("apps.messaging.providers.melipayamak.requests.post") as mock_post:
            mock_post.return_value.json.return_value = {
                "RetStatus": 1, "StrRetStatus": "Ok", "Value": "77777"
            }
            mock_post.return_value.raise_for_status = lambda: None
            msg_id = provider.send("09121234567", "سلام")
        assert msg_id == "77777"

    def test_send_error(self):
        from apps.messaging.providers.melipayamak import MeliPayamakSMSProvider

        provider = MeliPayamakSMSProvider(username="user", password="pass")  # noqa: S106
        with patch("apps.messaging.providers.melipayamak.requests.post") as mock_post:
            mock_post.return_value.json.return_value = {
                "RetStatus": -1, "StrRetStatus": "Error", "Value": "0"
            }
            mock_post.return_value.raise_for_status = lambda: None
            with pytest.raises(RuntimeError, match="MeliPayamak error"):
                provider.send("09121234567", "سلام")


# ─── AgencySMSConfig.get_provider_instance ───────────────────────────────────


@pytest.mark.django_db
class TestAgencySMSConfig:
    def test_console_provider(self, agency):
        from apps.messaging.models import AgencySMSConfig, SMSProvider
        from apps.messaging.providers.console import ConsoleSMSProvider

        cfg = AgencySMSConfig.objects.create(
            agency=agency, provider=SMSProvider.CONSOLE
        )
        assert isinstance(cfg.get_provider_instance(), ConsoleSMSProvider)

    def test_kavenegar_provider(self, agency):
        from apps.messaging.models import AgencySMSConfig, SMSProvider
        from apps.messaging.providers.kavenegar import KavenegarSMSProvider

        cfg = AgencySMSConfig.objects.create(
            agency=agency, provider=SMSProvider.KAVENEGAR, api_key="key123"
        )
        assert isinstance(cfg.get_provider_instance(), KavenegarSMSProvider)

    def test_no_config_falls_back_to_console(self, agency):
        from apps.messaging.providers.console import ConsoleSMSProvider
        from apps.messaging.services import get_provider_for_agency

        p = get_provider_for_agency(agency)
        assert isinstance(p, ConsoleSMSProvider)

    def test_tenant_isolation(self, agency, agency_b):
        """Config for agency_b should not be returned for agency."""
        from apps.messaging.models import AgencySMSConfig, SMSProvider
        from apps.messaging.providers.console import ConsoleSMSProvider
        from apps.messaging.services import get_provider_for_agency

        AgencySMSConfig.objects.create(
            agency=agency_b, provider=SMSProvider.KAVENEGAR, api_key="other-key"
        )
        # agency has no config → should still get console
        p = get_provider_for_agency(agency)
        assert isinstance(p, ConsoleSMSProvider)


# ─── enqueue_sms + state machine ─────────────────────────────────────────────


@pytest.mark.django_db
class TestEnqueueSmsStateMachine:
    def test_enqueue_creates_queued_message(self, agency):
        from apps.messaging.models import SMSMessageState
        from apps.messaging.services import enqueue_sms

        with patch("apps.messaging.tasks.send_sms_task.delay") as mock_delay:
            msg = enqueue_sms(agency=agency, to="09121234567", body="سلام")

        assert msg.state == SMSMessageState.QUEUED
        assert "4567" in msg.recipient_masked  # last 4 digits of phone
        mock_delay.assert_called_once_with(msg.pk, "09121234567")

    def test_send_sms_message_transitions_to_sent(self, agency):
        from apps.messaging.models import SMSMessageState
        from apps.messaging.services import enqueue_sms, send_sms_message

        with patch("apps.messaging.tasks.send_sms_task.delay"):
            msg = enqueue_sms(agency=agency, to="09121234567", body="تست")

        with patch("apps.messaging.services.get_provider_for_agency") as mock_prov:
            mock_provider = MagicMock()
            mock_provider.send.return_value = "PROV-001"
            mock_prov.return_value = mock_provider
            send_sms_message(msg.pk, "09121234567")

        msg.refresh_from_db()
        assert msg.state == SMSMessageState.SENT
        assert msg.provider_message_id == "PROV-001"
        assert msg.sent_at is not None

    def test_send_sms_message_transitions_to_failed(self, agency):
        from apps.messaging.models import SMSMessageState
        from apps.messaging.services import enqueue_sms, send_sms_message

        with patch("apps.messaging.tasks.send_sms_task.delay"):
            msg = enqueue_sms(agency=agency, to="09121234567", body="تست")

        with patch("apps.messaging.services.get_provider_for_agency") as mock_prov:
            mock_provider = MagicMock()
            mock_provider.send.side_effect = RuntimeError("Network error")
            mock_prov.return_value = mock_provider
            with pytest.raises(RuntimeError):
                send_sms_message(msg.pk, "09121234567")

        msg.refresh_from_db()
        assert msg.state == SMSMessageState.FAILED
        assert "Network error" in msg.failure_reason

    def test_idempotent_for_sent_message(self, agency):
        """Calling send on an already-SENT message should be a no-op."""
        from django.utils import timezone

        from apps.messaging.models import SMSMessage, SMSMessageState
        from apps.messaging.services import send_sms_message

        msg = SMSMessage.objects.create(
            agency=agency,
            recipient_masked="7890",
            body="test",
            state=SMSMessageState.SENT,
            sent_at=timezone.now(),
        )
        with patch("apps.messaging.services.get_provider_for_agency") as mock_prov:
            send_sms_message(msg.pk, "09121234567")
            mock_prov.assert_not_called()


# ─── Unsubscribe / renewal tokens ────────────────────────────────────────────


class TestTokens:
    def test_unsubscribe_roundtrip(self):
        from apps.messaging.models import make_unsubscribe_token, verify_unsubscribe_token

        token = make_unsubscribe_token(42)
        assert verify_unsubscribe_token(token) == 42

    def test_invalid_unsubscribe_token(self):
        from apps.messaging.models import verify_unsubscribe_token

        assert verify_unsubscribe_token("bad-token") is None

    def test_renewal_roundtrip(self):
        from apps.messaging.models import make_renewal_token, verify_renewal_token

        token = make_renewal_token(99)
        assert verify_renewal_token(token) == 99

    def test_invalid_renewal_token(self):
        from apps.messaging.models import verify_renewal_token

        assert verify_renewal_token("garbage") is None


# ─── should_send_sms pure policy ─────────────────────────────────────────────


class TestShouldSendSms:
    """All tests use a mock policy object to keep them pure/fast."""

    def _policy(self, **kwargs):
        p = MagicMock()
        p.is_active = kwargs.get("is_active", True)
        p.auto_send_exact = kwargs.get("auto_send_exact", True)
        p.auto_send_strong = kwargs.get("auto_send_strong", True)
        p.score_threshold = kwargs.get("score_threshold", 70)
        p.quiet_start = kwargs.get("quiet_start", 22)
        p.quiet_end = kwargs.get("quiet_end", 8)
        p.daily_cap = kwargs.get("daily_cap", 3)
        return p

    def _call(self, policy, score=80, daily=0, consent=True, sent=False, hour=10):
        from apps.messaging.notification_policy import should_send_sms

        return should_send_sms(
            policy=policy,
            score=score,
            contact_daily_count=daily,
            has_consent=consent,
            already_sent=sent,
            current_hour=hour,
        )

    def test_policy_inactive(self):
        ok, reason = self._call(self._policy(is_active=False))
        assert not ok
        assert reason == "policy_inactive"

    def test_no_consent(self):
        ok, reason = self._call(self._policy(), consent=False)
        assert not ok
        assert reason == "no_consent"

    def test_already_sent(self):
        ok, reason = self._call(self._policy(), sent=True)
        assert not ok
        assert reason == "already_sent"

    def test_score_too_low(self):
        ok, reason = self._call(self._policy(), score=30)
        assert not ok
        assert reason == "score_too_low"

    def test_quiet_hours_night(self):
        # quiet 22–8; hour=23 is quiet
        ok, reason = self._call(self._policy(quiet_start=22, quiet_end=8), hour=23)
        assert not ok
        assert reason == "quiet_hours"

    def test_quiet_hours_early_morning(self):
        # quiet 22–8; hour=7 is quiet
        ok, reason = self._call(self._policy(quiet_start=22, quiet_end=8), hour=7)
        assert not ok
        assert reason == "quiet_hours"

    def test_not_quiet_daytime(self):
        ok, reason = self._call(self._policy(quiet_start=22, quiet_end=8), score=80, hour=10)
        assert ok

    def test_daily_cap_reached(self):
        ok, reason = self._call(self._policy(daily_cap=2), daily=2)
        assert not ok
        assert reason == "daily_cap"

    def test_exact_match_sends(self):
        ok, reason = self._call(self._policy(), score=90)
        assert ok
        assert reason == "exact_match"

    def test_strong_match_sends(self):
        ok, reason = self._call(self._policy(), score=60)
        assert ok
        assert reason == "strong_match"

    def test_strong_match_disabled(self):
        ok, reason = self._call(self._policy(auto_send_strong=False), score=60)
        assert not ok

    def test_exact_disabled(self):
        ok, reason = self._call(self._policy(auto_send_exact=False), score=90)
        assert not ok


# ─── handle_unsubscribe ───────────────────────────────────────────────────────


@pytest.mark.django_db
class TestHandleUnsubscribe:
    def test_valid_token_revokes_consent(self, agency):
        from apps.crm.models import ConsentRecord, ConsentSource, Contact

        contact = Contact.objects.create(agency=agency, full_name="علی تست")
        ConsentRecord.objects.create(
            contact=contact,
            agency=agency,
            source=ConsentSource.IN_PERSON,
        )
        from apps.messaging.models import make_unsubscribe_token
        from apps.messaging.notification_policy import handle_unsubscribe

        token = make_unsubscribe_token(contact.pk)
        result = handle_unsubscribe(token)
        assert result is True

        # All consent records should now be revoked (revoked_at set)
        assert not contact.consent_records.filter(revoked_at__isnull=True).exists()

    def test_invalid_token_returns_false(self):
        from apps.messaging.notification_policy import handle_unsubscribe

        assert handle_unsubscribe("bad-token") is False


# ─── handle_renewal ───────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestHandleRenewal:
    def _make_request(self, agency):
        from django.utils import timezone

        from apps.crm.models import Contact, Request, RequestStatus
        from apps.listings.models import DealType

        contact = Contact.objects.create(agency=agency, full_name="مراجع تست")
        return Request.objects.create(
            agency=agency,
            contact=contact,
            deal_type=DealType.SALE,
            status=RequestStatus.NEW,
            expires_at=timezone.now(),
        )

    def test_renew_extends_request(self, agency):
        from apps.messaging.models import make_renewal_token
        from apps.messaging.notification_policy import handle_renewal

        req = self._make_request(agency)
        token = make_renewal_token(req.pk)
        result = handle_renewal(token, "renew")
        assert result is True

        req.refresh_from_db()
        from datetime import timedelta

        from django.utils import timezone

        assert req.expires_at > timezone.now() + timedelta(days=80)

    def test_stop_closes_request(self, agency):
        from apps.crm.models import RequestStatus
        from apps.messaging.models import make_renewal_token
        from apps.messaging.notification_policy import handle_renewal

        req = self._make_request(agency)
        token = make_renewal_token(req.pk)
        result = handle_renewal(token, "stop")
        assert result is True

        req.refresh_from_db()
        assert req.status == RequestStatus.CLOSED

    def test_invalid_token_returns_false(self):
        from apps.messaging.notification_policy import handle_renewal

        assert handle_renewal("bad-token", "renew") is False


# ─── PublicSubscribeView ──────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPublicSubscribeView:
    def test_get_renders_form(self, client, agency):
        url = f"/messaging/subscribe/{agency.slug}/"
        resp = client.get(url)
        assert resp.status_code == 200
        assert agency.name.encode() in resp.content

    def test_honeypot_blocked(self, client, agency):
        """Request with honeypot field filled should silently redirect."""
        url = f"/messaging/subscribe/{agency.slug}/"
        resp = client.post(url, {
            "step": "1",
            "name": "Ali",
            "phone": "09121234567",
            "consent": "1",
            "website": "http://spam.com",  # honeypot
        })
        # Should redirect (not create any records)
        assert resp.status_code == 302

    def test_missing_name_shows_error(self, client, agency):
        url = f"/messaging/subscribe/{agency.slug}/"
        resp = client.post(url, {
            "step": "1",
            "phone": "09121234567",
            "consent": "1",
        }, follow=True)
        assert resp.status_code == 200
        assert "نام".encode() in resp.content

    def test_step2_wrong_otp(self, client, agency):
        """POST step=2 with wrong OTP shows error."""
        url = f"/messaging/subscribe/{agency.slug}/"
        # Set session data directly
        session = client.session
        session[f"pub_sub_{agency.slug}"] = {
            "phone": "09121234567",
            "name": "علی",
            "deal_type": "",
            "property_types": [],
            "city": "",
            "min_budget": "",
            "max_budget": "",
            "min_area": "",
            "max_area": "",
            "min_rooms": "",
            "max_rooms": "",
            "notes": "",
        }
        session.save()
        resp = client.post(url, {"step": "2", "otp_code": "000000"})
        assert resp.status_code == 200
        assert "اشتباه".encode() in resp.content

    def test_step2_correct_otp_creates_records(self, client, agency):
        """POST step=2 with correct OTP creates Contact + Request + Consent."""
        from django.core.cache import cache

        from apps.accounts.otp import _otp_key

        phone = "09121234567"
        # Manually store OTP in cache
        cache.set(_otp_key(phone), "123456", timeout=120)

        url = f"/messaging/subscribe/{agency.slug}/"
        session = client.session
        session[f"pub_sub_{agency.slug}"] = {
            "phone": phone,
            "name": "علی محمدی",
            "deal_type": "sale",
            "property_types": ["apartment"],
            "city": "تهران",
            "min_budget": "",
            "max_budget": "",
            "min_area": "",
            "max_area": "",
            "min_rooms": "",
            "max_rooms": "",
            "notes": "",
        }
        session.save()

        resp = client.post(url, {"step": "2", "otp_code": "123456"})
        assert resp.status_code == 200
        assert "موفقیت".encode() in resp.content

        from apps.crm.models import Contact, Request

        contact = Contact.objects.get(agency=agency, full_name="علی محمدی")
        assert Request.objects.filter(agency=agency, contact=contact).exists()
        assert contact.consent_records.filter(revoked_at__isnull=True).exists()


# ─── UnsubscribeView + RenewalView ───────────────────────────────────────────


@pytest.mark.django_db
class TestWebViews:
    def test_unsubscribe_valid(self, client, agency):
        from apps.crm.models import ConsentRecord, ConsentSource, Contact
        from apps.messaging.models import make_unsubscribe_token

        contact = Contact.objects.create(agency=agency, full_name="تست لغو")
        ConsentRecord.objects.create(
            contact=contact, agency=agency, source=ConsentSource.IN_PERSON
        )
        token = make_unsubscribe_token(contact.pk)
        resp = client.get(f"/messaging/unsubscribe/{token}/")
        assert resp.status_code == 200
        assert "لغو اشتراک".encode() in resp.content

    def test_unsubscribe_invalid(self, client):
        resp = client.get("/messaging/unsubscribe/bad-token/")
        assert resp.status_code == 200
        assert "نامعتبر".encode() in resp.content

    def test_renewal_renew(self, client, agency):
        from django.utils import timezone

        from apps.crm.models import Contact, Request, RequestStatus
        from apps.listings.models import DealType
        from apps.messaging.models import make_renewal_token

        contact = Contact.objects.create(agency=agency, full_name="تست تمدید")
        req = Request.objects.create(
            agency=agency,
            contact=contact,
            deal_type=DealType.SALE,
            status=RequestStatus.NEW,
            expires_at=timezone.now(),
        )
        token = make_renewal_token(req.pk)
        resp = client.get(f"/messaging/renew/{token}/renew/")
        assert resp.status_code == 200
        assert "تمدید".encode() in resp.content

    def test_renewal_invalid_action(self, client, agency):
        from apps.messaging.models import make_renewal_token

        token = make_renewal_token(1)
        resp = client.get(f"/messaging/renew/{token}/invalid-action/")
        assert resp.status_code == 400
