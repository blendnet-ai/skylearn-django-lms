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
from evaluation.usecases import AssessmentUseCase,AssessmentGenerationConfigUsecase
from course.repositories import UploadVideoRepository
from custom_auth.repositories import UserProfileRepository
from datetime import datetime,timedelta
from evaluation.repositories import AssessmentAttemptRepository
from meetings.repositories import AttendaceRecordRepository
from events_logger.repositories import PageEventRepository
from datetime import datetime, timedelta
from Feedback.repositories import FeedbackFormRepository
import logging
from meetings.repositories import MeetingRepository
from django.contrib.auth import get_user_model
User = get_user_model()

logger = logging.getLogger(__name__)

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
            user_data=config.get("user_data")
            user.is_student = True
            student_id=user.id
            user_profile = UserProfileRepository.get(user.id)

            if settings.DEPLOYMENT_TYPE == "ECF":
                StudentRepository.create_student(user)
            else:
                batch=BatchRepository.get_batch_by_id(batch_id)
                StudentRepository.create_student(user)
                StudentRepository.add_batch_by_student_id(student_id, batch)
                
            if user_data is not None:
                # Transform user_data into the required format
                user_data=user_data[0]
                formatted_user_data = {"fields":[]}
                if isinstance(user_data, dict):

                    for key, value in user_data.items():
                        formatted_user_data["fields"].append({
                            "name": key,
                            "value": value
                        })

                existing_data = user_profile.user_data if user_profile.user_data else {"sections": []}
                existing_data["sections"].append(formatted_user_data)
                
                user_profile.user_data = existing_data
                user_profile.save()
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
    def _calculate_age(user_data):
        try:
            if not user_data or 'sections' not in user_data:
                return 'N/A'
            
            # Find dob field in the sections
            user_dob=UserProfileRepository.fetch_value_from_form('dob',user_data)
            dob = datetime.strptime(user_dob, '%Y-%m-%d')
            today = datetime.now()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            return str(age)
                        
        except (ValueError, TypeError):
            return 'N/A'
    @staticmethod
    def get_student_profile(student_id):
        try:
            # Get student and user info
            student = StudentRepository.get_student_by_student_id(student_id)
            user = student.student
            # Get student batches and course info
            student_batches = StudentRepository.get_batches_by_student_id(student_id)
            
            # Get assessment data
            # Build courses enrolled data
            learning_time = timedelta(seconds=0)
            courses_enrolled = []
            for batch in student_batches:
                course = batch.course
                total_time_spent_on_resources = PageEventRepository.get_total_time_spent_by_user_on_resources_in_course(user, course.id)
                attendance_data = AttendaceRecordRepository.get_total_classes_attended_by_user_for_course(user.id, course.id,batch.id)
                assessments_data = AssessmentGenerationConfigUsecase.get_total_assessment_duration_by_course_and_user(course.id, user.id)
                # Get video stats
                total_videos = UploadVideoRepository.get_video_count_by_course(course.id)
                videos_watched = PageEventRepository.get_total_videos_watched_by_user_in_course(user, course)
                total_assessments = assessments_data.get('total_count')
                completed_count = assessments_data.get('completed_count')
                attendance = attendance_data.get('attendance_percentage')
                learning_time += (total_time_spent_on_resources + assessments_data.get('total_duration'))  # Convert seconds to hours
                courses_enrolled.append({
                    "course_id": course.code,
                    "course_name": course.title,
                    "batch_id": batch.title,
                    "attendance": attendance,
                    "videos_watched": videos_watched,
                    "total_videos": total_videos,
                    "assessments_attempted": completed_count,
                    "total_assessments": total_assessments
                })

            # Get last login info from user profile
            user_profile = UserProfileRepository.get(user.id)
            gender=UserProfileRepository.fetch_value_from_form('gender',user_profile.user_data)
            college=UserProfileRepository.fetch_value_from_form('College Name',user_profile.user_data)
            phone=user_profile.phone
            return {
                "status": student.status_string,
                "user_stats": {
                    "user_id": user.id,
                    "name": f"{user.first_name} {user.last_name}",
                    "age": StudentProfileUsecase._calculate_age(user_profile.user_data),
                    "gender": gender if gender else 'N/A',
                    "college": college if college else 'N/A',
                    "email": user.email,
                    "phone":  phone if phone else "N/A"
                },
                "engagement_stats": {
                    "last_login_date": user.last_login.date() if user.last_login else None,
                    "last_login_time": user.last_login.time() if user.last_login else None,
                    "total_learning_time": learning_time / 3600
                },
                "courses_enrolled": courses_enrolled
            }
            
        except Student.DoesNotExist:
            raise ValueError("Student not found")


class StudentStatusUsecase:
    @staticmethod
    def update_student_status(consecutive_absences=3, feedback_days=7):
        """
        Update student status based on:
        Active to Inactive if EITHER:
        - Absent in last N classes (N=3) OR
        - Not filled feedback form in past X days (X=7)
        
        Inactive to Active if BOTH:
        - All due feedback forms are filled AND
        - Attended the last scheduled live class
        """
        try:
            current_date = datetime.now().date()
            
            # Check active students for inactivation
            active_students = StudentRepository.get_active_students()
            for student in active_students:
                user_id = student.student.id
                batches = student.batches.all()
                
                for batch in batches:
                    should_inactivate = False
                    
                    # Check attendance (Condition 1)
                    recent_meetings = MeetingRepository.get_recent_meetings_for_batch(
                        batch, current_date, consecutive_absences
                    )
                    if len(recent_meetings) >= consecutive_absences:
                        attendance_records = AttendaceRecordRepository.get_attendance_records_for_meetings(
                            recent_meetings, student.student
                        )
                        
                        attendance_map = {record.meeting_id: record.attendance 
                                       for record in attendance_records}
                        
                        all_absent = True
                        for meeting in recent_meetings:
                            if attendance_map.get(meeting.id, False):
                                all_absent = False
                                break
                        
                        if all_absent:
                            should_inactivate = True
                    
                    # Check feedback forms (Condition 2)
                    if not should_inactivate:  # Only check if not already marked for inactivation
                        feedback_cutoff_date = current_date - timedelta(days=feedback_days)
                        has_pending_forms = FeedbackFormRepository.check_if_any_pending_mandatory_forms(
                            user_id=user_id,
                            batch_id=batch.id,
                            current_date=feedback_cutoff_date
                        )
                        
                        if has_pending_forms:
                            should_inactivate = True
                    
                    if should_inactivate:
                        StudentRepository.mark_student_inactive(student.student.id)
                        logger.info(f"Marked student {user_id} inactive due to attendance/feedback criteria")
                        break  # Exit batch loop once marked inactive
            
            # Check inactive students for reactivation
            inactive_students = StudentRepository.get_inactive_students()
            for student in inactive_students:
                user_id = student.student.id
                batches = student.batches.all()
                can_activate = True
                
                for batch in batches:
                    # Both conditions must be met for each batch
                    # Condition 1: All feedback forms must be filled
                    has_pending_forms = FeedbackFormRepository.check_if_any_pending_mandatory_forms(
                        user_id=user_id,
                        batch_id=batch.id,
                        current_date=current_date  # Check all forms up to current date
                    )
                    
                    if has_pending_forms:
                        can_activate = False
                        break
                    
                    # Condition 2: Must have attended last scheduled class
                    if AttendaceRecordRepository.check_student_attendance_in_period(
                        student.student, batch, consecutive_absences
                    ):
                        StudentRepository.mark_student_active(student.student.id)
                        break
                    
                if can_activate:
                    StudentRepository.mark_student_active(student.student.id)
                    logger.info(f"Reactivated student {user_id} - all criteria met")
                    
        except (Student.DoesNotExist, ValueError, AttributeError) as e:
            logger.error(f"Error in update_student_status: {str(e)}")