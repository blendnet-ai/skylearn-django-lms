from meetings.models import Meeting, MeetingSeries
import typing
from django.core.exceptions import ValidationError
from django.db import IntegrityError, DatabaseError
from datetime import datetime, timedelta, timezone


class MeetingSeriesRepository:
    @staticmethod
    def create_meeting_series(
        title,
        start_time,
        start_date,
        duration,
        end_date,
        recurrence_type,
        weekday_schedule,
        monthly_day,
    ):
        return MeetingSeries.objects.create(
            title=title,
            start_time=start_time,
            start_date=start_date,
            duration=duration,
            end_date=end_date,
            recurrence_type=recurrence_type,
            weekday_schedule=weekday_schedule,
            monthly_day=monthly_day,
        )

    @staticmethod
    def update_meeting_series(
        meeting_series,
        title,
        start_time,
        duration,
        end_date,
        recurrence_type,
        weekday_schedule,
        monthly_day,
    ):
        meeting_series.title = title
        meeting_series.start_time = start_time
        meeting_series.duration = duration
        meeting_series.end_date = end_date
        meeting_series.recurrence_type = recurrence_type
        meeting_series.weekday_schedule = weekday_schedule
        meeting_series.monthly_day = monthly_day
        meeting_series.save()

    @staticmethod
    def get_meeting_series_by_id(id):
        return MeetingSeries.objects.get(id=id)
    
    @staticmethod
    def add_presenter_details_to_meeting_series(meeting_series,presenter_details):
        meeting_series.presenter_details=presenter_details
        meeting_series.save()
        


class MeetingRepository:
    @staticmethod
    def create_meeting(series, start_date, link):
        return Meeting.objects.create(series=series, start_date=start_date, link=link)

    @staticmethod
    def get_meetings_by_series_id(series_id) -> typing.List[Meeting]:
        return list(Meeting.objects.filter(series_id=series_id))

    @staticmethod
    def get_meeting_by_id(id) -> Meeting:
        return Meeting.objects.get(id=id)

    @staticmethod
    def get_meetings_of_series_in_period(series_id, start_date, end_date):
        return Meeting.objects.filter(
            start_date__range=(start_date, end_date), series_id=series_id
        ).select_related("series")


    @staticmethod
    def get_attendance_details_pending_meetings():
        current_date = timezone.now().date()  # Get the current date
        # Create a naive datetime for the end of the current day
        end_of_day = datetime.combine(current_date, datetime.max.time())  # End of the current day (naive)

        # Fetch all meetings
        meetings = Meeting.objects.all()

        # Filter meetings
        pending_meetings = [
            meeting.id for meeting in meetings
            if meeting.end_time.replace(tzinfo=None) < end_of_day and meeting.attendance_reports is None
        ]

        return pending_meetings

    @staticmethod
    def get_recordings_pending_meetings():
        current_date = timezone.now().date()  # Get the current date
        # Create a naive datetime for the end of the current day
        end_of_day = datetime.combine(current_date, datetime.max.time())  # End of the current day (naive)

        # Fetch all meetings
        meetings = Meeting.objects.all()

        # Filter meetings 
        pending_meetings = [
            meeting.id for meeting in meetings
            if meeting.end_time.replace(tzinfo=None) < end_of_day and meeting.recordings is None
        ]

        return pending_meetings

