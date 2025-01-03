from celery import shared_task
from course.usecases import CourseContentDriveUsecase
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3,queue='course_queue')
def sync_course_content_task(self, course_id):
    """Celery task to sync course content from Drive"""
    usecase = CourseContentDriveUsecase()
    result = usecase.sync_course_content(course_id)
    logger.info(f"Synced content for course {course_id}")

@shared_task(bind=True, max_retries=3, queue='course_queue')
def create_attendance_records_task(self, meeting_id):
    """Celery task to create attendance records for a meeting"""
    try:
        from meetings.usecases import MeetingUsecase
        from meetings.repositories import MeetingRepository
        logger.info(f"Creating attendance records for meeting {meeting_id}")
        meeting = MeetingRepository.get_meeting_by_id(meeting_id)
        MeetingUsecase.create_attendace_records(meeting=meeting)
        logger.info(f"Successfully created attendance records for meeting {meeting_id}")
    except Exception as e:
        logger.error(f"Error creating attendance records for meeting {meeting_id}: {str(e)}")
        raise self.retry(exc=e)