from celery import shared_task
from .usecases import StudentStatusUsecase, UserSyncUsecase
import logging

logger = logging.getLogger(__name__)


@shared_task(queue="accounts_queue")
def update_student_status_task():
    """
    Celery task to update student status based on attendance and feedback criteria
    """
    try:
        StudentStatusUsecase.update_student_status()
        logger.info("Successfully completed student status update task")
    except Exception as e:
        logger.error(f"Error in student status update task: {str(e)}")
        raise


@shared_task(queue="accounts_queue")
def sync_configs_task():
    """
    Celery task to update student status based on attendance and feedback criteria
    """
    try:
        UserSyncUsecase.sync_users_from_config()
        logger.info("Successfully started sync user task")
    except Exception as e:
        logger.error(f"Error in syncing user task: {str(e)}")
        raise
