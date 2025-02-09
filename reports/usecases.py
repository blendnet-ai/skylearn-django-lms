# reports/usecases/generate_user_course_reports.py

from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from accounts.repositories import StudentRepository
from evaluation.repositories import AssessmentAttemptRepository
from meetings.repositories import AttendaceRecordRepository, MeetingRepository
from events_logger.repositories import PageEventRepository
from .repositories import UserCourseReportRepository, DailyAggregationRepository
from evaluation.repositories import AssessmentAttemptRepository
from meetings.repositories import AttendaceRecordRepository
from events_logger.repositories import PageEventRepository

User = get_user_model()

class GenerateUserCourseReportsUseCase:
    @staticmethod
    def generate_report(user_id):
        """
        Generate or update UserCourseReport records for all courses associated with a user.
        
        Args:
            user_id: The ID of the user to generate reports for
            
        Returns:
            list: List of (UserCourseReport object, created boolean) tuples
        """
        user = User.objects.get(id=user_id)
        date=datetime.now().date()
        reports = []

        if not user.is_student:
            return reports

        courses = GenerateUserCourseReportsUseCase._get_user_courses(user_id)
        batch_to_course_mapping = GenerateUserCourseReportsUseCase._get_mapping_of_batch_to_course(user_id)
        print("batch_to_course_mapping",batch_to_course_mapping)
        for course in courses:
            batch_id = batch_to_course_mapping.get(course.id)
            print("batch_id",batch_id,"date",date,"course_id",course.id)
            no_of_meetings = MeetingRepository.get_no_of_meetings_occured_in_course(course.id,batch_id,date)
            print("no_of_meetings",no_of_meetings)
            activites = DailyAggregationRepository.get_aggregations_by_user(user_id,course.id)
            report=GenerateUserCourseReportsUseCase._create_or_update_course_report(user,activites,course,no_of_meetings)
            reports.append(report)

        return reports

    def _get_user_courses(user_id):
        student = StudentRepository.get_student_by_student_id(user_id)
        if not student:
            return []
            
        batches = student.batches.all()
        return [batch.course for batch in batches]
    
    def _get_mapping_of_batch_to_course(user_id):
        student = StudentRepository.get_student_by_student_id(user_id)
        if not student:
            return []
            
        batches = student.batches.all()
        return {batch.course_id:batch.id for batch in batches}

    def _create_or_update_course_report(user, daily_activites,course,no_of_meetings):
        assessment_time=timedelta(0)
        resource_reading_time=timedelta(0)
        resource_video_time=timedelta(0)
        time_spent_live_classes=timedelta(0)
        time_spent_recording_classes=timedelta(0)
        total_classes=no_of_meetings
        total_classes_attended=0
        
        for activity in daily_activites:
            if activity.type_of_aggregation=="assessment":
                assessment_time=assessment_time+activity.time_spent
            elif activity.type_of_aggregation=="resource_reading":
                resource_reading_time=resource_reading_time+activity.time_spent
            elif activity.type_of_aggregation=="resource_video":
                resource_video_time=resource_video_time+activity.time_spent
            elif activity.type_of_aggregation=="live_class":
                if activity.time_spent != timedelta(0):
                    #Here time zero means that the class was not attended hence we are not counting it for attendance
                    time_spent_live_classes=time_spent_live_classes+activity.time_spent
                    total_classes_attended+=1;
                else:
                    pass
            elif activity.type_of_aggregation=="resource_recording":
                time_spent_recording_classes=time_spent_recording_classes+activity.time_spent
                    
            

        defaults = {
            'assessment_time': assessment_time,
            'resource_time_reading': resource_reading_time,
            'resource_time_video':resource_video_time,
            'total_classes': total_classes,
            'classes_attended': total_classes_attended,
            'time_spent_in_live_classes':time_spent_live_classes,
            'time_spent_in_recording_classes':time_spent_recording_classes,
            'total_time_spent': time_spent_live_classes + resource_reading_time+resource_video_time+time_spent_recording_classes+assessment_time
        }

        return UserCourseReportRepository.get_or_create(
            user_id=user.id,
            course=course,
            defaults=defaults
        )


class DailyAggregationUsecase:
    @staticmethod
    def create_daily_aggregation_entries_for_user(user_id, date):
        courses = GenerateUserCourseReportsUseCase._get_user_courses(user_id)

        for course in courses:
            DailyAggregationUsecase._aggregate_assessments(user_id, course.id, date)
            DailyAggregationUsecase._aggregate_meetings(user_id, course.id, date)
            DailyAggregationUsecase._aggregate_resources(user_id, course.id, date)

    @staticmethod
    def _aggregate_assessments(user_id, course_id, date):
        attempts = AssessmentAttemptRepository.fetch_daily_assessments_with_time_spent(user_id=user_id, course_id=course_id, date=date)
        for attempt in attempts:
            DailyAggregationRepository.get_or_create_daily_aggregation(
                user_id=user_id,
                date=date,
                course_id=course_id,
                type_of_aggregation='assessment',
                time_spent=attempt.get('test_duration'),
                reference_id=attempt.get('assessment_id'),
                resource_name=attempt.get('assessment_generation_config_id__assessment_display_name')
            )

    @staticmethod
    def _aggregate_meetings(user_id, course_id, date):
        live_classes = AttendaceRecordRepository.get_attended_meetings_for_user_on_day(user_id=user_id, course_id=course_id, date=date)
        for meeting in live_classes:
            DailyAggregationRepository.get_or_create_daily_aggregation(
                user_id=user_id,
                date=date,
                course_id=course_id,
                type_of_aggregation='live_class',
                time_spent=meeting.get('duration'),
                reference_id=meeting.get('meeting_id'),
                resource_name=meeting.get('meeting_title')
                
            )

    @staticmethod
    def _aggregate_resources(user_id, course_id, date):
        resources = PageEventRepository.get_daily_resources_consumption_by_date_course_user(user_id=user_id, course_id=course_id, date=date)
        
        for resource in resources:
            if resource.pdf_id is not None:
                type_of_aggregation = 'resource_reading'
                reference_id = resource.pdf_id
                resource_name=resource.pdf.title
            elif resource.video_id is not None:
                type_of_aggregation = 'resource_video'
                reference_id = resource.video_id
                resource_name=resource.video.title
            elif resource.recording_id is not None:
                type_of_aggregation = 'resource_recording'
                reference_id = resource.recording_id
                resource_name=resource.recording.title
            else:
                raise ValueError("Resource must have either a pdf_id, video_id, or recording_id")

            DailyAggregationRepository.get_or_create_daily_aggregation(
                user_id=user_id,
                date=date,
                course_id=course_id,
                type_of_aggregation=type_of_aggregation,
                time_spent=resource.time_spent,
                reference_id=reference_id,
                resource_name=resource_name
            )