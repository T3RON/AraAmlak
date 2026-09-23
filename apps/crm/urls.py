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

    # Timeline (تایم‌لاین)
    path("timeline/", views.InteractionListView.as_view(), name="timeline"),
    path("timeline/add/", views.InteractionCreateView.as_view(), name="timeline_add"),

    # Visit (بازدید)
    path("visits/add/", views.VisitCreateView.as_view(), name="visit_create"),
    path("visits/<int:pk>/complete/", views.VisitCompleteView.as_view(), name="visit_complete"),

    # Task (وظایف)
    path("tasks/", views.TaskListView.as_view(), name="tasks"),
    path("tasks/add/", views.TaskCreateView.as_view(), name="task_create"),
    path("tasks/<int:pk>/toggle/", views.task_toggle_view, name="task_toggle"),
    path("my-day/", views.MyDayView.as_view(), name="my_day"),

    # Notifications (اعلان‌ها)
    path("notifications/", views.NotificationListView.as_view(), name="notifications"),
    path(
        "notifications/mark-read/",
        views.notification_mark_read_view,
        name="notifications_mark_read",
    ),
]
