"""Signals for the matching app."""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


def connect_signals():
    """
    Wire up post_save signal for crm.Request → matching task.

    Called from MatchingConfig.ready() to avoid import issues.
    """
    from apps.crm.models import Request

    @receiver(post_save, sender=Request, dispatch_uid="matching.run_on_request_save")
    def on_request_save(sender, instance, created, **kwargs):
        """Dispatch matching task whenever a Request is created or updated."""
        from apps.matching.tasks import run_matching_for_request

        run_matching_for_request.delay(instance.pk)
        logger.debug("Matching task dispatched for Request pk=%s", instance.pk)
