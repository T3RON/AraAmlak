from django.apps import AppConfig


class MatchingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.matching"
    verbose_name = "تطبیق"

    def ready(self):
        from apps.matching.signals import connect_signals  # noqa: F401

        connect_signals()
