from accounts.models import Student
from accounts.repositories import (
    CourseProviderAdminRepository,
    LecturerRepository,
    StudentRepository,
    CourseProviderRepository,
    UserConfigMappingRepository,
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


class UserConfigMappingUsecase:
    @staticmethod
    def get_user_config_mapping(email):
        return UserConfigMappingRepository.get_user_config_mapping(email).config


class RoleAssignmentUsecase:
    STUDENT_ROLE = "student"
    LECTURER_ROLE = "lecturer"
    COURSE_PROVIDER_ADMIN_ROLE = "course_provider_admin"

    @staticmethod
    def assign_role_from_config(user):
        config = UserConfigMappingUsecase.get_user_config_mapping(user.email)

        if config is None:
            return

        role = config.get("role")

        if role == RoleAssignmentUsecase.STUDENT_ROLE:
            user.is_student = True
            user.save()

            StudentRepository.create_student(user)
        elif role == RoleAssignmentUsecase.LECTURER_ROLE:
            user.is_lecturer = True
            user.save()

            course_provider_id = config.get("course_provider_id")

            course_provider = CourseProviderRepository.get_course_provider_by_id(
                course_provider_id
            )

            LecturerRepository.create_lecturer(
                user,
                course_provider.teams_guid,
                course_provider.teams_upn,
                course_provider,
            )
        elif role == RoleAssignmentUsecase.COURSE_PROVIDER_ADMIN_ROLE:
            user.is_course_provider_admin = True
            user.save()

            course_provider_id = config.get("course_provider_id")

            course_provider = CourseProviderRepository.get_course_provider_by_id(
                course_provider_id
            )

            course_provider_admin = (
                CourseProviderAdminRepository.create_course_provider_admin(user)
            )
            CourseProviderAdminRepository.associate_with_course_provider(
                course_provider_admin, course_provider
            )
