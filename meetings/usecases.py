from telnetlib import LOGOUT
from meetings.models import Meeting, MeetingSeries, meeting_post_save
from django.conf import settings
from meetings.repositories import (
    MeetingRepository,
    MeetingSeriesRepository,
    AttendaceRecordRepository,
)
from course.serializers import LiveClassSeriesSerializer
from dateutil.rrule import DAILY, WEEKLY, MONTHLY
from dateutil.rrule import rrule
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import transaction
from .exceptions import (
    MeetingNotFoundError,
    PresenterDetailsMissingError,
    ConferenceIDMissingError,
    SeriesNotFoundError,
    NoMeetingsFoundError,
)
import urllib
from meetings.services.msteams import MSTeamsConferencePlatformService
import logging
from storage_service.azure_storage import AzureStorageService
from meetings.models import AttendanceRecord, Meeting
from .repositories import AttendaceRecordRepository
from django.conf import settings
from meetings.tasks import create_teams_meeting_task

logger = logging.getLogger(__name__)
from django.contrib.auth import get_user_model

User = get_user_model()
from custom_auth.utils import CryptographyHandler
from notifications.repositories import NotificationIntentRepository
from evaluation.usecases import AssessmentUseCase
import time

storage_service = AzureStorageService()
import pytz


class MeetingSeriesUsecase:
    class WeekdayScheduleNotSet(Exception):
        def __init__(self):
            super().__init__("`weekday_schedule` is required for weekly recurrence")

    class InvalidWeekdaySchedule(Exception):
        def __init__(self):
            super().__init__(
                "`weekday_schedule` must be a list of 7 boolean values (one for each day of the week)"
            )

    class MonthlyDayNotSet(Exception):
        def __init__(self):
            super().__init__("`monthly_day` is required for monthly recurrence")

    class NoRecurringDatesFound(Exception):
        def __init__(self):
            super().__init__("The provided configuration results in no meeting dates")

    class StartDateInPast(Exception):
        def __init__(self):
            super().__init__("Start date must be in the future")

    class EndDateSmallerThanStartDate(Exception):
        def __init__(self):
            super().__init__("End date must be greater than start date")

    class LecturerNotAssigned(Exception):
        def __init__(self):
            super().__init__("Lecturer Not Assigned Yet to Batch")

    @staticmethod
    def renew_meeting_series(
        meeting_series,
        title,
        start_time,
        start_date,
        duration,
        end_date,
        recurrence_type,
        weekday_schedule,
        monthly_day,
    ):
        # If recurrence type is changing, we not only need to update the meeting series, but also delete previous meeting occurrences and create new ones
        # Do the same in case of start time and end date changing (for simplicity)
        if (
            recurrence_type != meeting_series.recurrence_type
            or start_time != meeting_series.start_time
            or end_date != meeting_series.end_date
        ):
            # Get old meetings before creating new ones
            old_meetings = list(
                MeetingRepository.get_meetings_by_series_id(meeting_series.id)
            )

            # First create new meetings
            MeetingSeriesUsecase.create_or_update_meeting_series_and_create_occurrences(
                title,
                start_time,
                start_date,
                duration,
                end_date,
                recurrence_type,
                weekday_schedule,
                monthly_day,
                meeting_series,
            )

            # Delete the old meetings that we captured before creating new ones
            for meeting in old_meetings:
                meeting.delete()

        # If not, then only update the meeting series
        else:
            MeetingSeriesRepository.update_meeting_series(
                meeting_series,
                title,
                start_time,
                duration,
                end_date,
                recurrence_type,
                (
                    weekday_schedule
                    if recurrence_type == MeetingSeries.RECURRENCE_TYPE_WEEKLY
                    else None
                ),
                (
                    monthly_day
                    if recurrence_type == MeetingSeries.RECURRENCE_TYPE_MONTHLY
                    else None
                ),
            )

    @staticmethod
    def create_or_update_meeting_series_and_create_occurrences(
        title,
        start_time,
        start_date,
        duration,
        end_date,
        recurrence_type,
        weekday_schedule,
        monthly_day,
        meeting_series=None,
    ):

        if start_date < timezone.now().date():
            raise MeetingSeriesUsecase.StartDateInPast()
        if start_date > end_date:
            raise MeetingSeriesUsecase.EndDateSmallerThanStartDate()

        if (
            recurrence_type == MeetingSeries.RECURRENCE_TYPE_WEEKLY
            and weekday_schedule is None
        ):
            raise MeetingSeriesUsecase.WeekdayScheduleNotSet()
        elif len(weekday_schedule) != 7 or not all(
            isinstance(element, bool) for element in weekday_schedule
        ):
            raise MeetingSeriesUsecase.InvalidWeekdaySchedule()

        if (
            recurrence_type == MeetingSeries.RECURRENCE_TYPE_MONTHLY
            and monthly_day is None
        ):
            raise MeetingSeriesUsecase.MonthlyDayNotSet()

        # Generate meeting dates based on recurrence type
        if recurrence_type == MeetingSeries.RECURRENCE_TYPE_NOT_REPEATING:
            recurring_dates = [start_date]
        else:
            # Set up recurrence rules based on type
            if recurrence_type == MeetingSeries.RECURRENCE_TYPE_DAILY:
                freq = DAILY

                recurring_dates = list(
                    rrule(
                        freq=freq,
                        dtstart=start_date,
                        until=end_date,
                    )
                )
            elif recurrence_type == MeetingSeries.RECURRENCE_TYPE_WEEKLY:
                freq = WEEKLY
                # Convert weekday_schedule booleans to weekday numbers (0-6)
                byweekday = [i for i, enabled in enumerate(weekday_schedule) if enabled]

                if len(byweekday) == 0:
                    recurring_dates = []
                else:
                    recurring_dates = list(
                        rrule(
                            freq=freq,
                            dtstart=start_date,
                            until=end_date,
                            byweekday=byweekday,
                        )
                    )
            elif recurrence_type == MeetingSeries.RECURRENCE_TYPE_MONTHLY:
                freq = MONTHLY
                bymonthday = monthly_day

                recurring_dates = list(
                    rrule(
                        freq=freq,
                        dtstart=start_date,
                        until=end_date,
                        bymonthday=bymonthday,
                    )
                )

        if recurring_dates == []:
            raise MeetingSeriesUsecase.NoRecurringDatesFound()

        if meeting_series is None:
            meeting_series = MeetingSeriesRepository.create_meeting_series(
                title,
                start_time,
                start_date,
                duration,
                end_date,
                recurrence_type,
                (
                    weekday_schedule
                    if recurrence_type == MeetingSeries.RECURRENCE_TYPE_WEEKLY
                    else None
                ),
                (
                    monthly_day
                    if recurrence_type == MeetingSeries.RECURRENCE_TYPE_MONTHLY
                    else None
                ),
            )
        else:
            MeetingSeriesRepository.update_meeting_series(
                meeting_series,
                title,
                start_time,
                duration,
                end_date,
                recurrence_type,
                (
                    weekday_schedule
                    if recurrence_type == MeetingSeries.RECURRENCE_TYPE_WEEKLY
                    else None
                ),
                (
                    monthly_day
                    if recurrence_type == MeetingSeries.RECURRENCE_TYPE_MONTHLY
                    else None
                ),
            )

        meetings_to_create = []
        # Create meeting instances for each date
        for meeting_date in recurring_dates:
            meetings_to_create.append(
                Meeting(series=meeting_series, start_date=meeting_date, link="")
            )

        created_meetings = MeetingRepository.create_bulk_meetings(meetings_to_create)
        time.sleep(10)
        for meeting in created_meetings:
            create_teams_meeting_task.delay(meeting.id)
        return meeting_series

    @staticmethod
    def delete_meeting_series(id):
        meeting_series = MeetingSeriesRepository.get_meeting_series_by_id(id)
        MeetingRepository.get_meetings_by_series_id(id)
        meeting_series.delete()

    def get_meeting_series(id):
        meeting_series = MeetingSeriesRepository.get_meeting_series_by_id(id)
        data = {
            "title": meeting_series.title,
            "start_time": meeting_series.start_time,
            "duration": meeting_series.duration,
            "start_date": meeting_series.start_date,
            "end_date": meeting_series.end_date,
            "recurrence_type": meeting_series.recurrence_type,
            "weekday_schedule": meeting_series.weekday_schedule,
            "monthly_day": meeting_series.monthly_day,
        }
        return data


class MeetingUsecase:
    @staticmethod
    def create_teams_meeting(meeting_id: int) -> None:
        """
        Creates a Teams meeting for a given meeting ID
        """
        meeting = MeetingRepository.get_meeting_by_id(meeting_id)
        if not meeting:
            raise MeetingNotFoundError(f"Meeting with ID {meeting_id} not found")

        if not meeting.series.presenter_details:
            raise PresenterDetailsMissingError(
                f"Presenter details are missing for meeting ID {meeting_id}"
            )

        try:
            teams_service = MSTeamsConferencePlatformService()
            # Create Teams meeting using model properties
            meeting_details = teams_service.create_meeting(
                presenter=meeting.series.presenter_details,
                start_time=meeting.start_time,
                end_time=meeting.end_time,
                subject=meeting.title,
            )

            # Update meeting with Teams details
            meeting.link = meeting_details.join_url
            meeting.conference_metadata = meeting_details.all_details
            meeting.conference_id = meeting_details.id
            # Temporarily disconnect signals
            post_save.disconnect(meeting_post_save, sender=Meeting)

            # Save the meeting without triggering signals
            with transaction.atomic():
                meeting.save()

        except Exception as e:
            logger.error(
                f"Failed to create Teams meeting for meeting ID {meeting_id}: {str(e)}"
            )
            raise

    @staticmethod
    def delete_teams_meeting(meeting_id, presenter_details, conference_id) -> None:
        """
        Deletes a Teams meeting for a given meeting ID
        """

        if not conference_id:
            raise ConferenceIDMissingError(
                f"missing conference id for meeting ID {meeting_id}"
            )

        if not presenter_details:
            raise PresenterDetailsMissingError(
                f"Presenter details are missing for meeting ID {meeting_id}"
            )

        try:
            teams_service = MSTeamsConferencePlatformService()
            teams_service.delete_meeting(
                presenter=presenter_details, meeting_id=conference_id
            )
            logger.info(f"Deleted meeting {meeting_id}")

        except Exception as e:
            logger.error(
                f"Failed to delete Teams meeting for meeting ID {meeting_id}: {str(e)}"
            )
            raise

    def update_teams_meeting(meeting_id: int) -> None:
        """
        Creates a Teams meeting for a given meeting ID
        """
        meeting = MeetingRepository.get_meeting_by_id(meeting_id)

        if not meeting:
            raise MeetingNotFoundError(f"Meeting with ID {meeting_id} not found")

        if not meeting.series.presenter_details:
            raise PresenterDetailsMissingError(
                f"Presenter details are missing for meeting ID {meeting_id}"
            )

        if not meeting.conference_id:
            raise ConferenceIDMissingError(
                f"missing conference id for meeting ID {meeting_id}"
            )

        try:
            teams_service = MSTeamsConferencePlatformService()
            # Create Teams meeting using model properties
            meeting_details = teams_service.update_meeting(
                presenter=meeting.series.presenter_details,
                start_time=meeting.start_time,
                end_time=meeting.end_time,
                subject=meeting.title,
                meeting_id=meeting.conference_id,
            )
            # Update meeting with Teams details
            meeting.link = meeting_details.join_url
            meeting.conference_metadata = meeting_details.all_details
            meeting.conference_id = meeting_details.id

            # Temporarily disconnect signals
            post_save.disconnect(meeting_post_save, sender=Meeting)

            # Save the meeting without triggering signals
            with transaction.atomic():
                meeting.save()

        except Exception as e:
            logger.error(
                f"Failed to create Teams meeting for meeting ID {meeting_id}: {str(e)}"
            )
            raise

    def fetch_teams_meeting_recording(meeting_id: str) -> None:
        """
        Fetches Teams meeting recordings for a meeting
        """

        meeting = MeetingRepository.get_meeting_by_id(meeting_id)

        if not meeting:
            raise MeetingNotFoundError(f"Meeting with ID {meeting_id} not found")

        if not meeting.series.presenter_details:
            raise PresenterDetailsMissingError(
                f"Presenter details are missing for meeting ID {meeting_id}"
            )

        if not meeting.conference_id:
            raise ConferenceIDMissingError(
                f"missing conference id for meeting ID {meeting_id}"
            )

        try:
            teams_service = MSTeamsConferencePlatformService()

            recording_by_thread = teams_service.get_meetings_recordings(
                presenter=meeting.series.presenter_details, meeting=meeting
            )

            if len(recording_by_thread) == 0:
                logger.info(f"No recordings found for meeting {meeting_id}")
                return

            meeting.recording_metadata = recording_by_thread
            logger.info(
                f"Recording data saved for meeting {meeting.recording_metadata}"
            )
            # Temporarily disconnect signals
            post_save.disconnect(meeting_post_save, sender=Meeting)

            # Save the meeting without triggering signals
            with transaction.atomic():
                meeting_to_update = Meeting.objects.select_for_update().get(
                    id=meeting_id
                )
                meeting_to_update.recording_metadata = recording_by_thread
                meeting_to_update.save()

        except Exception as e:
            logger.error(
                f"Failed to fetch Teams recordings for meeting ID {meeting_id}: {str(e)}"
            )
            raise

    def upload_meeting_recording_to_storage(meeting_id: int) -> str:
        """
        Downloads a meeting recording from Teams and uploads it to Azure Blob Storage.
        Creates an entry in the recordings table.

        Args:
            meeting_id (int): The meeting ID

        Returns:
            str: The blob URL with SAS token
        """
        meeting = MeetingRepository.get_meeting_by_id(meeting_id)

        if not meeting or not meeting.recording_metadata:
            raise MeetingNotFoundError(
                f"Meeting {meeting_id} not found or has no recordings"
            )

        try:
            # Get recording metadata
            recording_data = meeting.recording_metadata

            # Download and upload using Teams service
            teams_service = MSTeamsConferencePlatformService()
            blob_url = teams_service.download_and_upload_recording(
                meeting_id=meeting_id,
                recording_metadata=recording_data,
                container_name=settings.RECORDINGS_CONTAINER_NAME,
            )

            meeting.blob_url = blob_url
            # Temporarily disconnect signals
            post_save.disconnect(meeting_post_save, sender=Meeting)

            # Save the meeting without triggering signals
            with transaction.atomic():
                meeting_to_update = Meeting.objects.select_for_update().get(
                    id=meeting_id
                )
                meeting_to_update.blob_url = blob_url
                meeting_to_update.save()

            return blob_url

        except Exception as e:
            logger.error(
                f"Error processing recording for meeting {meeting_id}: {str(e)}"
            )
            raise

    def fetch_teams_meeting_attendance(meeting_id: int) -> None:
        """
        Fetches Teams meeting attendance for a specific meeting and stores it in the database
        """
        meeting = MeetingRepository.get_meeting_by_id(id=meeting_id)

        if not meeting:
            raise MeetingNotFoundError(f"Meeting with ID {meeting_id} not found")

        if not meeting.series.presenter_details:
            raise PresenterDetailsMissingError(
                f"Presenter details are missing for meeting ID {meeting_id}"
            )

        if not meeting.conference_id:
            raise ConferenceIDMissingError(
                f"Missing conference id for meeting ID {meeting_id}"
            )

        try:
            teams_service = MSTeamsConferencePlatformService()

            # Get attendance data from Teams
            attendance_data = teams_service.get_meeting_attendance(
                presenter=meeting.series.presenter_details,
                meeting_id=meeting.conference_id,
            )

            # Update meeting with attendance data
            meeting.attendance_metadata = attendance_data

            # Temporarily disconnect signals
            post_save.disconnect(meeting_post_save, sender=Meeting)

            # Save the meeting without triggering signals
            with transaction.atomic():
                meeting_to_update = Meeting.objects.select_for_update().get(
                    id=meeting_id
                )
                meeting_to_update.attendance_metadata = attendance_data
                meeting_to_update.save()

            logger.info(f"Attendance data saved for meeting {meeting_id}")

        except Exception as e:
            logger.error(
                f"Failed to fetch Teams attendance for meeting ID {meeting_id}: {str(e)}"
            )
            raise

    @staticmethod
    def update_meeting(id, start_time_override, duration_override, start_date):
        """
        Update meeting details and handle notification updates if timing changes
        """
        meeting = MeetingRepository.get_meeting_by_id(id)

        # Check if date or time is changing
        time_changed = (start_time_override != meeting.start_time_override) or (
            duration_override != meeting.duration_override
        )
        date_changed = start_date != meeting.start_date

        # If either time or date changed, update notification schedules
        if time_changed or date_changed:
            # Calculate new meeting start datetime in IST
            ist_tz = pytz.timezone("Asia/Kolkata")
            new_start_time = start_time_override or meeting.series.start_time
            new_start_datetime_ist = ist_tz.localize(
                datetime.combine(start_date, new_start_time)
            )

            # Convert to UTC for database storage
            new_start_datetime_utc = new_start_datetime_ist.astimezone(pytz.UTC)
            current_time_utc = timezone.now()

            # Update pending notification schedules
            pending_intents = (
                NotificationIntentRepository.get_pending_intents_by_reference(
                    reference_id=id, notification_types=["meeting_24h", "meeting_30m"]
                )
            )

            for intent in pending_intents:
                if intent.notification_type == "meeting_24h":
                    new_scheduled_time = new_start_datetime_utc - timedelta(hours=24)
                elif intent.notification_type == "meeting_30m":
                    new_scheduled_time = new_start_datetime_utc - timedelta(minutes=30)

                # Only update if the notification time is in the future
                if new_scheduled_time > current_time_utc:
                    NotificationIntentRepository.update_intent_schedule(
                        intent_id=intent.id, scheduled_at=new_scheduled_time
                    )

        # Update meeting details
        meeting.start_time_override = start_time_override
        meeting.duration_override = duration_override
        meeting.start_date = start_date
        meeting.save()

    @staticmethod
    def delete_meeting(id):
        meeting = MeetingRepository.get_meeting_by_id(id)
        # Delete all associated notification intents
        NotificationIntentRepository.delete_intents_by_reference(
            reference_id=id,
            notification_types=[
                "meeting_24h",
                "meeting_30m",
            ],
        )
        meeting.delete()

    @staticmethod
    def get_meetings_of_series_in_period(series_id, start_date, end_date):
        meetings = MeetingRepository.get_meetings_of_series_in_period(
            series_id, start_date, end_date
        )
        meetings_data = []
        for meeting in meetings:
            # Combine date and time for start_time
            start_datetime = meeting.start_time
            end_datetime = meeting.end_time
            meetings_data.append(
                {
                    "type": 0,
                    "title": meeting.series.title,
                    "meeting_id": meeting.id,
                    "series_id": meeting.series_id,
                    "start_date": meeting.start_date,
                    "start_timestamp": start_datetime,
                    "end_timestamp": end_datetime,
                    "link": meeting.link,
                    "start_time": (
                        meeting.start_time_override
                        if meeting.start_time_override
                        else meeting.series.start_time
                    ),
                    "duration": (
                        meeting.duration_override
                        if meeting.duration_override
                        else meeting.series.duration
                    ),
                    "batch": meeting.batch.title if meeting.batch else None,
                    "course": meeting.course.title if meeting.course else None,
                }
            )
        return meetings_data

    def get_meeting_by_id(meeting_id):
        meeting = MeetingRepository.get_meeting_by_id(meeting_id)
        data = {
            "title": meeting.series.title,
            "meeting_id": meeting.id,
            "series_id": meeting.series_id,
            "start_date": meeting.start_date,
            "link": meeting.link,
            "start_time": (
                meeting.start_time_override
                if meeting.start_time_override
                else meeting.series.start_time
            ),
            "duration": (
                meeting.duration_override
                if meeting.duration_override
                else meeting.series.duration
            ),
        }
        return data

    def get_recordings_by_user_role(user_id: int, role: str):
        """
        Get recordings based on user role and permissions

        Args:
            user_id (int): ID of the user requesting recordings
            role (str): Role of the user (user/lecturer/course_provider_admin)

        Returns:
            list: List of recordings with metadata
        """
        meetings = MeetingRepository.get_meetings_with_recordings_by_role(user_id, role)

        recordings_data = []
        for meeting in meetings:
            recordings_data.append(
                {
                    "meeting_id": meeting.id,
                    "meeting_title": meeting.series.title,
                    "meeting_date": (
                        meeting.start_date.strftime("%Y-%m-%d")
                        if meeting.start_date
                        else None
                    ),
                    "course_id": meeting.course.id if meeting.course else None,
                    "course_name": meeting.course.title if meeting.course else None,
                    "batch_id": meeting.batch.id if meeting.batch else None,
                    "batch_name": meeting.batch.title if meeting.batch else None,
                    "blob_url": meeting.blob_url,
                    "additional_recordings": meeting.additional_recordings,
                }
            )

        if not recordings_data:
            return []

        return recordings_data

    def get_sas_url_for_recording(meeting_blob_url: str):
        clean_url = meeting_blob_url.split("?")[0]
        # Parse the URL
        parsed_url = urllib.parse.urlparse(clean_url)
        # Split the path and remove empty strings
        path_parts = [p for p in parsed_url.path.split("/") if p]
        # First part is container name, rest is blob name
        container_name = path_parts[0]
        blob_name = "/".join(path_parts[1:]).replace("%20", " ")

        # Determine content type based on file extension
        content_type = None
        file_extension = blob_name.lower().split(".")[-1] if "." in blob_name else ""

        content_types = {
            "pdf": "application/pdf",
            "mp4": "video/mp4",
            "mov": "video/quicktime",
            "doc": "application/msword",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "xls": "application/vnd.ms-excel",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "ppt": "application/vnd.ms-powerpoint",
            "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
        }

        content_type = content_types.get(file_extension, "application/octet-stream")

        sas_url = storage_service.generate_blob_access_url(
            container_name,
            blob_name,
            expiry_time=datetime.now() + timedelta(hours=24),
            allow_read=True,
            allow_write=False,
            content_type=content_type,
        )
        return sas_url

    @staticmethod
    def upload_additional_recording(meeting_id: int, filename: str) -> str:
        """
        Uploads an additional recording for a meeting

        Args:
            meeting_id (int): Meeting ID
            file_content (bytes): Content of the video file
            filename (str): Name of the file
            content_type (str): Content type of the file

        Returns:
            str: The blob URL of the uploaded recording
        """
        meeting = MeetingRepository.get_meeting_by_id(meeting_id)

        if not meeting:
            raise MeetingNotFoundError(f"Meeting with ID {meeting_id} not found")

        try:
            from course.usecases import CourseContentDriveUsecase

            # Create blob path for additional recording
            blob_path = f"meetings/{meeting.course.code if meeting.course else 'general'}/{meeting.id}/additional_recordings/{filename}"

            # Upload to blob storage
            blob_url = AssessmentUseCase.fetch_azure_storage_url(
                blob_name=blob_path, container_name=settings.RECORDINGS_CONTAINER_NAME
            )

            # Update meeting's additional_recordings
            if not meeting.additional_recordings:
                meeting.additional_recordings = []

            recording_info = {
                "filename": filename,
                "blob_url": blob_url,
                "uploaded_at": timezone.now().isoformat(),
            }

            # Add new recording to the list
            meeting.additional_recordings.append(recording_info)

            # Save meeting
            with transaction.atomic():
                meeting.save()

            return blob_url

        except Exception as e:
            logger.error(
                f"Error uploading additional recording for meeting {meeting_id}: {str(e)}"
            )
            raise

    @staticmethod
    def delete_recording(blob_url: str) -> None:
        """
        Delete a recording by its blob URL and update the meeting record

        Args:
            blob_url (str): The blob URL of the recording to delete
        """
        # Delete from Azure storage first
        storage_service = AzureStorageService()
        storage_service.delete_blob(blob_url)

        # Find meeting by blob URL
        meeting = Meeting.objects.filter(blob_url=blob_url).first()
        if meeting:
            meeting.blob_url = None
            meeting.save()
            return

        # Look in additional recordings if not found in main blob_url
        meetings = Meeting.objects.filter(
            additional_recordings__contains=[{"blob_url": blob_url}]
        )
        for meeting in meetings:
            meeting.additional_recordings = [
                r
                for r in meeting.additional_recordings
                if r.get("blob_url") != blob_url
            ]
            meeting.save()

    def create_attendace_records(meeting):
        participants = meeting.get_participants
        AttendaceRecordRepository.create_attendance_records(meeting, participants)
        logger.info(f"created attendance records for meeting {meeting.id}")


class MeetingAttendanceUseCase:
    def mark_meeting_attendance(attendance_id):
        attendance_record = AttendaceRecordRepository.get_attendance_record(
            attendance_id
        )
        if attendance_record is not None:
            # Check if the meeting's start date is today
            meeting_link = attendance_record.meeting.link
            if attendance_record.meeting.start_date == timezone.now().date():
                AttendaceRecordRepository.mark_attendance(attendance_record)

                return meeting_link
            else:
                return meeting_link

    def mark_meeting_attendance_common_link(reference_id):
        user_id = CryptographyHandler.decrypt_user_id(reference_id)
        user = User.objects.get(id=user_id)
        next_meeting_for_user = MeetingRepository.get_next_meeting_for_user(user_id)
        logger.info(f"next meeting for user  {next_meeting_for_user}")
        if next_meeting_for_user is not None:
            meeting_id = next_meeting_for_user.get("meeting_id")
            meeting_link = next_meeting_for_user.get("meeting_link")
            # Get or create attendance record
            attendance_record, created = (
                AttendaceRecordRepository.get_or_create_attendance_record(
                    user_id=user, meeting_id=meeting_id
                )
            )
            attendance_record = (
                AttendaceRecordRepository.get_attendance_record_by_user_and_meeting_id(
                    user_id, meeting_id
                )
            )
            meeting_link = attendance_record.meeting.link
            if attendance_record.meeting.start_date == timezone.now().date():
                AttendaceRecordRepository.mark_attendance(attendance_record)
                return meeting_link
            else:
                return meeting_link

    def get_common_joining_url(user_id):
        encrypted_user_id = CryptographyHandler.encrypt_user_id(user_id)
        joining_url = (
            f"{settings.BACKEND_BASE_URL}/en/meeting/join-meeting/{encrypted_user_id}/"
        )

        return joining_url

    def get_joining_url(user_id, meeting_id):
        user = User.objects.get(id=user_id)
        # Get or create attendance record
        attendance_record, created = (
            AttendaceRecordRepository.get_or_create_attendance_record(
                user_id=user, meeting_id=meeting_id
            )
        )

        # Generate joining URL
        joining_url = f"{settings.BACKEND_BASE_URL}/en/meeting/join/{attendance_record.attendance_id}/"

        return joining_url
