from datetime import datetime, timedelta
from .repositories import PageEventRepository
from course.repositories import UploadRepository, UploadVideoRepository
from meetings.repositories import MeetingRepository

class LogEventUseCase:
    @staticmethod
    def log_event(user, content_id, content_type, time_spent):
        if not content_id or not content_type:
            raise ValueError("content_id and content_type are required.")

        current_date = datetime.now().date()
        
        # Convert time_spent string to timedelta if needed
        if isinstance(time_spent, str):
            import re
            match = re.match(r'^(\d+):(\d+):(\d+)$', time_spent)
            if not match:
                raise ValueError("Invalid time format. Expected hh:mm:ss.")
            time_parts = list(map(int, match.groups()))
            time_spent = timedelta(hours=time_parts[0], minutes=time_parts[1], seconds=time_parts[2])

        handlers = {
            "reading": LogEventUseCase._handle_reading_event,
            "video": LogEventUseCase._handle_video_event,
            "recording": LogEventUseCase._handle_recording_event
        }

        handler = handlers.get(content_type)
        if not handler:
            raise ValueError(f"Invalid content_type: {content_type}")

        return handler(user, content_id, current_date, time_spent)

    @staticmethod
    def _handle_reading_event(user, content_id, current_date, time_spent):
        upload = UploadRepository.get_reading_resource_by_id(resource_id=content_id)
        if not upload:
            raise ValueError("Content not found")
        return LogEventUseCase._create_or_update_event(user, current_date, time_spent, upload=upload)

    @staticmethod
    def _handle_video_event(user, content_id, current_date, time_spent):
        upload_video = UploadVideoRepository.get_video_resource_by_id(resource_id=content_id)
        if not upload_video:
            raise ValueError("Content not found")
        return LogEventUseCase._create_or_update_event(user, current_date, time_spent, upload_video=upload_video)

    @staticmethod
    def _handle_recording_event(user, content_id, current_date, time_spent):
        meeting = MeetingRepository.get_meeting_by_id(id=content_id)
        if not meeting:
            raise ValueError("Content not found")
        return LogEventUseCase._create_or_update_event(user, current_date, time_spent, meeting=meeting)

    @staticmethod
    def _create_or_update_event(user, current_date, time_spent, upload=None, upload_video=None, meeting=None):
        event, created = PageEventRepository.get_or_create_page_event(
            user, current_date, True, time_spent, upload, upload_video, meeting
        )
        if not created:
            event = PageEventRepository.add_time_to_user_time(event, time_spent)
        return event