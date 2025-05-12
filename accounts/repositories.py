from accounts.models import (
    Student,
    Lecturer,
    User,
    CourseProvider,
    CourseProviderAdmin,
    UserConfigMapping,
)
from course.repositories import BatchRepository
from django.db.models import F
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)


class StudentRepository:
    def get_student_by_student_id(student_id):
        return Student.objects.get(student_id=student_id)

    def get_students_by_student_ids(student_ids):
        return Student.objects.filter(student_id__in=student_ids)

    def add_batch_by_student_id(student_id, batch):
        student = StudentRepository.get_student_by_student_id(student_id)

        student.batches.add(batch)
        student.save()

    def add_students_to_batch(batch_id, student_ids):
        batch = BatchRepository.get_batch_by_id(batch_id)
        students = StudentRepository.get_students_by_student_ids(student_ids)

        for student in students:
            student.batches.add(batch)
            student.save()

    def get_batches_by_student_id(student_id):
        return Student.objects.get(student_id=student_id).batches.all()

    def create_student(user):
        return Student.objects.get_or_create(student=user)

    def get_all_students():
        return Student.objects.all()

    @staticmethod
    def get_active_students():
        """Get all students with active status"""
        return Student.objects.filter(status=Student.Status.ACTIVE)

    @staticmethod
    def get_inactive_students():
        """Get all students with inactive status"""
        return Student.objects.filter(status=Student.Status.INACTIVE)

    @staticmethod
    def mark_student_inactive(student_id):
        """Mark a student as inactive"""
        student = Student.objects.get(student_id=student_id)
        student.status = Student.Status.INACTIVE
        student.save()

    @staticmethod
    def mark_student_active(student_id):
        """Mark a student as active"""
        student = Student.objects.get(student_id=student_id)
        student.status = Student.Status.ACTIVE
        student.save()

    @staticmethod
    def mark_students_inactive(student_ids):
        """
        Bulk update to mark multiple students as inactive
        Args:
            student_ids (list): List of student user IDs to mark as inactive
        """
        try:
            Student.objects.filter(student_id__in=student_ids).update(
                status=Student.Status.INACTIVE
            )
        except Exception as e:
            logger.error(f"Error marking students inactive in bulk: {str(e)}")

    @staticmethod
    def mark_students_active(student_ids):
        """
        Bulk update to mark multiple students as active
        Args:
            student_ids (list): List of student user IDs to mark as active
        """
        try:
            Student.objects.filter(student_id__in=student_ids).update(
                status=Student.Status.ACTIVE
            )
        except Exception as e:
            logger.error(f"Error marking students active in bulk: {str(e)}")


class UserRepository:
    @staticmethod
    def get_user_by_id(user_id):
        return User.objects.get(id=user_id)

    @staticmethod
    def get_inactive_users(days: int):
        """
        Get inactive student users who:
        1. Haven't logged in for specified number of days
        2. Are enrolled in an active batch based on dates:
        - If both dates null: consider active
        - If only start_date: check if started
        - If only end_date: check if not ended
        - If both dates: check if current date is between them
        3. Are students

        Args:
            days (int): Number of days of inactivity to check

        Returns:
            QuerySet: Filtered User objects
        """
        from django.utils import timezone
        from datetime import timedelta
        from django.db.models import Q

        current_date = timezone.now().date()
        threshold_date = timezone.now() - timedelta(days=days)

        # Build batch date conditions
        batch_conditions = Q(
            # Case 1: Both dates are null - consider active
            Q(
                student__batches__start_date__isnull=True,
                student__batches__end_date__isnull=True,
            )
            |
            # Case 2: Only start_date exists - check if started
            Q(
                student__batches__start_date__lte=current_date,
                student__batches__end_date__isnull=True,
            )
            |
            # Case 3: Only end_date exists - check if not ended
            Q(
                student__batches__start_date__isnull=True,
                student__batches__end_date__gte=current_date,
            )
            |
            # Case 4: Both dates exist - check if current date is between them
            Q(
                student__batches__start_date__lte=current_date,
                student__batches__end_date__gte=current_date,
            )
        )

        return (
            User.objects.filter(last_login__lt=threshold_date, is_student=True)
            .filter(batch_conditions)
            .distinct()
        )


class CourseProviderAdminRepository:
    @staticmethod
    def create_course_provider_admin(user):
        return CourseProviderAdmin.objects.get_or_create(course_provider_admin=user)[0]

    @staticmethod
    def associate_with_course_provider(course_provider_admin, course_provider):
        # Check if admin is already associated with this course provider
        if not course_provider.admins.filter(id=course_provider_admin.id).exists():
            course_provider.admins.add(course_provider_admin)
            course_provider.save()
        return course_provider


class CourseProviderRepository:
    @staticmethod
    def get_course_provider_by_user_id(user_id):
        try:
            # Fetch the CourseProviderAdmin instance using the user_id
            course_provider_admin = CourseProviderAdmin.objects.get(
                course_provider_admin__id=user_id
            )

            # Fetch the related CourseProvider instance
            course_provider = CourseProvider.objects.filter(
                admins=course_provider_admin
            ).first()

            if course_provider is None:
                return None

            return course_provider

        except CourseProviderAdmin.DoesNotExist:
            return None

    def get_all_course_providers():
        return CourseProvider.objects.all()

    @staticmethod
    def get_course_provider_by_id(course_provider_id):
        try:
            return CourseProvider.objects.get(id=course_provider_id)
        except CourseProvider.DoesNotExist:
            return None


class LecturerRepository:
    @staticmethod
    def get_presenter_details_by_lecturer_id(lecturer_id):
        try:
            lecturer = Lecturer.objects.get(lecturer_id=lecturer_id)
            return lecturer.presenter_details()
        except Lecturer.DoesNotExist:
            return None

    @staticmethod
    def create_lecturer(user, guid, upn, zoom_gmail, course_provider):
        return Lecturer.objects.get_or_create(
            lecturer=user, guid=guid, upn=upn,zoom_gmail=zoom_gmail, course_provider=course_provider
        )[
            0
        ]  # get_or_create returns (object, created) tuple, we return just the object

    @staticmethod
    def get_lecturers_by_course_provider_id(course_provider_id):
        """Get all lecturers associated with a course provider"""
        return (
            Lecturer.objects.filter(course_provider_id=course_provider_id)
            .select_related("lecturer")
            .values(
                "lecturer_id",
                "guid",
                "upn",
                first_name=F("lecturer__first_name"),
                last_name=F("lecturer__last_name"),
                email=F("lecturer__email"),
            )
        )


class UserConfigMappingRepository:
    @staticmethod
    def create_user_config_mapping(email: str, config: dict):
        return UserConfigMapping.objects.create(email=email, config=config)

    @staticmethod
    def get_or_create(email: str, config: dict):
        return UserConfigMapping.objects.get_or_create(
            email=email, defaults={"config": config}
        )

    @staticmethod
    def update_or_create(email: str, config: dict):

        return UserConfigMapping.objects.update_or_create(
            email=email, defaults={"config": config}
        )

    @staticmethod
    def get_user_config_mapping(email: str):

        try:
            return UserConfigMapping.objects.get(email=email)
        except UserConfigMapping.DoesNotExist:
            return None

    @staticmethod
    def bulk_create_user_config_mappings(config_mappings: list):
        return UserConfigMapping.objects.bulk_create(config_mappings)

    @staticmethod
    def get_configs_by_course_code(course_code: str):
        # Match course_code exactly (between commas or at the start/end of the string)
        regex_pattern = rf"(^|,){course_code}($|,)"

        return UserConfigMapping.objects.filter(
            Q(config__course_codes__regex=regex_pattern)
        )

    @staticmethod
    def get_configs_for_day(date):
        """
        Get all user config mappings created on a specific date

        Args:
            date (datetime.date): The date to filter on

        Returns:
            QuerySet: UserConfigMapping objects created on the specified date
        """
        return UserConfigMapping.objects.filter(
            Q(created_at__date=date) | Q(updated_at__date=date)
        )
