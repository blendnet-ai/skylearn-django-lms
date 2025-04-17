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
from evaluation.usecases import AssessmentUseCase, AssessmentGenerationConfigUsecase
from course.repositories import UploadVideoRepository
from custom_auth.repositories import UserProfileRepository
from datetime import datetime, timedelta
from evaluation.repositories import AssessmentAttemptRepository
from meetings.repositories import AttendaceRecordRepository
from events_logger.repositories import PageEventRepository
from datetime import datetime, timedelta
from Feedback.repositories import FeedbackFormRepository
import logging
from meetings.repositories import MeetingRepository
from django.contrib.auth import get_user_model
from custom_auth.services.custom_auth_service import CustomAuth
from custom_auth.services.sendgrid_service import SendgridService
from evaluation.management.register.utils import Utils
import firebase_admin
import csv
from pathlib import Path

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
            batch_id = config.get("batch_id")
            user_data = config.get("user_data")
            user.is_student = True
            student_id = user.id
            user_profile = UserProfileRepository.get(user.id)

            if settings.DEPLOYMENT_TYPE == "ECF" and batch_id is None:
                StudentRepository.create_student(user)
            else:
                batch_ids = batch_id.split(",")  # Convert to a list of batch IDs
                StudentRepository.create_student(user)
                for batch_id in batch_ids:
                    batch = BatchRepository.get_batch_by_id(batch_id.strip())
                    if batch:
                        StudentRepository.add_batch_by_student_id(student_id, batch)

            if user_data is not None:
                # Transform user_data into the required format
                user_data = user_data[0]
                formatted_user_data = {"fields": []}
                if isinstance(user_data, dict):

                    for key, value in user_data.items():
                        formatted_user_data["fields"].append(
                            {"name": key, "value": value}
                        )

                existing_data = (
                    user_profile.user_data
                    if user_profile.user_data
                    else {"sections": []}
                )
                existing_data["sections"].append(formatted_user_data)

                user_profile.user_data = existing_data
                user_profile.save()
            user.needs_role_assignment = False
            user.save()

        elif role == RoleAssignmentUsecase.LECTURER_ROLE:
            user.is_lecturer = True
            course_code = config.get("course_code")
            batch_id = config.get("batch_id")
            user.save()

            course_provider_id = config.get("course_provider_id")
            course_provider = CourseProviderRepository.get_course_provider_by_id(
                course_provider_id
            )

            lecturer = LecturerRepository.create_lecturer(
                user,
                course_provider.teams_guid,
                course_provider.teams_upn,
                course_provider,
            )

            # Assuming you have course instances
            course = Course.objects.get(code=course_code)
            # Create a new course allocation for the lecturer
            course_allocation = CourseAllocation.objects.create(lecturer=user)

            # Allocate courses to the lecturer
            course_allocation.courses.add(course)
            course_allocation.save()

            BatchRepository.set_batch_lecturer(batch_id, user)

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


class StudentProfileUsecase:
    def _calculate_age(user_data):
        try:
            if not user_data or "sections" not in user_data:
                return "N/A"

            # Find dob field in the sections
            user_dob = UserProfileRepository.fetch_value_from_form("dob", user_data)
            dob = datetime.strptime(user_dob, "%Y-%m-%d")
            today = datetime.now()
            age = (
                today.year
                - dob.year
                - ((today.month, today.day) < (dob.month, dob.day))
            )
            return str(age)

        except (ValueError, TypeError):
            return "N/A"

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
                total_time_spent_on_resources = PageEventRepository.get_total_time_spent_by_user_on_resources_in_course(
                    user, course.id
                )
                attendance_data = AttendaceRecordRepository.get_total_classes_attended_by_user_for_course(
                    user.id, course.id, batch.id
                )
                assessments_data = AssessmentGenerationConfigUsecase.get_total_assessment_duration_by_course_and_user(
                    course.id, user.id
                )
                # Get video stats
                total_videos = UploadVideoRepository.get_video_count_by_course(
                    course.id
                )
                videos_watched = (
                    PageEventRepository.get_total_videos_watched_by_user_in_course(
                        user, course
                    )
                )
                total_assessments = assessments_data.get("total_count")
                completed_count = assessments_data.get("completed_count")
                attendance = attendance_data.get("attendance_percentage")
                learning_time += total_time_spent_on_resources + assessments_data.get(
                    "total_duration"
                )  # Convert seconds to hours
                courses_enrolled.append(
                    {
                        "course_id": course.code,
                        "course_name": course.title,
                        "batch_id": batch.title,
                        "attendance": attendance,
                        "videos_watched": videos_watched,
                        "total_videos": total_videos,
                        "assessments_attempted": completed_count,
                        "total_assessments": total_assessments,
                    }
                )

            # Get last login info from user profile
            user_profile = UserProfileRepository.get(user.id)
            gender = UserProfileRepository.fetch_value_from_form(
                "gender", user_profile.user_data
            )
            college = UserProfileRepository.fetch_value_from_form(
                "College Name", user_profile.user_data
            )
            phone = (
                (
                    user_profile.phone
                    if user_profile.phone
                    else UserProfileRepository.fetch_value_from_form(
                        "Phone", user_profile.user_data
                    )
                ),
            )  # From UserProfile
            return {
                "status": student.status_string,
                "user_stats": {
                    "user_id": user.id,
                    "name": f"{user.first_name} {user.last_name}",
                    "age": StudentProfileUsecase._calculate_age(user_profile.user_data),
                    "gender": gender if gender else "N/A",
                    "college": college if college else "N/A",
                    "email": user.email,
                    "phone": phone if phone else "N/A",
                },
                "engagement_stats": {
                    "last_login_date": (
                        user.last_login.date() if user.last_login else None
                    ),
                    "last_login_time": (
                        user.last_login.time() if user.last_login else None
                    ),
                    "total_learning_time": learning_time / 3600,
                },
                "courses_enrolled": courses_enrolled,
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

            # Get all active and inactive students in one query with their batches
            active_students = StudentRepository.get_active_students().prefetch_related(
                "batches"
            )
            inactive_students = (
                StudentRepository.get_inactive_students().prefetch_related("batches")
            )

            # Get all relevant batch IDs and student IDs
            all_batch_ids = set()
            all_student_ids = set()
            active_student_ids = set()
            inactive_student_ids = set()

            for student in active_students:
                student_id = student.student.id
                all_student_ids.add(student_id)
                active_student_ids.add(student_id)
                all_batch_ids.update(batch.id for batch in student.batches.all())

            for student in inactive_students:
                student_id = student.student.id
                all_student_ids.add(student_id)
                inactive_student_ids.add(student_id)
                all_batch_ids.update(batch.id for batch in student.batches.all())

            # Fetch all meetings for these batches in one query
            meetings_by_batch = {}
            recent_meetings = MeetingRepository.get_recent_meetings_for_batches_bulk(
                list(all_batch_ids), current_date, consecutive_absences
            )

            # Organize meetings by batch
            for meeting in recent_meetings:
                batch_id = meeting.series.course_enrollments.first().batch_id
                if batch_id not in meetings_by_batch:
                    meetings_by_batch[batch_id] = []
                meetings_by_batch[batch_id].append(meeting)

            # Get all attendance records in one query
            attendance_records = AttendaceRecordRepository.get_recent_attendance_bulk(
                list(all_student_ids), [meeting.id for meeting in recent_meetings]
            )

            # Create attendance lookup dictionary
            attendance_lookup = {}
            for record in attendance_records:
                key = (record.user_id.id, record.meeting_id)
                attendance_lookup[key] = record.attendance

            # Get all pending feedback forms and create lookup
            form_entries, filled_forms = (
                FeedbackFormRepository.get_pending_mandatory_forms_bulk(
                    list(all_student_ids), list(all_batch_ids), current_date
                )
            )

            # Create pending forms lookup
            user_filled_forms = {}
            for user_id, form_entry_id in filled_forms:
                if user_id not in user_filled_forms:
                    user_filled_forms[user_id] = set()
                user_filled_forms[user_id].add(form_entry_id)

            pending_forms_lookup = {}
            for student_id in all_student_ids:
                student_filled_forms = user_filled_forms.get(student_id, set())
                pending_forms = [
                    entry
                    for entry in form_entries
                    if entry.id not in student_filled_forms
                ]
                pending_forms_lookup[student_id] = pending_forms

            # Track students to be updated
            students_to_inactivate = set()
            students_to_activate = set()

            # Process active students for inactivation
            for student in active_students:
                user_id = student.student.id

                for batch in student.batches.all():
                    should_inactivate = False
                    batch_meetings = meetings_by_batch.get(batch.id, [])

                    # Check attendance
                    if len(batch_meetings) >= consecutive_absences:
                        all_absent = True
                        for meeting in batch_meetings:
                            if attendance_lookup.get((user_id, meeting.id), False):
                                all_absent = False
                                break

                        if all_absent:
                            should_inactivate = True

                    # Check pending forms
                    if not should_inactivate:
                        user_pending_forms = pending_forms_lookup.get(user_id, [])
                        has_pending_forms = any(
                            form.batch_id == batch.id for form in user_pending_forms
                        )
                        if has_pending_forms:
                            should_inactivate = True

                    if should_inactivate:
                        students_to_inactivate.add(user_id)
                        break

            # Process inactive students for reactivation
            for student in inactive_students:
                user_id = student.student.id
                can_activate = True

                for batch in student.batches.all():
                    batch_meetings = meetings_by_batch.get(batch.id, [])

                    # Condition 1: Check if all feedback forms are filled
                    user_pending_forms = pending_forms_lookup.get(user_id, [])
                    has_pending_forms = any(
                        form.batch_id == batch.id for form in user_pending_forms
                    )
                    if has_pending_forms:
                        can_activate = False
                        break

                    # Condition 2: Must have attended at least one recent class
                    if batch_meetings:
                        has_recent_attendance = False
                        for meeting in batch_meetings:
                            if attendance_lookup.get((user_id, meeting.id), False):
                                has_recent_attendance = True
                                break

                        if not has_recent_attendance:
                            can_activate = False
                            break

                if can_activate:
                    students_to_activate.add(user_id)

            # Perform bulk updates
            if students_to_inactivate:
                StudentRepository.mark_students_inactive(list(students_to_inactivate))
                logger.info(
                    f"Marked {len(students_to_inactivate)}: {students_to_inactivate} students inactive"
                )

            if students_to_activate:
                StudentRepository.mark_students_active(list(students_to_activate))
                logger.info(
                    f"Reactivated {len(students_to_activate)} : {students_to_activate} students"
                )

        except (Student.DoesNotExist, ValueError, AttributeError) as e:
            logger.error(f"Error in update_student_status: {str(e)}")
            raise


class UserSyncUsecase:
    @staticmethod
    def sync_users_from_config():
        """
        Creates users and assigns/updates roles for all users in config mappings.
        Creates new users in Firebase if they don't exist and saves passwords to CSV.
        """
        try:
            config_mappings = UserConfigMappingRepository.get_configs_for_day(
                datetime.now().date()
            )

            processed_users = []
            failed_users = []
            csv_path = Path("user_credentials.csv")
            file_exists = csv_path.exists()

            for mapping in config_mappings:
                try:
                    user = User.objects.filter(email=mapping.email).first()

                    if not user:
                        try:
                            # Try to get from Firebase first
                            firebase_uid = CustomAuth.get_user_by_email(mapping.email)
                            # Create user with Firebase data
                            user = User.objects.create(
                                email=mapping.email,
                                username=firebase_uid,
                                firebase_uid=firebase_uid,
                                first_name=mapping.config.get("first_name", ""),
                                last_name=mapping.config.get("last_name", ""),
                            )
                            logger.info(
                                f"Created new user from Firebase: {mapping.email}"
                            )

                        except firebase_admin.auth.UserNotFoundError:
                            # Generate password and create user in Firebase
                            password = Utils.generate_random_password()
                            firebase_uid = CustomAuth.create_user(
                                email=mapping.email, password=password
                            )

                            # Create user in Django
                            user = User.objects.create(
                                email=mapping.email,
                                username=firebase_uid,
                                firebase_uid=firebase_uid,
                                first_name=mapping.config.get("first_name", ""),
                                last_name=mapping.config.get("last_name", ""),
                            )

                            # Immediately write credentials to CSV
                            with open(csv_path, "a", newline="") as f:
                                writer = csv.DictWriter(
                                    f, fieldnames=["email", "password", "created_at"]
                                )
                                if not file_exists:
                                    writer.writeheader()
                                    file_exists = True
                                writer.writerow(
                                    {
                                        "email": mapping.email,
                                        "password": password,
                                        "created_at": datetime.now().strftime(
                                            "%Y-%m-%d %H:%M:%S"
                                        ),
                                    }
                                )
                            logger.info(f"Saved credentials for: {mapping.email}")
                            # Send password email
                            SendgridService.send_password_email(mapping.email, password)
                            logger.info(f"Sent password email to: {mapping.email}")

                    # Assign role
                    RoleAssignmentUsecase.assign_role_from_config(user)
                    processed_users.append(mapping.email)
                    logger.info(f"Processed role assignment for: {mapping.email}")

                except Exception as e:
                    failed_users.append({"email": mapping.email, "error": str(e)})
                    logger.error(f"Failed to process user {mapping.email}: {str(e)}")

            return {
                "success": True,
                "processed_users": processed_users,
                "failed_users": failed_users,
                "total_processed": len(processed_users),
                "total_failed": len(failed_users),
            }

        except Exception as e:
            logger.error(f"Error in sync_users_from_config: {str(e)}")
            return {"success": False, "error": str(e)}
