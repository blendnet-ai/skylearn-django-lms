from meetings.models import Meeting, MeetingSeries,AttendanceRecord
import typing
from django.core.exceptions import ValidationError
from django.db import IntegrityError, DatabaseError
from datetime import datetime, timedelta, timezone
import pytz
from django.db.models import Q,Count

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
    
    def create_bulk_meetings(meeting_objects):
        return Meeting.objects.bulk_create(meeting_objects)

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

class AttendaceRecordRepository:
    @staticmethod
    def create_attendance_records(meeting, participants):
        """
        Create attendance records for all participants for a given meeting.
        
        :param meeting: The Meeting instance for which attendance records are created.
        :param participants: A list of dictionaries containing participant details, 
                            each with a 'user_id' key.
        """
        attendance_records = []
        print("asdd",participants)
        for participant in participants:
            attendance_record = AttendanceRecord(
                meeting=meeting,
                user_id=participant,
                attendance=False
            )
            attendance_records.append(attendance_record)
        
        # Bulk create attendance records to optimize database operations
        AttendanceRecord.objects.bulk_create(attendance_records)
    
    @staticmethod
    def get_attendance_record(attendance_id):
        return AttendanceRecord.objects.filter(attendance_id=attendance_id).first()

    @staticmethod
    def mark_attendance(attendance_record):
        attendance_record.attendance = True
        attendance_record.save()
        return attendance_record

    @staticmethod
    def get_or_create_attendance_record(user_id, meeting_id):
        return AttendanceRecord.objects.get_or_create(
            user_id=user_id,
            meeting_id=meeting_id
        )
        
    @staticmethod
    def get_total_classes_attended_by_user_for_course(user_id: int, course_id: int) -> dict:
        """
        Get total classes attended by a user for a specific course.
        
        Args:
            user_id (int): ID of the user
            course_id (int): ID of the course
            
        Returns:
            dict: Contains total classes attended and total classes held
            Example: {
                'classes_attended': 10,
                'total_classes': 15,
                'attendance_percentage': 66.67
            }
        """
        
        # Get all attendance records for meetings in this course's batches
        total_classes = AttendanceRecord.objects.filter(
            meeting__series__course_enrollments__batch__course_id=course_id,
            user_id=user_id
        ).count()
        
        # Get count of attended classes
        attended_classes = AttendanceRecord.objects.filter(
            meeting__series__course_enrollments__batch__course_id=course_id,
            user_id=user_id,
            attendance=True
        ).count()
        
        # Calculate attendance percentage
        attendance_percentage = 0
        if total_classes > 0:
            attendance_percentage = round((attended_classes / total_classes) * 100, 2)
            
        return {
            'classes_attended': attended_classes,
            'total_classes': total_classes,
            'attendance_percentage': attendance_percentage
        }
        
    
    def get_attended_meetings_for_user_on_day(user_id: int, course_id:int, date: datetime) -> list:
        """
        Get all meetings attended by a user on a specific day.

        Args:
            user_id (int): ID of the user
            date (datetime): Date for which to fetch attended meetings

        Returns:
            list: List of meetings attended by the user on the specified date
        """
        # Filter attendance records for the user on the specified date
        attended_meetings = AttendanceRecord.objects.filter(
            user_id=user_id,
            meeting__start_date=date,
            meeting__series__course_enrollments__batch__course_id=course_id
        )

        # Convert the QuerySet to a list of dictionaries containing meeting details
        meetings_list = []
        for record in attended_meetings:
            meeting = record.meeting
            meetings_list.append({
                'meeting_id': meeting.id,
                'meeting_title':meeting.title,
                'course': meeting.course.id if meeting.course else None,
                'duration':meeting.duration if record.attendance else timedelta(0)
            })

        return meetings_list

    @staticmethod
    def get_all_attendance_records_data():
        """
        Get all attendance records with associated meeting and batch information.
        
        Returns:
            QuerySet of AttendanceRecord instances with related Meeting and Series.
        """
        return AttendanceRecord.objects.filter(
            meeting__series__course_enrollments__isnull=False  # Only records for enrolled courses
        ).select_related('meeting', 'meeting__series').distinct()
        
    @staticmethod
    def get_attendance_records_by_date(target_date):
        """
        Get attendance records for a specific date with associated meeting and batch information.
        
        Args:
            target_date (date): The date to filter attendance records for
                
        Returns:
            QuerySet of AttendanceRecord instances with related Meeting and Series.
        """
        return AttendanceRecord.objects.filter(
            meeting__series__course_enrollments__isnull=False,
            meeting__start_date=target_date
        ).select_related('meeting', 'meeting__series').distinct()

