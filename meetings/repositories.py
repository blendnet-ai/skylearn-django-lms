from meetings.models import Meeting, MeetingSeries
import typing
from django.core.exceptions import ValidationError
from django.db import IntegrityError, DatabaseError
from datetime import datetime, timedelta, timezone
import pytz
from django.db.models import Q

# Define the Indian timezone
ist = pytz.timezone('Asia/Kolkata')


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
        
    @staticmethod
    def get_series_by_presenter_details_guid(presenter_details_guid):
        return MeetingSeries.objects.filter(presenter_details__guid=presenter_details_guid)
        


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
    def get_meetings_completed_within_last_hour():
        # Get current time in IST
        now = datetime.now(ist)
        
        # Calculate the time threshold for one hour ago
        one_hour_ago = now - timedelta(hours=1)
        
        # Fetch potential meetings from the last 24 hours
        potential_meetings = Meeting.objects.filter(
            start_date__gt=now - timedelta(hours=24)
        ).select_related("series")
        
        # Filter in Python using the end_time property
        completed_meetings = []
        for meeting in potential_meetings:
            meeting_end_time = meeting.end_time.astimezone(ist) if meeting.end_time.tzinfo else ist.localize(meeting.end_time)
            
            # Check if the meeting ended within the last hour
            if meeting_end_time >= one_hour_ago and meeting_end_time <= now:
                completed_meetings.append(meeting)
                
        return completed_meetings

    @staticmethod
    def get_meetings_by_course_id_and_batch_id(course_id,batch_id):
        """
        Get all meetings associated with a specific course ID
        
        Args:
            course_id: The ID of the course to find meetings for
            
        Returns:
            List of Meeting objects associated with the course
        """
        return list(Meeting.objects.filter(
            series__in=MeetingSeries.objects.filter(
                course_enrollments__batch__course_id=course_id,
                course_enrollments__batch__id=batch_id
            ),
            blob_url__isnull=False,
            blob_url__gt=''
        ).distinct())

    def get_meetings_with_recordings_by_role(user_id: int, role:str):
        """
        Get meetings with recordings based on user role

        Args:
            user_id (int): ID of the user requesting recordings
            role (str): Role of the user (student/lecturer/course_provider_admin)

        Returns:
            QuerySet: Filtered meetings with recordings
        """
        # Base query - only get meetings that have recordings
        base_query = Meeting.objects.filter(blob_url__isnull=False).exclude(blob_url='')

        if role == 'student':
            # Get recordings for courses where student is enrolled in a batch
            return base_query.filter(
                series__course_enrollments__batch__student__student_id=user_id
            ).distinct()

        elif role == 'lecturer':
            # Get recordings for all batches where user is the lecturer
            return base_query.filter(
                Q(series__course_enrollments__batch__lecturer_id=user_id)
            ).distinct()

        elif role == 'course_provider_admin':
            return base_query.filter(
                series__course_enrollments__batch__course__course_provider__admins__course_provider_admin_id=user_id
            ).distinct()

        return Meeting.objects.none()

    @staticmethod
    def get_meetings_in_time_range(start_time, end_time):
        return Meeting.objects.filter(start_date__range=(start_time, end_time)).select_related("series")

