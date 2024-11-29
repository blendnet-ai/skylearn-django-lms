from accounts.models import Student
from accounts.repositories import (
    ConfigMapRepository,
    CourseProviderAdminRepository,
    LecturerRepository,
    StudentRepository,
    CourseProviderRepository,
)
from course.repositories import BatchRepository
import json
from django.conf import settings


class BatchAllocationUsecase:
    @staticmethod
    def enroll_students_in_batch(batch_id, student_ids):
        batch = BatchRepository.get_batch_by_id(batch_id)

        enrolled_students = []
        failed_to_enroll_studends = []

        for student_id in student_ids:
            try:
                # One student can be enrolled in only one batch of a course
                if not BatchAllocationUsecase.does_batch_of_course_exist(
                    student_id, batch.course.id
                ):
                    StudentRepository.add_batch_by_student_id(student_id, batch)
                    enrolled_students.append(student_id)
                else:
                    failed_to_enroll_studends.append(
                        {
                            "student_id": student_id,
                            "reason": "Student is already enrolled in one of the batches of this course.",
                        }
                    )
            except Student.DoesNotExist:
                failed_to_enroll_studends.append(
                    {"student_id": student_id, "reason": "Student does not exists."}
                )
        return enrolled_students, failed_to_enroll_studends

    @staticmethod
    def does_batch_of_course_exist(student_id, course_id):
        student_batches = StudentRepository.get_batches_by_student_id(student_id)
        return any(batch.course.id == course_id for batch in student_batches)


class CourseProviderUsecase:
    def get_course_provider(user_id):
        course_provider = CourseProviderRepository.get_course_provider_by_user_id(
            user_id
        )
        data = None
        if course_provider is not None:
            data = {"name": course_provider.name, "id": course_provider.id}
        return data


class ConfigMapUsecase:
    STUDENTS = "students"
    LECTURERS = "lecturers"
    COURSE_PROVIDER_ADMINS = "course_provider_admins"

    @staticmethod
    def get_config(tag):
        return ConfigMapRepository.get_config_map(tag)


class RoleAssignmentUsecase:

    @staticmethod
    def assign_role_from_config(user):
        students = ConfigMapUsecase.get_config(ConfigMapUsecase.STUDENTS).value

        if students is not None:
            # students = json.loads(students)
            if user.email in students:
                user.is_student = True
                user.save()

                StudentRepository.create_student(user)

        lecturers = ConfigMapUsecase.get_config(ConfigMapUsecase.LECTURERS).value

        if lecturers is not None:
            # lecturers = json.loads(lecturers)
            if user.email in lecturers:
                user.is_lecturer = True
                user.save()

                LecturerRepository.create_lecturer(
                    user, settings.MS_TEAMS_ADMIN_USER_ID, settings.MS_TEAMS_ADMIN_UPN
                )

        course_provider_admins = ConfigMapUsecase.get_config(
            ConfigMapUsecase.COURSE_PROVIDER_ADMINS
        ).value

        if course_provider_admins is not None:
            # course_provider_admins = json.loads(course_provider_admins)
            if user.email in course_provider_admins:
                user.is_course_provider_admin = True
                user.save()

                CourseProviderAdminRepository.create_course_provider_admin(user)
