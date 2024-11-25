from celery import shared_task
from celery.utils.log import get_task_logger
from .exceptions import ConferencePlatformError


logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
    autoretry_for=(ConferencePlatformError,),
    retry_backoff=True,
    queue='default',
)
def create_teams_meeting_task(self, meeting_id: int) -> None:
    """
    Celery task to create a Teams meeting
    """
    from .usecases import MeetingUsecase

    logger.info(f"Creating Teams meeting for meeting ID: {meeting_id}")
    try:
        MeetingUsecase.create_teams_meeting(meeting_id)
        logger.info(f"Successfully created Teams meeting for meeting ID: {meeting_id}")
    except Exception as e:
        logger.error(
            f"Error creating Teams meeting for meeting ID {meeting_id}: {str(e)}"
        )
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    autoretry_for=(ConferencePlatformError,),
    retry_backoff=True,
    queue='default',
)
def delete_teams_meeting_task(self, meeting_id:int,presenter_details,conference_id:str) -> None:
    """
    Celery task to delete a Teams meeting
    """
    from .usecases import MeetingUsecase
    logger.info(f"Deleting Teams meeting for meeting ID: {meeting_id}")
    try:
        MeetingUsecase.delete_teams_meeting(meeting_id,presenter_details,conference_id)
        logger.info(f"Successfully deleted Teams meeting for meeting ID: {meeting_id}")
    except Exception as e:
        logger.error(
            f"Error deleting Teams meeting for meeting ID {meeting_id}: {str(e)}"
        )
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    autoretry_for=(ConferencePlatformError,),
    retry_backoff=True,
    queue='default',
)
def update_teams_meeting_task(self, meeting_id:int) -> None:
    """
    Celery task to update a Teams meeting
    """
    from .usecases import MeetingUsecase
    logger.info(f"Updating Teams meeting for meeting ID: {meeting_id}")
    try:
        MeetingUsecase.update_teams_meeting(meeting_id)
        logger.info(f"Successfully updated Teams meeting for meeting ID: {meeting_id}")
    except Exception as e:
        logger.error(
            f"Error updating Teams meeting for meeting ID {meeting_id}: {str(e)}"
        )
        raise self.retry(exc=e)