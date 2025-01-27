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
    
    @staticmethod
    def create_bulk_meetings(meeting_objects):
        return Meeting.objects.bulk_create(meeting_objects)

    @staticmethod
    def get_meetings_by_series_id(series_id) -> typing.List[Meeting]:
        return list(Meeting.objects.filter(series_id=series_id))

    @staticmethod
    def get_meeting_by_id(id) -> Meeting:
        return Meeting.objects.get(id=id)
    
    def get_no_of_meetings_occured_in_course(course_id,batch_id,date):
        return Meeting.objects.filter(series__course_enrollments__batch__course_id=course_id,series__course_enrollments__batch__id=batch_id,start_date__lte=date).count()

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
            if meeting_end_time+timedelta(hours=1) <= now:
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
    
    def get_completed_meetings_in_past_24_hours_with_recordings():
        now = datetime.now(ist)
        potential_meetings = Meeting.objects.filter(
            start_date=(now - timedelta(hours=24)).date(),
            blob_url__isnull=False,  
            blob_url__gt=''
        ).select_related("series")
        return potential_meetings
    
    def get_meetings_in_time_range(start_time, end_time):
        return Meeting.objects.filter(
            start_date__range=(start_time, end_time)
        ).select_related("series")

    
    def get_next_meeting_for_user(user_id: int):
        """
        Get the next meeting aligned for a user along with its link.
        
        Args:
            user_id (int): The user's ID
        
        Returns:
            dict: A dictionary containing meeting details or None if no upcoming meeting.
        """
        # Get the current time
        now = datetime.now(ist)
        now_date=now.date()
        date_after_one_day=now.date()+timedelta(days=3)
        # Find the next meeting for the user
        # Get all meetings for the courses the user is enrolled in
        upcoming_meetings = Meeting.objects.filter(
            Q(series__course_enrollments__batch__student__student_id=user_id) | 
            Q(series__course_enrollments__batch__lecturer_id=user_id),
            start_date__gte=now_date,  # Only future meetings
            start_date__lte=date_after_one_day
            
        ).order_by('start_date')[:10]
        
        # Iterate through the meetings to check if the meeting has not yet finished
        for meeting in upcoming_meetings:
            # Calculate the meeting's end time by adding the duration to the start time
            end_time = meeting.end_time.astimezone(ist) if meeting.end_time.tzinfo else ist.localize(meeting.end_time)
            # Check if the meeting has finished or not
            if end_time > now:
                return {'meeting_id':meeting.id,'meeting_link':meeting.link}
        
        # If no meeting has yet to finish, return None
        return None


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
    def get_attendance_record_by_user_and_meeting_id(user_id,meeting_id):
        return AttendanceRecord.objects.filter(user_id_id=user_id,meeting_id=meeting_id).first()

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
    def get_total_classes_attended_by_user_for_course(user_id: int, course_id: int,batch_id:int) -> dict:
        """
        Get total classes attended by a user for a specific course.
        """
        # Get all meetings for this course
        meetings = Meeting.objects.filter(
            series__course_enrollments__batch__course_id=course_id,
            series__course_enrollments__batch_id=batch_id,
            start_date__lt=datetime.now().date()
        )
        
        # Get existing attendance records
        attendance_records = AttendanceRecord.objects.filter(
            meeting__series__course_enrollments__batch__course_id=course_id,
            meeting__series__course_enrollments__batch_id=batch_id,
            user_id=user_id
        )
        
        # Create a map of meeting_id to attendance record
        attendance_map = {record.meeting_id: record for record in attendance_records}
        
        # Count attendance
        attended_classes = 0
        total_classes = len(meetings)
        
        for meeting in meetings:
            if meeting.id in attendance_map:
                if attendance_map[meeting.id].attendance:
                    attended_classes += 1
            else:
                # If no record exists, count as absent
                pass
                
        # Calculate attendance percentage
        attendance_percentage = 0
        if total_classes > 0:
            attendance_percentage = round((attended_classes / total_classes) * 100, 2)
            
        return {
            'classes_attended': attended_classes,
            'total_classes': total_classes,
            'attendance_percentage': attendance_percentage
        }
        
    @staticmethod
    def get_attended_meetings_for_user_on_day(user_id: int, course_id: int, date: str) -> list:
        """
        Get all meetings for a user on a specific day, including those without attendance records.
        
        Args:
            user_id (int): The user's ID
            course_id (int): The course ID
            date (str): The date in YYYY-MM-DD format
            
        Returns:
            list: List of dictionaries containing meeting details and attendance status
        """
        # Get all meetings for the course on the specified date
        meetings = Meeting.objects.filter(
            series__course_enrollments__batch__course_id=course_id,
            start_date=date
        ).select_related('series')
        
        # Get existing attendance records
        attendance_records = AttendanceRecord.objects.filter(
            meeting__in=meetings,
            user_id=user_id
        ).select_related('meeting')
        
        # Create a map of meeting_id to attendance record
        attendance_map = {record.meeting_id: record for record in attendance_records}
        
        meetings_list = []
        for meeting in meetings:
            # Check if user is a participant in this meeting
            if user_id in [p.id for p in meeting.get_participants]:
                attendance_record = attendance_map.get(meeting.id)
                
                meetings_list.append({
                    'meeting_id': meeting.id,
                    'meeting_title':meeting.title,
                    'course_id': meeting.course.id if meeting.course else None,
                    # If no attendance record exists or attendance is False, duration is 0
                    'duration': meeting.duration if attendance_record and attendance_record.attendance else timedelta(0)
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

    @staticmethod
    def get_completed_meetings_in_past_24_hours_with_recordings():
        """
        Get meetings that:
        1. Have ended (based on start_time + duration)
        2. Have recording_metadata
        3. Haven't sent absent notifications yet
        """
        now = datetime.now(ist)
        potential_meetings = Meeting.objects.filter(
            start_date=(now - timedelta(hours=24)).date(),
            blob_url__isnull=False,  
            blob_url__gt=''
        ).select_related("series")
        return potential_meetings
    
    @staticmethod
    def get_absent_users_for_meeting(meeting_id):
        """Get all users who were absent for a specific meeting with their full names"""
        # Get the meeting
        meeting = Meeting.objects.get(id=meeting_id)
        
        # Get all participants for the meeting
        participants = meeting.get_participants
        
        # Get existing attendance records
        existing_records = AttendanceRecord.objects.filter(
            meeting_id=meeting_id
        ).select_related('user_id')
        
        # Create a map of user_id to attendance record
        attendance_map = {record.user_id_id: record for record in existing_records}
        
        # Build list of all attendance records, including virtual ones for missing records
        absent_records = []
        for participant in participants:
            if participant.id in attendance_map:
                # Use existing record if it exists
                record = attendance_map[participant.id]
                if not record.attendance:  # Only include if marked as absent
                    absent_records.append(record)
            else:
                # Create a virtual attendance record for users without one
                virtual_record = AttendanceRecord(
                    meeting_id=meeting_id,
                    user_id=participant,
                    attendance=False
                )
                absent_records.append(virtual_record)
        
        return absent_records