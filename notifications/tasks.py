from celery import shared_task
from django.utils import timezone
from .services import NotificationService
from .repositories import NotificationIntentRepository
import logging  # {{ edit_1 }}

# {{ edit_2 }}
logger = logging.getLogger(__name__)  # Setup logger

@shared_task(queue='notification_queue') 
def process_notification_intents():
    current_time = timezone.now()
    logger.info("Processing notification intents at %s", current_time)  # Log the current time
    intents=NotificationIntentRepository.get_pending_intents_by_time(current_time)
    for intent in intents:
        process_notification_intent.delay(intent.id)  # Use delay to call the task asynchronously

@shared_task(queue='notification_queue') 
def process_notification_intent(intent_id):
    logger.info(f"Processing Intent {intent_id}")
    NotificationService.process_intent(intent_id)