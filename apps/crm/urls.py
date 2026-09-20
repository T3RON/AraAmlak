"""
CRM URL configuration.
"""

from django.urls import path

from apps.crm import views

app_name = "crm"

urlpatterns = [
    path("", views.RequestListView.as_view(), name="list"),
    path("add/", views.RequestCreateView.as_view(), name="create"),
    path("<int:pk>/edit/", views.RequestUpdateView.as_view(), name="update"),
]
