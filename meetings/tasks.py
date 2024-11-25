from celery import shared_task
from celery.utils.log import get_task_logger
from meetings.repositories import MeetingRepository
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


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    autoretry_for=(ConferencePlatformError,),
    retry_backoff=True,
    queue='default',
)
def fetch_meetings_attendance_data(self) -> None:
    """
    Celery task to fetch and update attendance data for all pending Teams meetings.
    """
    logger.info("Fetching pending meetings to update Teams attendance.")
    try:
        pending_meetings = MeetingRepository.get_attendance_details_pending_meetings()
        for meeting in pending_meetings:
            # Schedule a new task for each pending meeting
            fetch_meeting_attendance_data.delay(meeting.id)
        logger.info(f"Scheduled tasks for {len(pending_meetings)} pending meetings to get attendance.")
    except Exception as e:
        logger.error(f"Error fetching pending meetings: {str(e)}")
        raise self.retry(exc=e)

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    autoretry_for=(ConferencePlatformError,),
    retry_backoff=True,
    queue='default',
)
def fetch_meeting_attendance_data(self, meeting_id: int) -> None:
    """
    Celery task to update a specific meeting attendance.
    """
    from .usecases import MeetingUsecase
    logger.info(f"Updating Teams meeting for meeting ID: {meeting_id}")
    try:
        MeetingUsecase.get_attendance_teams_meeting(meeting_id)
        logger.info(f"Successfully updated Teams meeting for meeting ID: {meeting_id}")
    except Exception as e:
        logger.error(f"Error updating Teams meeting for meeting ID {meeting_id}: {str(e)}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    autoretry_for=(ConferencePlatformError,),
    retry_backoff=True,
    queue='default',
)
def fetch_meetings_recordings_data(self) -> None:
    """
    Celery task to fetch and update recording data for all pending Teams meetings.
    """
    logger.info("Fetching pending recordings to update attendance data.")
    try:
        pending_meetings = MeetingRepository.get_recordings_pending_meetings()
        for meeting in pending_meetings:
            # Schedule a new task for each pending meeting
            fetch_meeting_recording_data.delay(meeting.id)
        logger.info(f"Scheduled tasks for {len(pending_meetings)} pending meetings to fetch recordings.")
    except Exception as e:
        logger.error(f"Error fetching pending recordings: {str(e)}")
        raise self.retry(exc=e)

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    autoretry_for=(ConferencePlatformError,),
    retry_backoff=True,
    queue='default',
)
def fetch_meeting_recording_data(self, meeting_id: int) -> None:
    """
    Celery task to update a specific meeting recording.
    """
    from .usecases import MeetingUsecase
    logger.info(f"Updating recording attendance for recording ID: {meeting_id}")
    try:
        MeetingUsecase.get_recordings_meeting(meeting_id)
        logger.info(f"Successfully updated recording for recording ID: {meeting_id}")
    except Exception as e:
        logger.error(f"Error updating recording for recording ID {meeting_id}: {str(e)}")
        raise self.retry(exc=e)


