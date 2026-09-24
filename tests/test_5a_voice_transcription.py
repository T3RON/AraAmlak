"""
Tests for Phase 5A — Voice infrastructure and transcription.

Coverage:
- detect_audio_mime (magic bytes)
- ConsoleTranscriptionProvider
- OpenAITranscriptionProvider (mocked HTTP)
- GeminiTranscriptionProvider (mocked HTTP, output_text + fallback)
- AgencyAIConfig → provider resolution (openai / gemini / console fallback)
- create_voice_note validation (empty, oversize, bad content)
- enqueue_transcription (state + task dispatch + idempotency)
- run_transcription state machine (success + failure)
- Voice upload view (auth, validation, agency scoping)
- Voice status/detail/retry views
- Tenant isolation: agency B cannot see agency A voice notes
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

# ─── Fixtures & helpers ───────────────────────────────────────────────────────


def _ogg_bytes() -> bytes:
    return b"OggS" + b"\x00" * 32


def _ogg_upload(name: str = "voice.ogg") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, _ogg_bytes(), content_type="audio/ogg")


@pytest.fixture
def listing(db, agency):
    from apps.listings.models import DealType, Listing, PropertyType

    return Listing.objects.create(
        agency=agency,
        property_type=PropertyType.APARTMENT,
        deal_type=DealType.SALE,
        city="تهران",
        status="active",
    )


@pytest.fixture
def voice_note(db, agency, user, listing):
    from apps.ai.models import VoiceNote

    return VoiceNote.objects.create(
        agency=agency,
        listing=listing,
        audio=_ogg_upload(),
        original_filename="voice.ogg",
        mime_type="audio/ogg",
        file_size=len(_ogg_bytes()),
        uploaded_by=user,
    )


# ─── detect_audio_mime ────────────────────────────────────────────────────────


class TestDetectAudioMime:
    def test_ogg(self):
        from apps.ai.services import detect_audio_mime

        assert detect_audio_mime(b"OggS\x00\x00") == "audio/ogg"

    def test_webm(self):
        from apps.ai.services import detect_audio_mime

        assert detect_audio_mime(b"\x1a\x45\xdf\xa3") == "audio/webm"

    def test_wav(self):
        from apps.ai.services import detect_audio_mime

        assert detect_audio_mime(b"RIFF\x00\x00\x00\x00WAVE") == "audio/wav"

    def test_mp4_m4a(self):
        from apps.ai.services import detect_audio_mime

        assert detect_audio_mime(b"\x00\x00\x00\x20ftypM4A ") == "audio/mp4"

    def test_mp3_id3(self):
        from apps.ai.services import detect_audio_mime

        assert detect_audio_mime(b"ID3\x04\x00") == "audio/mpeg"

    def test_mp3_bare_frame(self):
        from apps.ai.services import detect_audio_mime

        assert detect_audio_mime(b"\xff\xfb\x90\x00") == "audio/mpeg"

    def test_unknown(self):
        from apps.ai.services import detect_audio_mime

        assert detect_audio_mime(b"not audio at all") == ""


# ─── ConsoleTranscriptionProvider ─────────────────────────────────────────────


class TestConsoleTranscriptionProvider:
    def test_returns_canned_persian_transcript(self):
        from apps.ai.providers.console import ConsoleTranscriptionProvider

        result = ConsoleTranscriptionProvider().transcribe("fake.ogg")
        assert "آپارتمان" in result.text
        assert result.provider == "console"
        assert result.provider_file_id.startswith("FAKE-TR-")

    def test_language_passthrough(self):
        from apps.ai.providers.console import ConsoleTranscriptionProvider

        result = ConsoleTranscriptionProvider().transcribe("fake.ogg", language="fa")
        assert result.language == "fa"


# ─── OpenAITranscriptionProvider (mocked HTTP) ───────────────────────────────


class TestOpenAITranscriptionProvider:
    def test_send_success(self):
        from apps.ai.providers.openai_whisper import OpenAITranscriptionProvider

        provider = OpenAITranscriptionProvider(api_key="sk-test")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"text": "یک آپارتمان هشتاد متری"}
        mock_resp.raise_for_status = lambda: None

        with (
            patch("apps.ai.providers.openai_whisper.requests.post", return_value=mock_resp) as mp,
            patch("pathlib.Path.open", MagicMock()),
            patch("pathlib.Path.read_bytes", return_value=b"OggSfake"),
        ):
            result = provider.transcribe("fake.ogg")

        assert result.text == "یک آپارتمان هشتاد متری"
        assert result.provider == "openai"
        _, kwargs = mp.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer sk-test"
        assert kwargs["data"]["model"] == "whisper-1"
        assert kwargs["data"]["language"] == "fa"

    def test_empty_text_raises(self):
        from apps.ai.providers.openai_whisper import OpenAITranscriptionProvider

        provider = OpenAITranscriptionProvider(api_key="sk-test")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"text": ""}
        mock_resp.raise_for_status = lambda: None

        with (
            patch("apps.ai.providers.openai_whisper.requests.post", return_value=mock_resp),
            patch("pathlib.Path.open", MagicMock()),
            patch("pathlib.Path.read_bytes", return_value=b"OggSfake"),
        ):
            with pytest.raises(RuntimeError, match="empty"):
                provider.transcribe("fake.ogg")


# ─── GeminiTranscriptionProvider (mocked HTTP) ───────────────────────────────


class TestGeminiTranscriptionProvider:
    def test_success_output_text(self):
        from apps.ai.providers.gemini import GeminiTranscriptionProvider

        provider = GeminiTranscriptionProvider(api_key="g-key")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"output_text": "فروشی آپارتمان دو خواب"}
        mock_resp.raise_for_status = lambda: None

        with (
            patch("apps.ai.providers.gemini.requests.post", return_value=mock_resp) as mp,
            patch("pathlib.Path.read_bytes", return_value=b"OggSfake"),
        ):
            result = provider.transcribe("fake.ogg")

        assert result.text == "فروشی آپارتمان دو خواب"
        _, kwargs = mp.call_args
        assert kwargs["headers"]["x-goog-api-key"] == "g-key"
        # Audio part must be base64 with mime
        audio_part = kwargs["data"] and __import__("json").loads(kwargs["data"])["input"][1]
        assert audio_part["type"] == "audio"
        assert audio_part["mime_type"] == "audio/ogg"

    def test_success_fallback_output_steps(self):
        from apps.ai.providers.gemini import GeminiTranscriptionProvider

        provider = GeminiTranscriptionProvider(api_key="g-key")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "output": [
                {"content": {"parts": [{"type": "text", "text": "رونویسی جایگزین"}]}}
            ]
        }
        mock_resp.raise_for_status = lambda: None

        with (
            patch("apps.ai.providers.gemini.requests.post", return_value=mock_resp),
            patch("pathlib.Path.read_bytes", return_value=b"OggSfake"),
        ):
            result = provider.transcribe("fake.ogg")

        assert result.text == "رونویسی جایگزین"

    def test_no_text_raises(self):
        from apps.ai.providers.gemini import GeminiTranscriptionProvider

        provider = GeminiTranscriptionProvider(api_key="g-key")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"output": []}
        mock_resp.raise_for_status = lambda: None

        with (
            patch("apps.ai.providers.gemini.requests.post", return_value=mock_resp),
            patch("pathlib.Path.read_bytes", return_value=b"OggSfake"),
        ):
            with pytest.raises(RuntimeError, match="no text"):
                provider.transcribe("fake.ogg")

    def test_too_large_audio_raises(self, tmp_path):
        from apps.ai.providers.gemini import _MAX_B64_BYTES, GeminiTranscriptionProvider

        provider = GeminiTranscriptionProvider(api_key="g-key")
        big = tmp_path / "big.ogg"
        big.write_bytes(b"\x00" * (_MAX_B64_BYTES + 1))
        with pytest.raises(RuntimeError, match="too large"):
            provider.transcribe(str(big))


# ─── Provider resolution ──────────────────────────────────────────────────────


class TestProviderResolution:
    def test_no_config_falls_back_to_console(self, agency):
        from apps.ai.providers.console import ConsoleTranscriptionProvider
        from apps.ai.services import get_transcription_provider_for_agency

        provider = get_transcription_provider_for_agency(agency)
        assert isinstance(provider, ConsoleTranscriptionProvider)

    def test_openai_config(self, agency):
        from apps.ai.models import AgencyAIConfig, AIProvider
        from apps.ai.providers.openai_whisper import OpenAITranscriptionProvider
        from apps.ai.services import get_transcription_provider_for_agency

        AgencyAIConfig.objects.create(
            agency=agency, provider=AIProvider.OPENAI, api_key="sk-live"
        )
        provider = get_transcription_provider_for_agency(agency)
        assert isinstance(provider, OpenAITranscriptionProvider)
        assert provider._api_key == "sk-live"
        assert provider._model == "whisper-1"

    def test_gemini_config_with_custom_model(self, agency):
        from apps.ai.models import AgencyAIConfig, AIProvider
        from apps.ai.providers.gemini import GeminiTranscriptionProvider
        from apps.ai.services import get_transcription_provider_for_agency

        AgencyAIConfig.objects.create(
            agency=agency,
            provider=AIProvider.GEMINI,
            api_key="g-live",
            model_name="gemini-2.0-flash",
        )
        provider = get_transcription_provider_for_agency(agency)
        assert isinstance(provider, GeminiTranscriptionProvider)
        assert provider._model == "gemini-2.0-flash"


# ─── create_voice_note ────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCreateVoiceNote:
    def test_valid_ogg(self, agency, user, listing):
        from apps.ai.models import VoiceNoteState
        from apps.ai.services import create_voice_note

        note = create_voice_note(agency, _ogg_upload(), listing=listing, uploaded_by=user)
        assert note.pk is not None
        assert note.mime_type == "audio/ogg"
        assert note.status == VoiceNoteState.UPLOADED
        assert note.listing == listing
        assert note.file_size == len(_ogg_bytes())

    def test_empty_file_rejected(self, agency):
        from django.core.exceptions import ValidationError

        from apps.ai.services import create_voice_note

        with pytest.raises(ValidationError, match="خالی"):
            create_voice_note(agency, SimpleUploadedFile("x.ogg", b""))

    def test_oversize_rejected(self, agency):
        from django.core.exceptions import ValidationError

        from apps.ai.services import MAX_AUDIO_SIZE_BYTES, create_voice_note

        big = SimpleUploadedFile("big.ogg", b"OggS" + b"\x00" * MAX_AUDIO_SIZE_BYTES)
        with pytest.raises(ValidationError, match="بیش از حد"):
            create_voice_note(agency, big)

    def test_non_audio_rejected(self, agency):
        from django.core.exceptions import ValidationError

        from apps.ai.services import create_voice_note

        with pytest.raises(ValidationError, match="فرمت"):
            create_voice_note(
                agency, SimpleUploadedFile("x.txt", b"plain text file")
            )


# ─── enqueue_transcription ────────────────────────────────────────────────────


@pytest.mark.django_db
class TestEnqueueTranscription:
    def test_moves_to_queued_and_dispatches(self, voice_note):
        from apps.ai.models import VoiceNoteState
        from apps.ai.services import enqueue_transcription

        with patch("apps.ai.tasks.transcribe_voice_task.delay") as mock_delay:
            enqueue_transcription(voice_note)

        assert voice_note.status == VoiceNoteState.QUEUED
        mock_delay.assert_called_once_with(voice_note.pk)

    def test_idempotent_when_already_queued(self, voice_note):
        from apps.ai.services import enqueue_transcription

        voice_note.status = "queued"
        voice_note.save()
        with patch("apps.ai.tasks.transcribe_voice_task.delay") as mock_delay:
            enqueue_transcription(voice_note)

        mock_delay.assert_not_called()

    def test_retry_after_failure_allowed(self, voice_note):
        from apps.ai.services import enqueue_transcription

        voice_note.status = "failed"
        voice_note.save()
        with patch("apps.ai.tasks.transcribe_voice_task.delay") as mock_delay:
            enqueue_transcription(voice_note)

        mock_delay.assert_called_once_with(voice_note.pk)


# ─── run_transcription (state machine) ───────────────────────────────────────


@pytest.mark.django_db
class TestRunTranscription:
    def test_success_with_console_provider(self, voice_note):
        """No AI config → console provider → transcript stored, state transcribed."""
        from apps.ai.models import VoiceNoteState
        from apps.ai.services import run_transcription

        voice_note.status = "queued"
        voice_note.save()

        run_transcription(voice_note.pk)
        voice_note.refresh_from_db()

        assert voice_note.status == VoiceNoteState.TRANSCRIBED
        assert "آپارتمان" in voice_note.transcript
        assert voice_note.transcribed_at is not None
        assert voice_note.duration_seconds == 42

    def test_provider_error_marks_failed_and_reraises(self, voice_note):
        from apps.ai.services import run_transcription

        with patch(
            "apps.ai.services.get_transcription_provider_for_agency"
        ) as mock_get:
            mock_get.return_value.transcribe.side_effect = RuntimeError("API down")
            with pytest.raises(RuntimeError, match="API down"):
                run_transcription(voice_note.pk)

        voice_note.refresh_from_db()
        assert voice_note.status == "failed"
        assert "API down" in voice_note.error_message

    def test_idempotent_when_already_transcribed(self, voice_note):
        from apps.ai.services import run_transcription

        voice_note.status = "transcribed"
        voice_note.transcript = "موجود"
        voice_note.save()
        run_transcription(voice_note.pk)  # must not raise or change state
        voice_note.refresh_from_db()
        assert voice_note.transcript == "موجود"


# ─── Celery task ──────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestTranscribeVoiceTask:
    def test_task_calls_service(self, voice_note):
        from apps.ai.tasks import transcribe_voice_task

        with patch("apps.ai.services.run_transcription") as mock_run:
            transcribe_voice_task.apply(args=[voice_note.pk])

        mock_run.assert_called_once_with(voice_note.pk)


# ─── Views ────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestVoiceViews:
    def test_list_requires_login(self, client):
        resp = client.get("/ai/voice/")
        assert resp.status_code == 302  # redirect to login

    def test_list_page_renders(self, client, user, voice_note):
        client.force_login(user)
        resp = client.get("/ai/voice/")
        assert resp.status_code == 200
        assert b"voice-note-%d" % voice_note.pk in resp.content

    def test_upload_valid(self, client, user, listing):
        """Celery runs eagerly in tests — upload goes end-to-end to transcribed."""
        client.force_login(user)
        resp = client.post(
            "/ai/voice/upload/",
            {"audio": _ogg_upload(), "listing": listing.pk},
        )
        assert resp.status_code == 201

        from apps.ai.models import VoiceNote

        note = VoiceNote.objects.get(listing=listing)
        assert note.status == "transcribed"
        assert note.transcript  # console provider filled a transcript

    def test_upload_missing_file(self, client, user):
        client.force_login(user)
        resp = client.post("/ai/voice/upload/", {})
        assert resp.status_code == 400

    def test_upload_bad_format(self, client, user):
        client.force_login(user)
        bad = SimpleUploadedFile("x.txt", b"hello world", content_type="text/plain")
        resp = client.post("/ai/voice/upload/", {"audio": bad})
        assert resp.status_code == 422

    def test_upload_to_other_agency_listing_404(self, client, user, agency_b):
        from apps.listings.models import DealType, Listing, PropertyType

        other = Listing.objects.create(
            agency=agency_b,
            property_type=PropertyType.APARTMENT,
            deal_type=DealType.SALE,
            city="شهر",
        )
        client.force_login(user)
        resp = client.post(
            "/ai/voice/upload/", {"audio": _ogg_upload(), "listing": other.pk}
        )
        assert resp.status_code == 404

    def test_status_partial(self, client, user, voice_note):
        client.force_login(user)
        resp = client.get(f"/ai/voice/{voice_note.pk}/status/")
        assert resp.status_code == 200

    def test_status_other_agency_404(self, client, user_b, voice_note):
        client.force_login(user_b)
        resp = client.get(f"/ai/voice/{voice_note.pk}/status/")
        assert resp.status_code == 404

    def test_detail_page(self, client, user, voice_note):
        client.force_login(user)
        resp = client.get(f"/ai/voice/{voice_note.pk}/")
        assert resp.status_code == 200

    def test_detail_other_agency_404(self, client, user_b, voice_note):
        client.force_login(user_b)
        resp = client.get(f"/ai/voice/{voice_note.pk}/")
        assert resp.status_code == 404

    def test_retry_requeues(self, client, user, voice_note):
        client.force_login(user)
        voice_note.status = "failed"
        voice_note.save()
        with patch("apps.ai.tasks.transcribe_voice_task.delay") as mock_delay:
            resp = client.post(f"/ai/voice/{voice_note.pk}/retry/")

        assert resp.status_code == 200
        mock_delay.assert_called_once_with(voice_note.pk)
        voice_note.refresh_from_db()
        assert voice_note.status == "queued"


# ─── Model behaviour ──────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestVoiceNoteModel:
    def test_is_terminal(self, voice_note):
        assert voice_note.is_terminal is False
        voice_note.status = "transcribed"
        assert voice_note.is_terminal is True
        voice_note.status = "failed"
        assert voice_note.is_terminal is True

    def test_str(self, voice_note):
        assert "Voice" in str(voice_note)

    def test_audio_upload_path(self, voice_note):
        assert voice_note.audio.name.startswith(f"ai/voice/{voice_note.agency_id}/")
