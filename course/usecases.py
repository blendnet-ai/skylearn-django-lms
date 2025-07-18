from accounts.repositories import (
    StudentRepository,
    UserConfigMappingRepository,
    UserRepository,
    LecturerRepository,
)
from accounts.models import Student
from config import settings
from course.models import Batch, LiveClassSeriesBatchAllocation
from course.repositories import (
    BatchRepository,
    CourseRepository,
    LiveClassSeriesBatchAllocationRepository,
    ModuleRepository,
    UploadRepository,
    UploadVideoRepository,
)
from custom_auth.repositories import UserProfileRepository
from meetings.repositories import MeetingSeriesRepository
from meetings.usecases import MeetingSeriesUsecase, MeetingUsecase
from accounts.repositories import CourseProviderRepository
from .exceptions import CourseContentDriveException

import os
import logging
import re
from urllib.parse import urlparse
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
from evaluation.management.generate_status_sheet.gd_wrapper import GDWrapper
from course.models import Course, Module, Upload, UploadVideo
from storage_service.azure_storage import AzureStorageService
from telegram_bot.repositories import TelegramChatDataRepository
from notifications_manager.usecases import NotificationManagerUsecase
from django.utils import timezone
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
from django.contrib.auth import get_user_model
from reports.repositories import UserCourseReportRepository

User = get_user_model()


class LiveClassUsecase:
    class UserNotInBatchOfCourseException(Exception):
        def __init__(self):
            super().__init__("User is not enrolled in the any batch of the course")

    @staticmethod
    def create_live_class_series(
        title,
        batch_ids,
        start_time,
        start_date,
        duration,
        end_date,
        recurrence_type,
        weekday_schedule,
        monthly_day,
    ):

        live_class_series = (
            MeetingSeriesUsecase.create_or_update_meeting_series_and_create_occurrences(
                title=title,
                start_time=start_time,
                start_date=start_date,
                duration=duration,
                end_date=end_date,
                recurrence_type=recurrence_type,
                weekday_schedule=weekday_schedule,
                monthly_day=monthly_day,
            )
        )

        for batch_id in batch_ids:
            batch = BatchRepository.get_batch_by_id(batch_id)
            if not batch.lecturer:
                raise MeetingSeriesUsecase.LecturerNotAssigned

        batches_allocated, batches_failed_to_allocate = (
            LiveClassSeriesBatchAllocationUseCase.allocate_batches_to_live_series(
                batch_ids, live_class_series
            )
        )

        presenter_assignment_success = []
        # Assign presenters to the allocated batches
        if batches_allocated:
            presenter_assignment_success = (
                LiveClassSeriesPresenterAssignmentUseCase.assign_presenters_to_batches(
                    batches_allocated, live_class_series
                )
            )

        return (
            live_class_series.id,
            batches_allocated,
            batches_failed_to_allocate,
            presenter_assignment_success,
        )

    @staticmethod
    def update_live_class_series(
        series_id,
        title,
        batch_ids,
        start_time,
        start_date,
        duration,
        end_date,
        recurrence_type,
        weekday_schedule,
        monthly_day,
    ):
        live_class_series = MeetingSeriesRepository.get_meeting_series_by_id(series_id)

        MeetingSeriesUsecase.renew_meeting_series(
            live_class_series,
            title,
            start_time,
            start_date,
            duration,
            end_date,
            recurrence_type,
            weekday_schedule,
            monthly_day,
        )

        # Update batch allocations
        new_batch_ids = set(batch_ids)

        batches_allocated, batches_failed_to_allocate = (
            LiveClassSeriesBatchAllocationUseCase.create_and_remove_allocations(
                live_class_series, new_batch_ids
            )
        )
        presenter_assignment_success = []
        if batches_allocated:
            presenter_assignment_success = (
                LiveClassSeriesPresenterAssignmentUseCase.assign_presenters_to_batches(
                    batches_allocated, live_class_series
                )
            )

        return (
            batches_allocated,
            batches_failed_to_allocate,
            presenter_assignment_success,
        )

    @staticmethod
    def delete_live_class_series(id):
        MeetingSeriesUsecase.delete_meeting_series(id)

    @staticmethod
    def get_live_classes_of_course_in_period_for_student(
        course_id, student_id, start_date, end_date
    ):
        # Get the batch of the course in which the user is enrolled in
        batch = BatchUseCase.get_batch_by_user_id_and_course_id(student_id, course_id)
        if not batch:
            raise LiveClassUsecase.UserNotInBatchOfCourseException()

        # Get the live classes of that batch in the given period
        live_classes = (
            LiveClassSeriesBatchAllocationUseCase.get_live_classes_of_batch_in_period(
                batch.id, start_date, end_date
            )
        )
        return live_classes

    @staticmethod
    def get_live_classes_in_period_for_lecturer_or_student(user, start_date, end_date):
        if user.is_student:
            # Get all the batches of the student
            batches = StudentRepository.get_batches_by_student_id(user.id)
        elif user.is_lecturer:
            batches = BatchRepository.get_batches_by_lecturer_id(user.id)
        elif user.is_course_provider_admin:
            course_provider = CourseProviderRepository.get_course_provider_by_user_id(
                user.id
            ).id
            courses = CourseUseCase.get_courses_by_course_provider(course_provider)
            batches = []
            for course in courses:
                batch_queryset = BatchRepository.get_batches_by_course_id(
                    course.get("id")
                )
                if batch_queryset.exists():  # Check if there are any batches
                    for batch in batch_queryset:  # Iterate over each batch
                        batches.append(batch)
        else:
            # This is not in the requirements currently
            return []
        live_classes = []
        # Get the live classes of the batches in the given period
        for batch in batches:
            live_classes.extend(
                LiveClassSeriesBatchAllocationUseCase.get_live_classes_of_batch_in_period(
                    batch.id, start_date, end_date
                )
            )
        # Convert to set of tuples for deduplication, then back to list of dicts
        # This is to remove duplicate live classes
        unique_tuples = {tuple(meeting.items()) for meeting in live_classes}
        return [dict(t) for t in unique_tuples]


class LiveClassSeriesPresenterAssignmentUseCase:
    @staticmethod
    def assign_presenters_to_batches(batches_allocated, live_class_series):
        assignment_results = {}
        for batch in batches_allocated:
            batch = BatchRepository.get_batch_by_id(batch)
            if batch.lecturer:
                presenter_details = (
                    LecturerRepository.get_presenter_details_by_lecturer_id(
                        batch.lecturer.id
                    )
                )
            else:
                raise MeetingSeriesUsecase.LecturerNotAssigned

            if presenter_details:
                # Convert presenter_details to a serializable format if needed
                serializable_presenter_details = {
                    key: value
                    for key, value in presenter_details.items()
                    if not callable(value)  # Filter out any method objects
                }

                LiveClassSeriesPresenterAssignmentUseCase.assign_presenter(
                    live_class_series, serializable_presenter_details
                )
                assignment_results[batch.id] = True

        return assignment_results

    @staticmethod
    def assign_presenter(live_class_series, presenter_details):
        # Ensure presenter_details is serializable before passing it
        if not isinstance(presenter_details, dict):
            presenter_details = dict(presenter_details)

        # Remove any method objects from the dictionary
        presenter_details = {
            key: value
            for key, value in presenter_details.items()
            if not callable(value)
        }

        MeetingSeriesRepository.add_presenter_details_to_meeting_series(
            live_class_series, presenter_details
        )


class LiveClassSeriesBatchAllocationUseCase:
    class BatchIdNotIntegerException(Exception):
        def __init__(self):
            super().__init__("Batch ID is not an integer")

    @staticmethod
    def create_and_remove_allocations(live_class_series, new_batch_ids):
        old_batch_ids = set(
            LiveClassSeriesBatchAllocationRepository.get_batch_ids_by_live_class_series_id(
                live_class_series
            )
        )
        batches_allocated = batches_failed_to_allocate = []

        # Remove allocations for batches that are no longer included
        batches_to_remove = old_batch_ids - new_batch_ids
        LiveClassSeriesBatchAllocationUseCase.remove_batches_from_live_series(
            batches_to_remove, live_class_series
        )

        # Create allocations for new batches
        batches_to_add = new_batch_ids - old_batch_ids
        batches_allocated, batches_failed_to_allocate = (
            LiveClassSeriesBatchAllocationUseCase.allocate_batches_to_live_series(
                list(batches_to_add), live_class_series
            )
        )
        return batches_allocated, batches_failed_to_allocate

    @staticmethod
    def allocate_batches_to_live_series(batch_ids, live_class_series):
        batches_allocated = []
        batches_failed_to_allocate = []
        for batch_id in batch_ids:
            try:
                LiveClassSeriesBatchAllocationUseCase.create_live_class_series_batch_allocation(
                    live_class_series, batch_id
                )
                batches_allocated.append(batch_id)
            except Batch.DoesNotExist:
                batches_failed_to_allocate.append(
                    {"batch_id": batch_id, "reason": "Batch not found"}
                )
            except LiveClassSeriesBatchAllocationUseCase.BatchIdNotIntegerException:
                batches_failed_to_allocate.append(
                    {"batch_id": batch_id, "reason": "Batch ID is not an integer"}
                )
        return batches_allocated, batches_failed_to_allocate

    @staticmethod
    def remove_batches_from_live_series(batch_ids, live_class_series):
        for batch_id in batch_ids:
            try:
                LiveClassSeriesBatchAllocationRepository.delete_live_class_series_batch_allocation(
                    live_class_series, batch_id
                )
            except LiveClassSeriesBatchAllocation.DoesNotExist:
                pass

    @staticmethod
    def create_live_class_series_batch_allocation(live_class_series, batch_id):
        if not isinstance(batch_id, int):
            raise LiveClassSeriesBatchAllocationUseCase.BatchIdNotIntegerException()
        batch = BatchRepository.get_batch_by_id(batch_id)

        return LiveClassSeriesBatchAllocationRepository.create_live_class_series_batch_allocation(
            live_class_series, batch=batch
        )

    @staticmethod
    def get_live_classes_of_batch_in_period(batch_id, start_date, end_date):
        # Get all the live class series of the batch
        live_classe_series_ids = (
            LiveClassSeriesBatchAllocationRepository.get_live_classe_series_by_batch_id(
                batch_id
            )
        )
        live_classes = []

        # Get all the live classes of the live class series in the given period
        for series_id in live_classe_series_ids:
            live_classes.extend(
                MeetingUsecase.get_meetings_of_series_in_period(
                    series_id, start_date, end_date
                )
            )

        return live_classes


class BatchUseCase:
    class UserIsNotLecturerException(Exception):
        def __init__(self):
            super().__init__("User is not a lecturer")

    @staticmethod
    def create_batch(
        course_id, title, lecturer_id, start_date=None, end_date=None, form=None
    ):
        course = CourseRepository.get_course_by_id(course_id)
        lecturer = UserRepository.get_user_by_id(lecturer_id)
        if not lecturer.is_lecturer:

            raise BatchUseCase.UserIsNotLecturerException()
        batch, created = BatchRepository.create_batch(
            course, title, lecturer, start_date, end_date, form
        )
        return batch, created

    @staticmethod
    def get_batch_by_user_id_and_course_id(user_id, course_id):
        # Get all the batches for the user
        user_batches = StudentRepository.get_batches_by_student_id(user_id)

        for user_batch in user_batches:
            if user_batch.course_id == course_id:
                return user_batch
        return None

    @staticmethod
    def get_batches_by_course_id(user, course_id):
        batches = BatchRepository.get_batches_by_course_id(course_id)

        # Convert to a list of dictionaries, including students
        batches_with_students = []
        for batch in batches:
            # Get all students for this batch
            students = []
            for student in batch.students.all():
                student_data = {
                    "id": student.student.id,
                    "name": f"{student.student.first_name} {student.student.last_name}",
                    "email": student.student.email,
                    "status": student.status_string,
                    "enrollment_date": batch.created_at
                }
                students.append(student_data)

            batch_data = {
                "id": batch.id,
                "title": batch.title,
                "course_id": batch.course_id,
                "lecturer_id": batch.lecturer_id,
                "start_date": batch.created_at,
                "students_count": len(batch.students.values()),  # Get student data
                "students": students,
            }
            batches_with_students.append(batch_data)
        if user.is_lecturer:
            if user.is_lecturer:
                batches_with_students = [
                    batch
                    for batch in batches_with_students
                    if batch["lecturer_id"] == user.id
                ]

        return batches_with_students

    @staticmethod
    def get_students_for_lecturer_or_provider(user):
        students_data = []

        if user.is_lecturer:
            # Get all batches where user is the lecturer
            batches = BatchRepository.get_batches_by_lecturer_id(user.id)
        elif user.is_course_provider_admin:
            # Get course provider ID
            course_provider = CourseProviderRepository.get_course_provider_by_user_id(
                user.id
            )
            # Get all courses for this provider
            courses = CourseRepository.get_courses_by_course_provider(
                course_provider.id
            )
            # Get all batches for these courses
            batches = []
            for course in courses:
                batch_queryset = BatchRepository.get_batches_by_course_id(course.id)
                batches.extend(batch_queryset)
        else:
            return []

        # Process each batch to get student information
        for batch in batches:
            for student in batch.students.all():
                student_data = {
                    "id": student.student.id,
                    "name": f"{student.student.first_name} {student.student.last_name}",
                    "email": student.student.email,
                    "status": student.status_string,
                    "batch_id": batch.id,
                    "batch_title": batch.title,
                    "course_id": batch.course.id,
                    "course_title": batch.course.title,
                    "enrollment_date": batch.created_at,
                    "last_login": (
                        student.student.last_login
                        if student.student.last_login
                        else None
                    ),
                }
                students_data.append(student_data)

        # Remove duplicates based on student ID
        unique_students = {student["id"]: student for student in students_data}.values()
        return list(unique_students)

    @staticmethod
    def add_students_to_batch(batch_id, student_ids):
        return StudentRepository.add_students_to_batch(batch_id, student_ids)


class CourseUseCase:
    def get_courses_by_course_provider(course_provider_id):

        courses = list(
            CourseRepository.get_courses_by_course_provider(course_provider_id).values()
        )
        return courses

    def get_courses_for_student_or_lecturer(user):
        if user.is_lecturer or user.is_course_provider_admin:
            if user.is_lecturer:
                courses = CourseRepository.get_courses_for_lecturer(user.id)
            else:
                courses = CourseRepository.get_courses_for_course_provider_admin(
                    user.id
                )
            for course in courses:
                # Get batches for the current course
                batches = BatchRepository.get_batches_by_course_id(course.get("id"))
                # Filter batches to include only those for the current lecturer
                if user.is_lecturer:
                    lecturer_batches = batches.filter(lecturer_id=user.id)
                else:
                    lecturer_batches = batches
                # Count the number of batches for the lecturer
                course["no_of_batches"] = lecturer_batches.count()
            return courses, "lecturer"

        elif user.is_student:
            courses = CourseRepository.get_courses_for_student(user.id)
            return courses, "student"
        else:
            return None, "user"

    def get_modules_by_course_id(course_id):
        modules = ModuleRepository.get_module_details_by_course_id(course_id)
        module_data = []
        for module in modules:
            assessment_generation_configs = [
                config.assessment_generation_id
                for config in module.assignment_configs.all()
            ]

            # Collect reading resources and sort by title
            resource_data_reading = sorted(
                [
                    {
                        "type": "reading",
                        "id": resource.id,
                        "title": resource.title,
                        "url": resource.blob_url,
                    }
                    for resource in module.uploads.all()
                ],
                key=lambda x: x["title"],
            )

            # Collect video resources and sort by title
            resource_data_video = sorted(
                [
                    {
                        "type": "video",
                        "id": resource.id,
                        "title": resource.title,
                        "url": resource.blob_url,
                    }
                    for resource in module.video_uploads.all()
                ],
                key=lambda x: x["title"],
            )

            module_data.append(
                {
                    "id": module.id,
                    "order_in_course": module.order_in_course,
                    "title": module.title,
                    "resources_reading": resource_data_reading,
                    "resources_video": resource_data_video,
                    "assessment_generation_configs": assessment_generation_configs,
                }
            )
        return module_data

    @staticmethod
    def create_course(
        title: str, summary: str, code, course_hours: int, course_provider
    ) -> Course:
        """Create a new course"""
        course = CourseRepository.create_course(
            course_provider, code, title, summary, course_hours
        )
        return course

    @staticmethod
    def update_course(course_id: int, **kwargs) -> Course:
        """Update an existing course"""
        course = Course.objects.get(id=course_id)

        # Update only provided fields
        for field, value in kwargs.items():
            if value is not None:
                setattr(course, field, value)

        course.save()
        return course

    @staticmethod
    def delete_course(course_id: int) -> None:
        """Delete a course"""
        course = Course.objects.get(id=course_id)
        course.delete()


class CourseContentDriveUsecase:
    def __init__(self):
        self.storage_service = AzureStorageService()
        self.logger = logging.getLogger(__name__)

    def sync_course_content(self, course_id):
        """Syncs content for a specific course from Drive to blob storage"""
        self.logger.info(f"Starting content sync for course ID: {course_id}")
        try:
            course = CourseRepository.get_course_by_id(course_id)
            self.logger.info(f"Found course: {course.code} - Starting sync process")

            if not course.drive_folder_link:
                self.logger.error(f"No drive folder link found for course {course_id}")
                raise CourseContentDriveException.DriveInitializationException(
                    "No drive folder link found for course"
                )

            folder_id = self._extract_folder_id_from_url(course.drive_folder_link)
            self.logger.info(f"Extracted folder ID: {folder_id} from drive link")

            drive_service = self._initialize_drive_service()
            self.logger.info("Successfully initialized Google Drive service")

            result = self._process_course_folder(drive_service, folder_id, course)
            self.logger.info(f"Successfully completed sync for course {course_id}")
            return result

        except CourseContentDriveException as e:
            self.logger.error(
                f"Drive content sync failed for course {course_id}: {str(e)}",
                exc_info=True,
            )
            raise
        except Exception as e:
            self.logger.error(
                f"Unexpected error during content sync for course {course_id}: {str(e)}",
                exc_info=True,
            )
            raise CourseContentDriveException.DriveAPIException(
                "sync_course_content", e
            )

    def _initialize_drive_service(self):
        """Initialize Google Drive API client"""
        try:
            scopes = [
                "https://www.googleapis.com/auth/drive.file",
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive.readonly",
            ]
            current_directory = os.getcwd()
            config_file_path = os.path.join(current_directory, "gd_config.json")

            credentials = Credentials.from_service_account_file(
                config_file_path, scopes=scopes
            )
            return build("drive", "v3", credentials=credentials)
        except Exception as e:
            raise CourseContentDriveException.DriveInitializationException(e)

    def _process_course_folder(self, drive_service, folder_id, course):
        """Processes all modules within a course folder"""
        self.logger.info(f"Processing course folder for course: {course.code}")
        try:
            module_folders = self._list_folders(drive_service, folder_id)
            self.logger.info(f"Found {len(module_folders)} module folders")
        except Exception as e:
            self.logger.error(f"Failed to list folders: {str(e)}", exc_info=True)
            raise CourseContentDriveException.DriveAPIException("list_folders", e)

        module_results = []
        for index, module_folder in enumerate(module_folders, 1):
            self.logger.info(
                f"Processing module {index}/{len(module_folders)}: {module_folder['name']}"
            )
            try:
                module_order, module_name = self._parse_module_folder_name(
                    module_folder["name"]
                )
                self.logger.debug(
                    f"Parsed module name: {module_name}, order: {module_order}"
                )

                module, created = ModuleRepository.get_or_create_module(
                    course=course, title=module_name, order_in_course=module_order
                )

                if created:
                    self.logger.info(
                        f"Created module: {module.title} (ID: {module.id})"
                    )
                else:
                    self.logger.info(
                        f"Retrieved module: {module.title} (ID: {module.id})"
                    )

                module_content = {
                    "module_id": module.id,
                    "module_name": module_name,
                    "resources": self._process_module_resources(
                        drive_service,
                        module_folder["id"],
                        f"{course.code}/{module_folder['name']}",
                        course,
                        module,
                    ),
                }
                module_results.append(module_content)
                self.logger.info(f"Successfully processed module: {module_name}")

            except Exception as e:
                self.logger.error(
                    f"Failed to process module {module_folder['name']}: {str(e)}",
                    exc_info=True,
                )
                module_results.append(
                    {
                        "module_name": module_folder["name"],
                        "status": "failed",
                        "error": str(e),
                    }
                )

        return module_results

    def _process_module_resources(
        self, drive_service, module_folder_id, module_path, course, module
    ):
        """Processes both video and reading resources in a module"""
        self.logger.info(f"Processing resources for module: {module.title}")
        resources = {"video": [], "reading": []}

        resource_folders = self._list_folders(drive_service, module_folder_id)
        self.logger.info(f"Found {len(resource_folders)} resource folders")

        for folder in resource_folders:
            resource_path = os.path.join(module_path, folder["name"])
            self.logger.info(f"Processing resource folder: {folder['name']}")

            if folder["name"] == "Video Resources":
                self.logger.info("Processing video resources")
                resources["video"] = self._process_resource_folder(
                    drive_service, folder["id"], "video", resource_path, course, module
                )
                self.logger.info(f"Processed {len(resources['video'])} video resources")

            elif folder["name"] == "Reading Resources":
                self.logger.info("Processing reading resources")
                resources["reading"] = self._process_resource_folder(
                    drive_service,
                    folder["id"],
                    "reading",
                    resource_path,
                    course,
                    module,
                )
                self.logger.info(
                    f"Processed {len(resources['reading'])} reading resources"
                )

        return resources

    def _process_resource_folder(
        self, drive_service, folder_id, resource_type, resource_path, course, module
    ):
        """Downloads and uploads all files in a resource folder"""
        self.logger.info(
            f"Processing {resource_type} resources at path: {resource_path}"
        )
        processed_files = []

        try:
            query = f"'{folder_id}' in parents and mimeType!='application/vnd.google-apps.folder'"
            files = drive_service.files().list(q=query).execute().get("files", [])
            self.logger.info(f"Found {len(files)} files to process")
        except Exception as e:
            self.logger.error(f"Failed to list files: {str(e)}", exc_info=True)
            raise CourseContentDriveException.DriveAPIException("list_files", e)

        for index, file in enumerate(files, 1):
            file_path = os.path.join(resource_path, file["name"])
            self.logger.info(f"Processing file {index}/{len(files)}: {file['name']}")

            try:
                repository = (
                    UploadRepository
                    if resource_type == "reading"
                    else UploadVideoRepository
                )
                existing_upload = repository.get_existing_upload(
                    file["name"], course, module
                )

                if existing_upload:
                    self.logger.info(f"File already exists: {file['name']}")
                    processed_files.append(
                        {
                            "name": file["name"],
                            "type": resource_type,
                            "url": f"https://drive.google.com/file/d/{file['id']}/view",
                            "status": "existing",
                        }
                    )
                    continue

                self.logger.info(f"Downloading and uploading file: {file['name']}")
                blob_url = self._download_and_upload_file(
                    drive_service, file, file_path
                )

                repository.create_upload(
                    title=file["name"], course=course, module=module, blob_url=blob_url
                )
                self.logger.info(f"Successfully processed file: {file['name']}")

                processed_files.append(
                    {
                        "name": file["name"],
                        "type": resource_type,
                        "url": f"https://drive.google.com/file/d/{file['id']}/view",
                        "status": "success",
                    }
                )

            except Exception as e:
                self.logger.error(
                    f"Failed to process file {file['name']}: {str(e)}", exc_info=True
                )
                raise CourseContentDriveException.DriveFileUploadException(
                    file["name"], e
                )

        return processed_files

    def _download_and_upload_file(self, drive_service, file, file_path):
        """Helper method to download from Drive and upload to blob storage"""
        try:
            # Get file metadata to retrieve MIME type
            file_metadata = (
                drive_service.files()
                .get(fileId=file["id"], fields="mimeType")
                .execute()
            )
            mime_type = file_metadata.get("mimeType", "application/octet-stream")

            request = drive_service.files().get_media(fileId=file["id"])
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)

            done = False
            while not done:
                _, done = downloader.next_chunk()

            file_content.seek(0)
            return self._upload_to_blob(
                file_content, file["name"], file_path, mime_type
            )
        except Exception as e:
            raise CourseContentDriveException.DriveFileUploadException(file["name"], e)

    def _parse_module_folder_name(self, folder_name):
        """Extract order and name from module folder name (e.g., "1_Module Name")"""
        match = re.match(r"^(\d+)_(.+)$", folder_name)
        if not match:
            raise CourseContentDriveException.InvalidFolderFormatException(
                f"Invalid module folder name format: {folder_name}. Expected format: 'ORDER_NAME'"
            )
        return int(match.group(1)), match.group(2)

    def _extract_folder_id_from_url(self, url):
        """Extract folder ID from Google Drive URL"""
        patterns = [
            r"folders/([a-zA-Z0-9-_]+)",  # Standard folder URL
            r"id=([a-zA-Z0-9-_]+)",  # Alternate format
            r"/d/([a-zA-Z0-9-_]+)",  # Short format
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        raise CourseContentDriveException.DriveInitializationException(
            f"Could not extract folder ID from URL: {url}"
        )

    def _list_folders(self, drive_service, parent_id):
        """List all folders within a parent folder"""
        query = f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder'"
        results = drive_service.files().list(q=query).execute()
        return results.get("files", [])

    def _upload_to_blob(self, file_content, filename, blob_path, content_type):
        """Upload file to Azure Blob Storage with content type"""
        logging.info(
            f"Uploading file to blob storage: {blob_path} with content type: {content_type}"
        )
        blob_url = self.storage_service.upload_blob(
            container_name=settings.AZURE_STORAGE_COURSE_MATERIALS_CONTAINER_NAME,
            blob_name=blob_path,
            content=file_content,
            content_type=content_type,  # Pass the content type to Azure
            overwrite=True,
        )
        logging.info(f"Uploaded file to blob storage: {blob_url}")
        return blob_url

    def _delete_blob(self, blob_url):
        self.storage_service.delete_blob(blob_url)


class BatchMessageUsecase:
    @staticmethod
    def send_batch_messages(batch_id: int, subject: str, message: str) -> dict:
        """
        Send messages to all students in a batch via email and telegram

        Args:
            batch_id: ID of the batch
            subject: Subject line for email
            message: Message content

        Returns:
            dict: Statistics about message delivery
        """
        batch = BatchRepository.get_batch_by_id(batch_id)

        # Prepare variables and user_ids
        variables = []
        user_ids = []

        for student in batch.students.all():
            variables.append(
                {
                    "participant_name": student.student.get_full_name,
                    "email_subject": subject,
                }
            )
            user_ids.append(student.student_id)

        # Send immediate notifications for both email and telegram
        email_success = NotificationManagerUsecase.send_immediate_notification(
            message_template=message,
            variables=variables,
            user_ids=user_ids,
            medium="email",
            notification_type="batch_message",
            reference_id=None,
        )

        telegram_success = NotificationManagerUsecase.send_immediate_notification(
            message_template=message,
            variables=variables,
            user_ids=user_ids,
            medium="telegram",
            notification_type="batch_message",
            reference_id=None,
        )

        # Return statistics
        return {
            "email_sent": len(user_ids) if email_success else 0,
            "email_failed": len(user_ids) if not email_success else 0,
            "telegram_sent": len(user_ids) if telegram_success else 0,
            "telegram_failed": len(user_ids) if not telegram_success else 0,
        }


class PersonalMessageUsecase:
    @staticmethod
    def send_personal_message(user_id: int, message: str) -> None:
        """
        Send a personal message to a user via email

        Args:
            user_id: ID of the user
            message: Message content
        """
        user = UserRepository.get_user_by_id(user_id)
        variables = [
            {
                "participant_name": user.get_full_name,
                "email_subject": "Message from course provider",
                "subject": message,
            }
        ]

        NotificationManagerUsecase.send_immediate_notification(
            message_template=message,
            variables=variables,
            user_ids=[user.id],
            medium="email",
            notification_type="personal_message",
            reference_id=None,
        )

        NotificationManagerUsecase.send_immediate_notification(
            message_template=message,
            variables=variables,
            user_ids=[user.id],
            medium="telegram",
            notification_type="personal_message",
            reference_id=None,
        )


class AssessmentModuleUsecase:
    def fetch_assessment_display_data(user_id, course_id, module_id):
        from evaluation.repositories import (
            AssessmentGenerationConfigRepository,
            AssessmentAttemptRepository,
        )

        available_assessments = AssessmentGenerationConfigRepository.return_assessment_generation_configs_by_course_id_module_id(
            course_id, module_id
        )
        resp_data = []
        for assessment in available_assessments:
            assessment_generation_id = assessment.assessment_generation_id
            # Get max score and percentage for this assessment config
            attempts = AssessmentAttemptRepository.get_assessment_attempts_by_config(
                user_id=user_id,
                assessment_generation_config_id=assessment_generation_id,
            )
            max_percentage = 0

            for attempt in attempts:
                eval_data = attempt.eval_data or {}
                percentage = eval_data.get("percentage", 0)
                max_percentage = max(max_percentage, percentage)

            # if (
            #     assessment_generation_id == int(AssessmentAttempt.Type.CODING) + 1
            #     and str(user_id) not in settings.USER_IDS_CODING_TEST_ENABLED
            # ):
            #     continue

            display_data = assessment.display_data
            name = assessment.assessment_display_name
            max_attempts = assessment.number_of_attempts
            start_date = assessment.start_date
            end_date = assessment.end_date
            due_date = assessment.due_date
            number_of_attempts = AssessmentAttemptRepository.number_of_attempts_expired(
                assessment_generation_config_id=assessment_generation_id,
                user_id=user_id,
            )

            # Check if the assessment should be locked
            current_date = timezone.now()
            if start_date is not None and end_date is not None:
                is_locked = not (start_date <= current_date <= end_date)
            else:
                is_locked = False

            resp_obj = {
                "assessment_generation_id": assessment_generation_id,
                "test": {
                    "heading": f"{name} test",
                    "path": f"assessment",
                    "query_params": f"?id={assessment_generation_id}",
                },
                "welcome": {
                    "heading": f"Welcome to {name} test",
                    "heading_inner": f"Welcome to your {name} test",
                    "instructions": display_data.get("instructions"),
                    "img_url": display_data.get("welcome_img_url"),
                },
                "eval_home": {
                    "heading": f"{name}",
                    "img_url": display_data.get("eval_img_url"),
                },
                "name": name,
                "max_attempts": max_attempts,
                "user_attempts": number_of_attempts,
                "user_id": user_id,
                "start_date": start_date,
                "end_date": end_date,
                "due_date": due_date,
                "is_locked": is_locked,
                "score": f"{max_percentage}%",
            }

            resp_data.append(resp_obj)
        resp_data.sort(key=lambda x: x["assessment_generation_id"])
        return resp_data


class UnassignedStudentsUsecase:
    @staticmethod
    def get_unassigned_students_for_course(course_code: str):
        """Get students who have the course code in their config but aren't assigned to a batch"""
        # Get all user configs with this course code
        configs = UserConfigMappingRepository.get_configs_by_course_code(course_code)
        print(configs)
        unassigned_students = []
        for config in configs:
            user = User.objects.filter(email=config.email).first()
            if not user or not user.is_student:
                continue

            # Check if student is already assigned to a batch for this course
            course = CourseRepository.get_course_by_code(course_code)
            if not course:
                continue

            student = StudentRepository.get_student_by_student_id(user.id)
            if not student:
                continue

            # Check if student is already in a batch for this course
            is_assigned = student.batches.filter(course=course).exists()

            if not is_assigned:
                unassigned_students.append(
                    {
                        "id": user.id,
                        "email": user.email,
                        "name": f"{user.first_name} {user.last_name}".strip(),
                        "course_codes": config.config.get("course_codes", "").split(
                            ","
                        ),
                    }
                )

        return unassigned_students


class StudentDashboardUsecase:
    @staticmethod
    def compute_course_hours(user):
        """Compute the total hours of a course"""
        user_id = user.id
        reports = UserCourseReportRepository.get_reports_data_by_user_id(user_id)
        form_link = ""
        if settings.DEPLOYMENT_TYPE == "DEFAULT":
            user_profile = UserProfileRepository.get(user_id)
            user_data = user_profile.user_data
            aadhar_number = UserProfileRepository.fetch_value_from_form(
                "beneficiaryId", user_data
            )
            name = user.get_full_name
            email = user.email
            phone = user_profile.phone
            form_link = (
                f"https://docs.google.com/forms/d/e/1FAIpQLSePJK1BHFMtPrZgrLJT98NUrvn78oxhf9UmQzH21EcSlkLO8A/viewform"
                f"?usp=pp_url&entry.1785019217={aadhar_number}&entry.112616835={name}&entry.1447575587={phone}"
                f"&entry.1182700804={email}"
            )

        # Use a list to keep track of course data instead of a dict keyed by course_id
        data = []
        for report in reports:
            # Try to find an existing entry for this course in the list
            course_data = next(
                (item for item in data if item.get("course_id") == report.course_id),
                None,
            )
            if not course_data:
                course_data = {
                    "card_type": "certificate",
                    "course_id": report.course_id,
                    "course_name": report.course.title,
                    "course_hours": report.course.course_hours,
                    "total_time_spent": report.total_time_spent / 60,
                    "updated_at": report.last_updated,
                }
                data.append(course_data)
                if settings.DEPLOYMENT_TYPE == "DEFAULT":
                    data.append({"card_type": "form", "concent_form_link": form_link})
            else:
                # If data for the course already exists, there's nothing extra to update
                # as the original logic simply overwrites. Adjust if aggregation is needed.
                pass
        return data


class StudentEnrollmentUsecase:
    """Usecase class for managing student enrollments"""

    class StudentNotFound(Exception):
        pass

    class CourseNotFound(Exception):
        pass

    class BatchNotFound(Exception):
        pass

    @staticmethod
    def remove_student_enrollment(student_id: int, course_id: int) -> dict:
        try:
            # Get student and validate existence
            student = StudentRepository.get_student_by_student_id(student_id)
            if not student:
                raise StudentEnrollmentUsecase.StudentNotFound("Student not found")

            # Get course and validate existence
            course = CourseRepository.get_course_by_id(course_id)
            if not course:
                raise StudentEnrollmentUsecase.CourseNotFound("Course not found")

            # Get batch for this student and course
            batch = BatchUseCase.get_batch_by_user_id_and_course_id(
                student_id, course_id
            )
            if not batch:
                raise StudentEnrollmentUsecase.BatchNotFound(
                    "Student is not enrolled in this course"
                )

            # Remove student from batch
            student.batches.remove(batch)

            # Update user config mapping
            config_mapping = UserConfigMappingRepository.get_user_config_mapping(
                student.student.email
            )
            if config_mapping and config_mapping.config:
                batch_ids = config_mapping.config.get("batch_id", "").split(",")
                if str(batch.id) in batch_ids:
                    batch_ids.remove(str(batch.id))
                    config_mapping.config["batch_id"] = ",".join(batch_ids)
                    config_mapping.save()

            # Log the unenrollment
            logger.info(
                f"Student {student_id} unenrolled from course {course_id}, batch {batch.id}"
            )

            return {
                "message": "Student unenrolled successfully",
                "student_id": student_id,
                "course_id": course_id,
                "batch_id": batch.id,
            }

        except Student.DoesNotExist:
            raise StudentEnrollmentUsecase.StudentNotFound("Student not found")
        except Course.DoesNotExist:
            raise StudentEnrollmentUsecase.CourseNotFound("Course not found")
