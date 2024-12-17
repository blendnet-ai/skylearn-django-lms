# reports/usecases/generate_user_course_reports.py

from datetime import timedelta
from django.contrib.auth import get_user_model
from accounts.repositories import StudentRepository
from evaluation.repositories import AssessmentAttemptRepository
from meetings.repositories import AttendaceRecordRepository
from events_logger.repositories import PageEventRepository
from .repositories import UserCourseReportRepository, DailyAggregationRepository
from evaluation.repositories import AssessmentAttemptRepository
from meetings.repositories import AttendaceRecordRepository
from events_logger.repositories import PageEventRepository

User = get_user_model()

class GenerateUserCourseReportsUseCase:
    @staticmethod
    def generate_report(user_id,date):
        """
        Generate or update UserCourseReport records for all courses associated with a user.
        
        Args:
            user_id: The ID of the user to generate reports for
            
        Returns:
            list: List of (UserCourseReport object, created boolean) tuples
        """
        user = User.objects.get(id=user_id)
        reports = []

        if not user.is_student:
            return reports

        courses = GenerateUserCourseReportsUseCase._get_user_courses(user_id)
        
        for course in courses:
            daily_activites = DailyAggregationRepository.get_aggregations_by_user_daywise(user_id,date,course.id)
            report=GenerateUserCourseReportsUseCase._create_or_update_course_report(user,daily_activites,course)
            reports.append(report)

        return reports

    def _get_user_courses(user_id):
        student = StudentRepository.get_student_by_student_id(user_id)
        if not student:
            return []
            
        batches = student.batches.all()
        return [batch.course for batch in batches]

    def _create_or_update_course_report(user, daily_activites,course):
        assessment_time=timedelta(0)
        resource_time=timedelta(0)
        total_classes=0
        total_classes_attended=0
        
        for activity in daily_activites:
            if activity.type_of_aggregation=="assessment":
                assessment_time+=assessment_time+activity.time_spent
            elif activity.type_of_aggregation=="resource":
                resource_time+=resource_time+activity.time_spent
            elif activity.type_of_aggregation=="live_class":
                if activity.time_spent != timedelta(0):
                    total_classes_attended+=1;
                    total_classes+=1;
                else:
                    total_classes+=1;
                    
            

        defaults = {
            'assessment_time': assessment_time,
            'resource_time': resource_time,
            'total_classes': total_classes,
            'classes_attended': total_classes_attended,
            'total_time_spent': assessment_time + resource_time
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
                time_spent=attempt.get('test_duration')
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
                time_spent=meeting.get('duration') 
            )

    @staticmethod
    def _aggregate_resources(user_id, course_id, date):
        resources = PageEventRepository.get_daily_resources_consumption_by_date_course_user(user_id=user_id, course_id=course_id, date=date)
        for resource in resources:
            DailyAggregationRepository.get_or_create_daily_aggregation(
                user_id=user_id,
                date=date,
                course_id=course_id,
                type_of_aggregation='resource',
                time_spent=resource.time_spent
            )