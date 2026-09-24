"""
Celery tasks for the rendering app.

Tasks:
- render_poster_task: render a queued RenderJob with retry and exponential backoff.
"""

from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_BACKOFF_BASE = 60  # seconds — doubles each retry: 60, 120, 240


@shared_task(
    bind=True,
    max_retries=_MAX_RETRIES,
    acks_late=True,
    name="apps.rendering.tasks.render_poster_task",
)
def render_poster_task(self, job_id: int) -> None:
    """
    Render a pending RenderJob via the configured engine.

    Retries up to _MAX_RETRIES times with exponential backoff on any error.
    """
    from apps.rendering.services import run_render

    try:
        run_render(job_id)
    except Exception as exc:
        countdown = _BACKOFF_BASE * (2 ** self.request.retries)
        logger.warning(
            "render_poster_task: RenderJob #%d attempt %d failed — retry in %ds: %s",
            job_id,
            self.request.retries + 1,
            countdown,
            exc,
        )
        raise self.retry(exc=exc, countdown=countdown) from exc
