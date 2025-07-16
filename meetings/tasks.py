from functools import wraps
from typing import List, Callable
from celery import shared_task, chain
from celery.utils.log import get_task_logger
from .exceptions import (
    ConferencePlatformError,
    TeamsAuthenticationError,
    TeamsMeetingCreationError,
    TeamsMeetingDeletionError,
    MeetingNotFoundError,
    PresenterDetailsMissingError,
    ConferenceIDMissingError,
    SeriesNotFoundError,
    NoMeetingsFoundError
)
#from .serializers import MeetingSerializer
from requests.exceptions import HTTPError

logger = get_task_logger(__name__)

# Common task configuration
COMMON_TASK_CONFIG = {
    'bind': True,
    'max_retries': 3,
    'default_retry_delay': 300,  # 5 minutes
    'autoretry_for': (ConferencePlatformError,),
    'retry_backoff': True,
    'queue': 'meeting_queue',
}

def handle_meeting_exceptions(task_func: Callable) -> Callable:
    """Decorator to handle common meeting-related exceptions."""
    @wraps(task_func)
    def wrapper(self, *args, **kwargs):
        meeting_id = args[0] if args else kwargs.get('meeting_id')
        try:
            return task_func(self, *args, **kwargs)
        except HTTPError as e:
            if hasattr(e, 'response') and e.response.status_code in [404, 401, 403]:
                logger.error(f"Non-retryable error for meeting ID {meeting_id}: {str(e)}")
                raise
            logger.error(f"Retryable error for meeting ID {meeting_id}: {str(e)}")
            raise self.retry(exc=e)
        except (
            ConferencePlatformError,
            TeamsAuthenticationError,
            MeetingNotFoundError,
            PresenterDetailsMissingError,
            ConferenceIDMissingError,
            SeriesNotFoundError,
            NoMeetingsFoundError
        ) as e:
            logger.error(f"Custom error in {task_func.__name__} for meeting ID {meeting_id}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error in {task_func.__name__} for meeting ID {meeting_id}: {str(e)}")
            raise self.retry(exc=e)
    return wrapper

@shared_task(**COMMON_TASK_CONFIG)
@handle_meeting_exceptions
def create_teams_meeting_task(self, meeting_id: int) -> None:
    """Create a Teams meeting."""
    from .usecases import MeetingUsecase
    logger.info(f"Creating Teams meeting for meeting ID: {meeting_id}")
    MeetingUsecase.create_teams_meeting(meeting_id)
    logger.info(f"Successfully created Teams meeting for meeting ID: {meeting_id}")

@shared_task(**COMMON_TASK_CONFIG)
@handle_meeting_exceptions
def delete_teams_meeting_task(self, meeting_id: int, presenter_details, conference_id: str) -> None:
    """Delete a Teams meeting."""
    from .usecases import MeetingUsecase
    logger.info(f"Deleting Teams meeting for meeting ID: {meeting_id}")
    MeetingUsecase.delete_teams_meeting(meeting_id, presenter_details, conference_id)
    logger.info(f"Successfully deleted Teams meeting for meeting ID: {meeting_id}")

@shared_task(**COMMON_TASK_CONFIG)
@handle_meeting_exceptions
def update_teams_meeting_task(self, meeting_id: int) -> None:
    """Update a Teams meeting."""
    from .usecases import MeetingUsecase
    logger.info(f"Updating Teams meeting for meeting ID: {meeting_id}")
    MeetingUsecase.update_teams_meeting(meeting_id)
    logger.info(f"Successfully updated Teams meeting for meeting ID: {meeting_id}")

@shared_task(**COMMON_TASK_CONFIG)
@handle_meeting_exceptions
def process_completed_meetings_task(self) -> List[dict]:
    from .serializers import MeetingSerializer    
    """
    Process meetings that completed within the last hour.
    
    Creates a chain of tasks for each meeting that needs:
    - Attendance processing
    - Recording fetching
    - Recording upload
    
    Returns:
        List of serialized completed meetings
    """
    from meetings.repositories import MeetingRepository
    
    try:
        completed_meetings = MeetingRepository.get_meetings_completed_within_last_hour()
        serialized_meetings = MeetingSerializer.serialize_meetings(completed_meetings)
        
        for meeting in serialized_meetings:
            meeting_id = meeting.get('id')
            tasks = []
            
            # Build task chain based on processing status
            if meeting.get('attendance_metadata') is None:
                fetch_meeting_attendance_task.delay(meeting_id)
            
            needs_recording = (
                not meeting.get('recording_metadata') and 
                not meeting.get('blob_url')
            )
            if needs_recording:
                tasks.extend([
                    fetch_meeting_recording_task.si(meeting_id),
                    upload_meeting_recording_task.si(meeting_id)
                ])
            elif meeting.get('recording_metadata') and not meeting.get('blob_url'):
                tasks.append(upload_meeting_recording_task.si(meeting_id))
            
            if tasks:
                chain(tasks).apply_async()
                logger.info(f"Created task chain for meeting ID {meeting_id}")
            else:
                logger.info(f"Meeting ID {meeting_id} already fully processed")
            
        return serialized_meetings
        
    except Exception as e:
        logger.error(f"Error processing completed meetings: {str(e)}")
        raise

@shared_task(**COMMON_TASK_CONFIG)
@handle_meeting_exceptions
def fetch_meeting_attendance_task(self, meeting_id: int) -> None:
    """Fetch attendance for a single meeting."""
    from .usecases import MeetingUsecase
    logger.info(f"Fetching attendance for meeting ID: {meeting_id}")
    MeetingUsecase.fetch_teams_meeting_attendance(meeting_id)
    logger.info(f"Successfully fetched attendance for meeting ID: {meeting_id}")

@shared_task(**COMMON_TASK_CONFIG)
@handle_meeting_exceptions
def fetch_meeting_recording_task(self, meeting_id: int) -> None:
    """Fetch recording for a single meeting."""
    from .usecases import MeetingUsecase
    logger.info(f"Fetching recording for meeting ID: {meeting_id}")
    MeetingUsecase.fetch_teams_meeting_recording(meeting_id)
    logger.info(f"Successfully fetched recording for meeting ID: {meeting_id}")

@shared_task(**COMMON_TASK_CONFIG)
@handle_meeting_exceptions
def upload_meeting_recording_task(self, meeting_id: int) -> None:
    """Upload meeting recording to storage."""
    from .usecases import MeetingUsecase
    logger.info(f"Uploading recording for meeting ID: {meeting_id}")
    MeetingUsecase.upload_meeting_recording_to_storage(meeting_id)
    logger.info(f"Successfully uploaded recording for meeting ID: {meeting_id}")
