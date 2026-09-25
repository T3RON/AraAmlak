"""
Tests for Phase 5D — in-page voice recording (MediaRecorder).

Server-side coverage only (the recorder itself is browser JS):
- upload partial exposes the recorder UI and error messages
- a real webm-magic upload goes end-to-end to transcribed (eager Celery)
"""

from __future__ import annotations

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

# ─── Template ─────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestVoiceUploadPartial:
    def test_record_ui_present(self, client, user):
        client.force_login(user)
        resp = client.get("/ai/voice/")
        html = resp.content.decode()
        assert "MediaRecorder" in html
        assert "startRecording()" in html
        assert "stopRecording()" in html
        assert "ضبط از میکروفن" in html

    def test_permission_error_message_present(self, client, user):
        client.force_login(user)
        html = client.get("/ai/voice/").content.decode()
        assert "دسترسی به میکروفن داده نشد" in html
        assert "فایل صوتی انتخاب کنید" in html  # manual fallback path


# ─── Upload accepts recorded webm ─────────────────────────────────────────────


@pytest.mark.django_db
class TestWebmUpload:
    def test_webm_end_to_end(self, client, user):
        """MediaRecorder output (webm magic) → upload → eager transcription."""
        webm = SimpleUploadedFile(
            "recording.webm",
            b"\x1a\x45\xdf\xa3" + b"\x00" * 64,
            content_type="audio/webm",
        )
        client.force_login(user)
        resp = client.post("/ai/voice/upload/", {"audio": webm})
        assert resp.status_code == 201

        from apps.ai.models import VoiceNote

        note = VoiceNote.objects.get(mime_type="audio/webm")
        assert note.status == "transcribed"
        assert note.transcript
