"""Celery tasks for the CRM app (timeline / visit / task reminders)."""

import logging

from django.utils.translation import gettext_lazy as _

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def send_due_task_reminders(self) -> dict:
    """
    Send one reminder notification per overdue pending task.

    Idempotent: ``reminder_sent_at`` guards against duplicate reminders, so this
    task can safely run repeatedly from the Celery Beat schedule.
    """
    from django.utils import timezone

    from apps.crm.models import NotificationKind, Task, TaskStatus
    from apps.crm.services import notify

    now = timezone.now()
    overdue = (
        Task.objects.filter(
            status=TaskStatus.PENDING,
            due_at__lt=now,
            reminder_sent_at__isnull=True,
        )
        .select_related("assignee", "agency")
        .iterator(chunk_size=200)
    )

    sent = 0
    for task in overdue:
        try:
            notify(
                task.assignee,
                kind=NotificationKind.WARNING,
                title=_("یادآوری: وظیفه سررسید شده"),
                body=_("«{}» موعد آن در {} گذشته است.").format(
                    task.title,
                    timezone.localtime(task.due_at).strftime("%Y-%m-%d %H:%M"),
                ),
                link="",
            )
            task.reminder_sent_at = now
            task.save(update_fields=["reminder_sent_at", "updated_at"])
            sent += 1
        except Exception:  # noqa: BLE001 — keep processing other tasks
            logger.exception("Failed to send reminder for task %s", task.pk)

    logger.info("send_due_task_reminders: sent %d reminders", sent)
    return {"sent": sent}
