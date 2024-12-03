from accounts.repositories import StudentRepository, UserRepository, LecturerRepository
from course.models import Batch, LiveClassSeriesBatchAllocation
from course.repositories import (
    BatchRepository,
    CourseRepository,
    LiveClassSeriesBatchAllocationRepository,
    ModuleRepository
)
from meetings.repositories import MeetingSeriesRepository
from meetings.usecases import MeetingSeriesUsecase, MeetingUsecase
from accounts.repositories import CourseProviderRepository

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
            presenter_details = LecturerRepository.get_presenter_details_by_lecturer_id(
                batch.lecturer.id
            )

            if presenter_details:
                # Convert presenter_details to a serializable format if needed
                serializable_presenter_details = {
                    key: value for key, value in presenter_details.items() 
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
            key: value for key, value in presenter_details.items() 
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
    def create_batch(course_id, title, lecturer_id):
        course = CourseRepository.get_course_by_id(course_id)
        lecturer = UserRepository.get_user_by_id(lecturer_id)
        if not lecturer.is_lecturer:
            raise BatchUseCase.UserIsNotLecturerException()
        return BatchRepository.create_batch(course, title, lecturer)

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
            batch_data = {
                "id": batch.id,
                "title": batch.title,
                "course_id": batch.course_id,
                "lecturer_id": batch.lecturer_id,
                "start_date": batch.created_at,
                "students_count": len(batch.students.values()),  # Get student data
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

            # Collect reading resources
            resource_data_reading = [
                {
                    "type": "reading",
                    "id": resource.id,
                    "title": resource.title,
                    "url": resource.file.url,
                }
                for resource in module.uploads.all()
            ]

            # Collect video resources
            resource_data_video = [
                {
                    "type": "video",
                    "id": resource.id,
                    "title": resource.title,
                    "url": resource.video.url,
                }
                for resource in module.video_uploads.all()
            ]

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