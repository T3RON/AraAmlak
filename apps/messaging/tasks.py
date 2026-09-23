from celery import shared_task
from django.utils import timezone
from apps.messaging.models import SMSMessage, SMSStatus
from apps.messaging.services import deliver_message, refresh_statuses

@shared_task(bind=True, max_retries=5)
def send_sms_task(self, message_id: int):
    try:
        deliver_message(message_id)
    except Exception as exc:
        self.retry(countdown=60 * (2 ** self.request.retries))

@shared_task
def poll_sms_statuses():
    refresh_statuses()

@shared_task
def check_sms_config_task():
    pass