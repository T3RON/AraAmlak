"""URL patterns for the AI app (voice entry)."""

from django.urls import path

from . import views

app_name = "ai"

urlpatterns = [
    path("voice/", views.voice_note_list_view, name="voice_list"),
    path("voice/upload/", views.voice_note_upload_view, name="voice_upload"),
    path("voice/<int:pk>/status/", views.voice_note_status_view, name="voice_status"),
    path("voice/<int:pk>/retry/", views.voice_note_retry_view, name="voice_retry"),
    path("voice/<int:pk>/draft/", views.draft_generate_view, name="draft_generate"),
    path("voice/<int:pk>/draft/status/", views.draft_status_view, name="draft_status"),
    path("draft/<int:pk>/apply/", views.draft_apply_view, name="draft_apply"),
    path("voice/<int:pk>/", views.voice_note_detail_view, name="voice_detail"),
]
