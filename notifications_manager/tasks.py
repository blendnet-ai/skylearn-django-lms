from celery import shared_task
from .usecases import NotificationManagerUsecase
import logging  # {{ edit_1 }}

# {{ edit_2 }}
logger = logging.getLogger(__name__)  # Setup logger


@shared_task(bind=True, max_retries=3, queue='notification_manager_queue')
def schedule_meeting_notifications_task(self):
    """Celery task to schedule notifications for upcoming meetings."""
    try:
        NotificationManagerUsecase.schedule_meeting_notifications()
    except Exception as e:
        logger.error(f"Error scheduling meeting notifications: {str(e)}")
        raise self.retry(exc=e)



@shared_task(bind=True, max_retries=3, queue='notification_manager_queue')
def schedule_missed_lecture_notifications_task(self):
    """Celery task to schedule notifications for upcoming meetings."""
    try:
        NotificationManagerUsecase.schedule_missed_lecture_notifications()
    except Exception as e:
        logger.error(f"Error scheduling meeting notifications: {str(e)}")
        raise self.retry(exc=e)
    

@shared_task(bind=True, max_retries=3, queue='notification_manager_queue')
def schedule_inactive_user_notifications_task(self):
    """Celery task to schedule notifications for inactive users."""
    try:
        NotificationManagerUsecase.schedule_inactive_users_notifications()
    except Exception as e:
        logger.error(f"Error scheduling inactive user notifications: {str(e)}")
        raise self.retry(exc=e)
