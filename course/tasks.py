from celery import shared_task
from course.usecases import CourseContentDriveUsecase
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3,queue='default')
def sync_course_content_task(self, course_id):
    """Celery task to sync course content from Drive"""
    usecase = CourseContentDriveUsecase()
    result = usecase.sync_course_content(course_id)
    logger.info(f"Synced content for course {course_id}")