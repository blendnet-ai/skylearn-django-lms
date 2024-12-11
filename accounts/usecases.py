from accounts.models import Student
from accounts.repositories import (
    CourseProviderAdminRepository,
    LecturerRepository,
    StudentRepository,
    CourseProviderRepository,
    UserConfigMappingRepository,
)
from course.repositories import BatchRepository, CourseRepository
from course.models import Course, CourseAllocation
import json
from django.conf import settings
from evaluation.models import AssessmentAttempt
from evaluation.usecases import AssessmentUseCase
from course.repositories import UploadVideoRepository
from custom_auth.repositories import UserProfileRepository

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
        mapping = UserConfigMappingRepository.get_user_config_mapping(email)
        if mapping:
            return mapping.config
        return None


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
        first_name = config.get("first_name")
        last_name = config.get("last_name")
        
        # Update user names if provided
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
            
        if role == RoleAssignmentUsecase.STUDENT_ROLE:
            batch_id=config.get("batch_id")
            user.is_student = True
            student_id=user.id

            batch=BatchRepository.get_batch_by_id(batch_id)
            StudentRepository.create_student(user)

            StudentRepository.add_batch_by_student_id(student_id, batch)
            user.save()
                    
            
        elif role == RoleAssignmentUsecase.LECTURER_ROLE:
            user.is_lecturer = True 
            course_code=config.get('course_code')
            batch_id=config.get('batch_id')
            user.save()
            
            course_provider_id = config.get("course_provider_id")
            course_provider = CourseProviderRepository.get_course_provider_by_id(course_provider_id)
            
            lecturer=LecturerRepository.create_lecturer(
                user,
                course_provider.teams_guid,
                course_provider.teams_upn,
                course_provider
            )
            
                        # Assuming you have course instances
            course = Course.objects.get(code=course_code) 
            # Create a new course allocation for the lecturer
            course_allocation = CourseAllocation.objects.create(
                lecturer=user,
                session=None
            )

            # Allocate courses to the lecturer
            course_allocation.courses.add(course)
            course_allocation.save()
            
            BatchRepository.set_batch_lecturer(batch_id,user)
            
            
        elif role == RoleAssignmentUsecase.COURSE_PROVIDER_ADMIN_ROLE:
            user.is_course_provider_admin = True
            user.save()
            
            course_provider_id = config.get("course_provider_id")
            course_provider = CourseProviderRepository.get_course_provider_by_id(course_provider_id)
            
            course_provider_admin = CourseProviderAdminRepository.create_course_provider_admin(user)
            CourseProviderAdminRepository.associate_with_course_provider(
                course_provider_admin,
                course_provider
            )


class StudentProfileUsecase:
    @staticmethod
    def get_student_profile(student_id):
        try:
            # Get student and user info
            student = StudentRepository.get_student_by_student_id(student_id)
            user = student.student
            
            # Get student batches and course info
            student_batches = StudentRepository.get_batches_by_student_id(student_id)
            
            # Get assessment data
            assessment_data = AssessmentUseCase.fetch_history_data(student_id)
            # Build courses enrolled data
            courses_enrolled = []
            for batch in student_batches:
                course = batch.course
                
                # Get video stats
                total_videos = UploadVideoRepository.get_video_count_by_course(course.id)
                videos_watched = 2 #TODO: Implement actual video watched logic
                
                # Get assessment stats for the course
                course_assessments = set()
                for a in assessment_data.get('attempted_list', []):
                    if a.get('course_code') == course.code and int(a.get('status')) == int(AssessmentAttempt.Status.COMPLETED):
                        course_assessments.add((a.get('module_name'), a.get('course_code'), a.get('assessment_config_id')))
                
                total_assessments = CourseRepository.get_assessment_count_by_course_id(course.id)
                
                # Calculate attendance (placeholder - implement actual attendance logic)
                attendance = 78  #TODO: Implement actual attendance calculation
                
                courses_enrolled.append({
                    "course_id": course.code,
                    "course_name": course.title,
                    "batch_id": batch.title,
                    "attendance": attendance,
                    "videos_watched": videos_watched,
                    "total_videos": total_videos,
                    "assessments_attempted": len(course_assessments),
                    "total_assessments": total_assessments
                })

            # Get last login info from user profile
            user_profile = UserProfileRepository.get(user.id)
            
            return {
                "user_stats": {
                    "user_id": user.id,
                    "name": f"{user.first_name} {user.last_name}",
                    "age": user_profile.age if user_profile else None,
                    "gender": user_profile.gender if user_profile else None,
                    "college": "college",
                    "email": user.email,
                    "phone": user_profile.phone if user_profile else None
                },
                "engagement_stats": {
                    "last_login_date": user.last_login.date() if user.last_login else None,
                    "last_login_time": user.last_login.time() if user.last_login else None,
                    "total_learning_time": "20"
                },
                "courses_enrolled": courses_enrolled
            }
            
        except Student.DoesNotExist:
            raise ValueError("Student not found")
