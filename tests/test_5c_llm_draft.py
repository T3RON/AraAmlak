"""
Tests for Phase 5C — LLM draft extraction (Gemini structured output).

All HTTP mocked — no real network calls.
Coverage:
- RegexPersianDraftProvider wraps the parser
- GeminiDraftProvider request shape (URL / headers / response_format schema)
- Response normalisation: whitelist, int coercion, enum validation,
  Jalali build year → Gregorian, junk removal, sanity guards
- Failure paths (no output_text / invalid JSON / HTTP error)
- get_draft_provider_for_agency selection (gemini+key / gemini-no-key / none)
- extract_draft stores parser name from provider
- extract_draft_task dispatch
- Views: async path (202 pending + task dispatch), draft_status polling,
  sync path unchanged
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from apps.ai.providers.gemini_draft import GeminiDraftProvider, _normalize
from apps.ai.providers.regex_draft import RegexPersianDraftProvider

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _gemini_resp(output_text: str):
    resp = MagicMock()
    resp.ok = True
    resp.raise_for_status = lambda: None
    resp.json.return_value = {"output_text": output_text}
    return resp


def _transcribed_note(agency, user, transcript="آپارتمان هشتاد متر دو خواب"):
    from tests.test_5b_smart_draft import _make_voice_note

    return _make_voice_note(agency, user, transcript)


# ─── Regex provider ───────────────────────────────────────────────────────────


class TestRegexProvider:
    def test_wraps_parser(self):
        result = RegexPersianDraftProvider().extract("هشتاد متر دو خواب")
        assert result["data"]["area"] == 80
        assert result["data"]["rooms"] == 2
        assert "sale_price" in result["missing"]

    def test_metadata(self):
        provider = RegexPersianDraftProvider()
        assert provider.name == "regex_fa"
        assert provider.is_async is False


# ─── Normalisation ────────────────────────────────────────────────────────────


class TestNormalize:
    def test_keeps_valid_fields_and_coerces_ints(self):
        data = _normalize(
            {"area": "80", "rooms": 2.0, "sale_price": "2700000000", "title": "آپارتمان"}
        )
        assert data["area"] == 80
        assert data["rooms"] == 2
        assert data["sale_price"] == 2_700_000_000
        assert data["title"] == "آپارتمان"

    def test_drops_junk_and_unknown_fields(self):
        data = _normalize({"hacker": "x", "name": "y", "area": 80})
        assert "hacker" not in data and "name" not in data
        assert data["area"] == 80

    def test_enum_validation(self):
        data = _normalize({"deal_type": "sale", "property_type": "castle", "direction": "north"})
        assert data["deal_type"] == "sale"  # valid kept
        assert "property_type" not in data  # invalid dropped
        assert data["direction"] == "north"

    def test_jalali_build_year_converted(self):
        assert _normalize({"build_year": 1390})["build_year"] == 2011
        assert _normalize({"build_year": 90})["build_year"] == 2011
        assert _normalize({"build_year": 2011})["build_year"] == 2011  # Gregorian passthrough

    def test_invalid_build_year_dropped(self):
        assert "build_year" not in _normalize({"build_year": 1700})

    def test_booleans_coerced(self):
        data = _normalize({"parking": True, "elevator": 1})
        assert data["parking"] is True
        assert data["elevator"] is True

    def test_sanity_guards(self):
        assert "area" not in _normalize({"area": -5})
        assert "area" not in _normalize({"area": 0})
        assert "sale_price" not in _normalize({"sale_price": -100})

    def test_nulls_skipped(self):
        assert _normalize({"area": None, "parking": None, "rooms": 2}) == {"rooms": 2}


# ─── GeminiDraftProvider (mocked HTTP) ────────────────────────────────────────


class TestGeminiDraftProvider:
    def test_metadata(self):
        provider = GeminiDraftProvider(api_key="g-key")
        assert provider.name == "gemini"
        assert provider.is_async is True

    def test_request_shape_and_success(self):
        provider = GeminiDraftProvider(api_key="g-key", model="gemini-2.0-flash")
        llm_json = json.dumps(
            {
                "area": 80,
                "rooms": 2,
                "deal_type": "sale",
                "sale_price": 2_700_000_000,
                "build_year": 1390,
                "parking": True,
                "direction": "north",
                "district": "سعادت‌آباد",
            }
        )

        with patch(
            "apps.ai.providers.gemini_draft.requests.post",
            return_value=_gemini_resp(llm_json),
        ) as mp:
            result = provider.extract("رونویسی تست")

        _, kwargs = mp.call_args
        assert kwargs["headers"]["x-goog-api-key"] == "g-key"
        body = json.loads(kwargs["data"])
        assert body["model"] == "gemini-2.0-flash"
        assert "interactions" in mp.call_args[0][0]
        rf = body["response_format"]
        assert rf["type"] == "text"
        assert rf["mime_type"] == "application/json"
        assert "properties" in rf["schema"]

        assert result["data"]["area"] == 80
        assert result["data"]["sale_price"] == 2_700_000_000
        assert result["data"]["build_year"] == 2011  # 1390 → Gregorian
        assert result["data"]["parking"] is True
        assert result["missing"] == []

    def test_no_output_text_raises(self):
        provider = GeminiDraftProvider(api_key="g-key")
        resp = MagicMock()
        resp.raise_for_status = lambda: None
        resp.json.return_value = {"output": []}
        with patch("apps.ai.providers.gemini_draft.requests.post", return_value=resp):
            with pytest.raises(RuntimeError, match="output_text"):
                provider.extract("متن")

    def test_invalid_json_raises(self):
        provider = GeminiDraftProvider(api_key="g-key")
        with patch(
            "apps.ai.providers.gemini_draft.requests.post",
            return_value=_gemini_resp("not json {"),
        ):
            with pytest.raises(RuntimeError, match="valid JSON"):
                provider.extract("متن")

    def test_http_error_raises(self):
        provider = GeminiDraftProvider(api_key="g-key")
        resp = MagicMock()
        resp.raise_for_status.side_effect = RuntimeError("HTTP 429")
        with patch("apps.ai.providers.gemini_draft.requests.post", return_value=resp):
            with pytest.raises(RuntimeError, match="429"):
                provider.extract("متن")


# ─── Provider selection ───────────────────────────────────────────────────────


@pytest.mark.django_db
class TestProviderSelection:
    def test_no_config_returns_regex(self, agency):
        from apps.ai.services import get_draft_provider_for_agency

        provider = get_draft_provider_for_agency(agency)
        assert isinstance(provider, RegexPersianDraftProvider)
        assert provider.is_async is False

    def test_gemini_config_with_key(self, agency):
        from apps.ai.models import AgencyAIConfig, AIProvider
        from apps.ai.services import get_draft_provider_for_agency

        AgencyAIConfig.objects.create(
            agency=agency, provider=AIProvider.GEMINI, api_key="g-live"
        )
        provider = get_draft_provider_for_agency(agency)
        assert isinstance(provider, GeminiDraftProvider)
        assert provider._api_key == "g-live"

    def test_gemini_config_without_key_falls_back(self, agency):
        from apps.ai.models import AgencyAIConfig, AIProvider
        from apps.ai.services import get_draft_provider_for_agency

        AgencyAIConfig.objects.create(agency=agency, provider=AIProvider.GEMINI, api_key="")
        assert isinstance(get_draft_provider_for_agency(agency), RegexPersianDraftProvider)

    def test_openai_config_still_uses_regex_for_drafts(self, agency):
        """Only Gemini is wired for drafts — OpenAI stays transcription-only."""
        from apps.ai.models import AgencyAIConfig, AIProvider
        from apps.ai.services import get_draft_provider_for_agency

        AgencyAIConfig.objects.create(
            agency=agency, provider=AIProvider.OPENAI, api_key="sk-x"
        )
        assert isinstance(get_draft_provider_for_agency(agency), RegexPersianDraftProvider)


# ─── extract_draft with provider ──────────────────────────────────────────────


@pytest.mark.django_db
class TestExtractDraftWithProvider:
    def test_parser_name_from_provider(self, agency, user):
        from apps.ai.services import extract_draft

        note = _transcribed_note(agency, user)
        draft = extract_draft(note, RegexPersianDraftProvider())
        assert draft.parser == "regex_fa"

    def test_gemini_provider_stores_llm_data(self, agency, user):
        from apps.ai.services import extract_draft

        note = _transcribed_note(agency, user, "توضیحات آپارتمان")
        provider = GeminiDraftProvider(api_key="g-key")
        llm_json = json.dumps(
            {"area": 80, "rooms": 2, "deal_type": "sale", "sale_price": 3_000_000_000}
        )
        with patch(
            "apps.ai.providers.gemini_draft.requests.post",
            return_value=_gemini_resp(llm_json),
        ):
            draft = extract_draft(note, provider)

        assert draft.parser == "gemini"
        assert draft.data["sale_price"] == 3_000_000_000


# ─── Celery task ──────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestExtractDraftTask:
    def test_task_calls_service(self, agency, user):
        from apps.ai.tasks import extract_draft_task

        note = _transcribed_note(agency, user)
        with patch("apps.ai.services.extract_draft") as mock_extract:
            extract_draft_task.apply(args=[note.pk])
        mock_extract.assert_called_once()


# ─── Views ────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestDraftViews:
    def test_sync_path_immediate_fields(self, client, user, agency):
        note = _transcribed_note(agency, user)
        client.force_login(user)
        resp = client.post(f"/ai/voice/{note.pk}/draft/")
        assert resp.status_code == 200
        assert "پیش‌نویس فایل" in resp.content.decode()

    def test_async_path_returns_pending_and_dispatches(self, client, user, agency):
        from apps.ai.models import AgencyAIConfig, AIProvider

        AgencyAIConfig.objects.create(
            agency=agency, provider=AIProvider.GEMINI, api_key="g-live"
        )
        note = _transcribed_note(agency, user)
        client.force_login(user)
        with patch("apps.ai.tasks.extract_draft_task.delay") as mock_delay:
            resp = client.post(f"/ai/voice/{note.pk}/draft/")
        assert resp.status_code == 202
        assert "در حال استخراج" in resp.content.decode()
        mock_delay.assert_called_once_with(note.pk)

    def test_draft_status_pending_then_fields(self, client, user, agency):
        from apps.ai.models import VoiceDraft

        note = _transcribed_note(agency, user)
        client.force_login(user)

        resp = client.get(f"/ai/voice/{note.pk}/draft/status/")
        assert resp.status_code == 202
        assert "در حال استخراج" in resp.content.decode()

        VoiceDraft.objects.create(
            agency=agency,
            voice_note=note,
            data={"area": 80},
            missing=[],
            confidence=0.2,
            parser="regex_fa",
        )
        resp = client.get(f"/ai/voice/{note.pk}/draft/status/")
        assert resp.status_code == 200
        assert "پیش‌نویس فایل" in resp.content.decode()

    def test_draft_status_other_agency_404(self, client, user_b, agency):
        note = _transcribed_note(agency, user_b.agency.members.first())
        client.force_login(user_b)
        resp = client.get(f"/ai/voice/{note.pk}/draft/status/")
        assert resp.status_code == 404
