"""URL patterns for the rendering app (poster render)."""

from django.urls import path

from . import views

app_name = "rendering"

urlpatterns = [
    path("listings/<int:pk>/jobs/", views.render_job_list_view, name="job_list"),
    path(
        "listings/<int:pk>/jobs/create/",
        views.render_job_create_view,
        name="job_create",
    ),
    path("jobs/<int:job_pk>/download/", views.render_job_download_view, name="job_download"),
    path("jobs/<int:job_pk>/status/", views.render_job_status_view, name="job_status"),
]
