from accounts.authentication import FirebaseAuthentication
from custom_auth.authentication import HardcodedAuthentication
from accounts.models import Student, User
from accounts.permissions import (
    IsCourseProviderAdmin,
    IsCourseProviderAdminOrLecturer,
    IsLecturer,
    IsLoggedIn,
    IsStudent,
    IsSuperuser,
    firebase_drf_authentication,
)

from course.models import Course, CourseAllocation, Upload, UploadVideo, Module
from course.serializers import (
    BatchSerializer,
    CourseMessageSerializer,
    LiveClassDateRangeSerializer,
    LiveClassSeriesSerializer,
    LiveClassUpdateSerializer,
    PersonalMessageSerializer,
    BatchWithStudentsSerializer,
    BulkEnrollmentSerializer,
    CourseSerializer,
    ModuleSerializer,
    UploadMaterialSerializer,
    DeleteMaterialTypeSerializer,
)
from course.usecases import (
    BatchUseCase,
    CourseUseCase,
    LiveClassSeriesBatchAllocationUseCase,
    LiveClassUsecase,
    BatchMessageUsecase,
    PersonalMessageUsecase,
    AssessmentModuleUsecase,
    StudentDashboardUsecase,
    UnassignedStudentsUsecase,
    StudentEnrollmentUsecase,
    CourseContentDriveUsecase,
)
from meetings.models import Meeting, MeetingSeries
from meetings.usecases import MeetingSeriesUsecase, MeetingUsecase
from Feedback.repositories import FeedbackFormRepository
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from .services import BulkEnrollmentService
from rest_framework import serializers
from evaluation.usecases import AssessmentUseCase

from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import (
    authentication_classes,
    permission_classes,
    api_view,
)
from rest_framework.response import Response
from accounts.usecases import StudentProfileUsecase
from django.conf import settings
from accounts.repositories import CourseProviderRepository
from course.repositories import ModuleRepository, CourseRepository


# admin/course provider
@api_view(["POST"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsCourseProviderAdmin])
def create_live_class_series(request):
    serializer = LiveClassSeriesSerializer(data=request.data)

    if serializer.is_valid():
        try:
            (
                live_class_series_id,
                batches_allocated,
                batches_failed_to_allocate,
                presenter_assignement,
            ) = LiveClassUsecase.create_live_class_series(
                title=serializer.validated_data["title"],
                batch_ids=serializer.validated_data["batch_ids"],
                start_time=serializer.validated_data["start_time"],
                start_date=serializer.validated_data["start_date"],
                duration=serializer.validated_data["duration"],
                end_date=serializer.validated_data["end_date"],
                recurrence_type=serializer.validated_data["recurrence_type"],
                weekday_schedule=serializer.validated_data.get(
                    "weekday_schedule", None
                ),
                monthly_day=serializer.validated_data.get("monthly_day", None),
            )

            return Response(
                {
                    "message": f"Live class created successfully.",
                    "id": live_class_series_id,
                    "batches_allocated": batches_allocated,
                    "batches_failed_to_allocate": batches_failed_to_allocate,
                    "presenter_assignment": presenter_assignement,
                },
                status=status.HTTP_201_CREATED,
            )
        except (
            # Sanchit -  these could have inherited a single exception and then that be caught here
            # Also, it would be cleaner if all these exceptions are raised internally in a single validation function
            # somewhere
            MeetingSeriesUsecase.LecturerNotAssigned,
            MeetingSeriesUsecase.WeekdayScheduleNotSet,
            MeetingSeriesUsecase.MonthlyDayNotSet,
            MeetingSeriesUsecase.InvalidWeekdaySchedule,
            MeetingSeriesUsecase.NoRecurringDatesFound,
            MeetingSeriesUsecase.StartDateInPast,
            MeetingSeriesUsecase.EndDateSmallerThanStartDate,
        ) as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST,
    )


# admin/course provider
@api_view(["PUT"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsCourseProviderAdmin])
def update_live_class_series(request, id):
    serializer = LiveClassSeriesSerializer(data=request.data)
    if serializer.is_valid():
        try:
            batches_allocated, batches_failed_to_allocate, presenter_assignement = (
                LiveClassUsecase.update_live_class_series(
                    id,
                    title=serializer.validated_data["title"],
                    batch_ids=serializer.validated_data["batch_ids"],
                    start_time=serializer.validated_data["start_time"],
                    start_date=serializer.validated_data["start_date"],
                    duration=serializer.validated_data["duration"],
                    end_date=serializer.validated_data["end_date"],
                    recurrence_type=serializer.validated_data["recurrence_type"],
                    weekday_schedule=serializer.validated_data.get(
                        "weekday_schedule", None
                    ),
                    monthly_day=serializer.validated_data.get("monthly_day", None),
                )
            )
            return Response(
                {
                    "message": f"Live class series updated successfully.",
                    "batches_allocated": batches_allocated,
                    "batches_failed_to_allocate": batches_failed_to_allocate,
                    "presenter_assignement": presenter_assignement,
                },
                status=status.HTTP_200_OK,
            )
        except MeetingSeries.DoesNotExist:
            return Response(
                {"error": "Live class series not found"},
                status=status.HTTP_404_NOT_FOUND,
            )


# admin/course provider
@api_view(["DELETE"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsCourseProviderAdmin])
def delete_live_class_series(_, id):
    try:
        LiveClassUsecase.delete_live_class_series(id)
        return Response(
            {"message": f"Live class series deleted successfully."},
            status=status.HTTP_200_OK,
        )
    except MeetingSeries.DoesNotExist:
        return Response(
            {"error": "Live class series not found"}, status=status.HTTP_404_NOT_FOUND
        )


# admin/course provider (can be modified for lecturer later, not in requirements currently)
@api_view(["GET"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsCourseProviderAdminOrLecturer])
def get_live_classes_by_batch_id(request, batch_id):

    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    serializer = LiveClassDateRangeSerializer(
        data={"start_date": start_date, "end_date": end_date}
    )

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    live_classes = (
        LiveClassSeriesBatchAllocationUseCase.get_live_classes_of_batch_in_period(
            batch_id, start_date, end_date
        )
    )

    return Response(live_classes, status=status.HTTP_200_OK)


# student/lecturer
@api_view(["GET"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn])
def get_live_classes(request):
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    serializer = LiveClassDateRangeSerializer(
        data={"start_date": start_date, "end_date": end_date}
    )

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    live_classes = LiveClassUsecase.get_live_classes_in_period_for_lecturer_or_student(
        request.user, start_date, end_date
    )

    return Response(live_classes, status=status.HTTP_200_OK)


# student (can be modified for lecturer and course provider later, not in requirements currently)
@api_view(["GET"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn])
def get_live_classes_by_course_id(request, course_id):
    try:
        # request.user=User.objects.get(id=2)
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        serializer = LiveClassDateRangeSerializer(
            data={"start_date": start_date, "end_date": end_date}
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        live_classes = (
            LiveClassUsecase.get_live_classes_of_course_in_period_for_student(
                course_id, request.user.id, start_date, end_date
            )
        )

        return Response(live_classes, status=status.HTTP_200_OK)
    except LiveClassUsecase.UserNotInBatchOfCourseException as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_404_NOT_FOUND,
        )


@api_view(["DELETE"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsCourseProviderAdmin])
def delete_live_class(_, id):
    try:
        MeetingUsecase.delete_meeting(id)
        return Response(
            {"message": f"Live class deleted successfully."},
            status=status.HTTP_200_OK,
        )
    except Meeting.DoesNotExist:
        return Response(
            {"error": "Live class not found"}, status=status.HTTP_404_NOT_FOUND
        )


@api_view(["PUT"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsCourseProviderAdmin])
def update_live_class(request, id):
    serializer = LiveClassUpdateSerializer(data=request.data)
    if serializer.is_valid():
        try:
            MeetingUsecase.update_meeting(
                id,
                serializer.validated_data.get("start_time", None),
                serializer.validated_data.get("duration", None),
                serializer.validated_data.get("start_date", None),
            )

            return Response(
                {"message": "Live class updated successfully."},
                status=status.HTTP_200_OK,
            )

        except Meeting.DoesNotExist:
            return Response(
                {"error": "Live class not found"}, status=status.HTTP_404_NOT_FOUND
            )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST,
    )


@api_view(["POST"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsCourseProviderAdmin])
def create_batch(request, course_id):
    serializer = BatchSerializer(data=request.data)

    if serializer.is_valid():
        try:
            batch = BatchUseCase.create_batch(
                course_id,
                serializer.validated_data["title"],
                serializer.validated_data["lecturer_id"],
            )
            return Response(
                {"message": f"Batch created successfully.", "id": batch.id},
                status=status.HTTP_201_CREATED,
            )
        except Course.DoesNotExist:
            return Response(
                {"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except User.DoesNotExist:
            return Response(
                {"error": "Invalid lecturer id"}, status=status.HTTP_400_BAD_REQUEST
            )
        except BatchUseCase.UserIsNotLecturerException as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsCourseProviderAdminOrLecturer])
def get_batches_by_course_id(request, course_id):
    try:
        # request.user=User.objects.get(id=30)
        user = request.user
        batches = BatchUseCase.get_batches_by_course_id(user, course_id)
        return Response(batches, status=status.HTTP_200_OK)
    except Course.DoesNotExist:
        return Response({"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND)


@api_view(["GET"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn])
def get_courses_by_course_provider_id(request, course_provider_id):
    course_provider = CourseUseCase.get_courses_by_course_provider(course_provider_id)
    return Response(course_provider, status=status.HTTP_200_OK)


@api_view(["GET"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn])
def get_modules_and_resources_by_course_id(request, course_id):
    module_data = CourseUseCase.get_modules_by_course_id(course_id)
    if not module_data:
        return Response(
            {"error": "No modules found for the given course ID."},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response({"module_data": module_data}, status=status.HTTP_200_OK)


@api_view(["GET"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn])
def get_assessments_by_module_id(request, course_id, module_id):
    user_id = request.user.id
    # extract module assessment_generation_configs
    assessment_generation_configs = (
        AssessmentModuleUsecase.fetch_assessment_display_data(
            user_id, course_id, module_id
        )
    )

    if not assessment_generation_configs or len(assessment_generation_configs) == 0:
        return Response(
            {
                "error": f"No assessment configs for course {course_id} module {module_id}"
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response(
        {"assessment_generation_configs": assessment_generation_configs},
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn])
def user_courses_list(request):
    # request.user=User.objects.get(id=4)
    courses, role = CourseUseCase.get_courses_for_student_or_lecturer(request.user)
    if courses:
        return Response({"courses": courses, "role": role}, status=status.HTTP_200_OK)
    else:
        return Response(
            {"error": "No Courses Found For User"}, status=status.HTTP_404_NOT_FOUND
        )


@api_view(["GET"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn])
def get_meeting_details(request, meeting_id):
    # request.user=User.objects.get(id=4)
    meeting = MeetingUsecase.get_meeting_by_id(meeting_id)
    return Response({"data": meeting}, status=status.HTTP_200_OK)


@api_view(["GET"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn])
def get_live_class_details(request, series_id):
    # request.user=User.objects.get(id=4)
    meeting_series = MeetingSeriesUsecase.get_meeting_series(series_id)
    return Response({"data": meeting_series}, status=status.HTTP_200_OK)


@api_view(["GET"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn])
def get_sas_url(request):
    blob_url = request.query_params.get("blob_url")

    if not blob_url:
        return Response(
            {"error": "blob_url is required as a query parameter"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        sas_url = MeetingUsecase.get_sas_url_for_recording(blob_url)
        return Response({"url": sas_url}, status=status.HTTP_200_OK)
    except (ValueError, KeyError, AttributeError) as e:
        return Response(
            {"error": f"Error generating SAS URL: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn])
def get_recordings(request):
    user_id = request.user.id
    if request.user.is_student:
        role = "student"
    elif request.user.is_lecturer:
        role = "lecturer"
    elif request.user.is_course_provider_admin:
        role = "course_provider_admin"

    recordings = MeetingUsecase.get_recordings_by_user_role(user_id, role)
    return Response(recordings, status=status.HTTP_200_OK)


@api_view(["GET"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsCourseProviderAdminOrLecturer])
def get_students_list(request):
    """
    Get list of students for lecturer or course provider admin
    """

    students = BatchUseCase.get_students_for_lecturer_or_provider(request.user)
    return Response(
        {"students": students, "total_count": len(students)}, status=status.HTTP_200_OK
    )


@api_view(["GET"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsCourseProviderAdminOrLecturer])
def get_student_details(request, student_id):
    """
    Get details of a student for lecturer or course provider admin
    """
    try:
        student_profile = StudentProfileUsecase.get_student_profile(student_id)
        return Response(student_profile, status=status.HTTP_200_OK)
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)


@api_view(["POST"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsCourseProviderAdminOrLecturer])
def send_course_batch_message(request):
    """
    Send message to all students in a batch for a specific course
    """
    serializer = CourseMessageSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        stats = BatchMessageUsecase.send_batch_messages(
            batch_id=serializer.validated_data["batch_id"],
            subject=serializer.validated_data["subject"],
            message=serializer.validated_data["message"],
        )
        return Response(
            {"message": "Messages sent", "stats": stats}, status=status.HTTP_200_OK
        )
    except (ValueError, BatchUseCase.BatchDoesNotExist) as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsCourseProviderAdminOrLecturer])
def send_course_personal_message(request):
    serializer = PersonalMessageSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    try:
        PersonalMessageUsecase.send_personal_message(
            user_id=serializer.validated_data["user_id"],
            message=serializer.validated_data["message"],
        )
        return Response({"message": "Messages sent"}, status=status.HTTP_200_OK)
    except (ValueError, User.DoesNotExist) as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsCourseProviderAdmin])
def create_batch_with_students(request, course_id):
    """Create a batch and assign students to it"""
    serializer = BatchWithStudentsSerializer(data=request.data)
    form = FeedbackFormRepository.get(id=1)
    if form is None:
        return Response(
            {
                "error": "Error in creating Batch : Specified Feedback Form doesnot exists"
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if serializer.is_valid():
        try:
            # Create batch
            batch, created = BatchUseCase.create_batch(
                course_id=course_id,
                title=serializer.validated_data["title"],
                lecturer_id=serializer.validated_data["lecturer_id"],
                start_date=serializer.validated_data.get("start_date"),
                end_date=serializer.validated_data.get("end_date"),
                form=form,
            )

            # Assign students
            student_ids = serializer.validated_data.get("student_ids", [])
            BatchUseCase.add_students_to_batch(batch.id, student_ids)

            return Response(
                {"message": "Batch created successfully", "batch_id": batch.id},
                status=status.HTTP_201_CREATED,
            )

        except (
            ValueError,
            Course.DoesNotExist,
            User.DoesNotExist,
            BatchUseCase.UserIsNotLecturerException,
        ) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsCourseProviderAdmin])
def get_unassigned_students(request, course_code):
    """Get students who have the course code but aren't assigned to a batch"""
    students = UnassignedStudentsUsecase.get_unassigned_students_for_course(course_code)
    return Response(
        {"students": students, "total_count": len(students)}, status=status.HTTP_200_OK
    )


@api_view(["GET"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsStudent])
def get_student_dashboard_data(request):
    """Get student dashboard data"""
    data = StudentDashboardUsecase.compute_course_hours(request.user)
    return Response(data, status=status.HTTP_200_OK)


class BulkEnrollmentView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    authentication_classes = [FirebaseAuthentication]
    permission_classes = [IsLoggedIn, IsCourseProviderAdmin]
    serializer_class = BulkEnrollmentSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            file = serializer.validated_data["file"]
            service = BulkEnrollmentService(file)
            result = service.process()

            return Response(
                {
                    "message": "Bulk enrollment processed successfully",
                    "data": {
                        "success_count": result["success_count"],
                        "failed_count": result["failed_count"],
                        "success": result["success"],  # Limit success examples
                        "failures": result["failed"],  # Show all failures for debugging
                    },
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"error": f"Failed to process file: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


@api_view(["DELETE"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsCourseProviderAdmin])
def remove_student_enrollment(request, course_id, student_id):
    """Remove student enrollment from a course"""
    try:
        result = StudentEnrollmentUsecase.remove_student_enrollment(
            student_id=student_id, course_id=course_id
        )
        return Response(result, status=status.HTTP_200_OK)

    except StudentEnrollmentUsecase.StudentNotFound:
        return Response(
            {"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND
        )
    except StudentEnrollmentUsecase.CourseNotFound:
        return Response({"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND)
    except StudentEnrollmentUsecase.BatchNotFound:
        return Response(
            {"error": "Student is not enrolled in this course"},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsCourseProviderAdmin])
def create_course(request):
    """Create a new course"""
    serializer = CourseSerializer(data=request.data)

    if serializer.is_valid():
        try:
            # Get course provider using CourseProviderUsecase
            course_provider = CourseProviderRepository.get_course_provider_by_user_id(
                request.user.id
            )
            if not course_provider:
                return Response(
                    {"error": "Course provider not found for this user"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            course = CourseUseCase.create_course(
                title=serializer.validated_data["title"],
                code=serializer.validated_data["code"],
                summary=serializer.validated_data["summary"],
                course_hours=serializer.validated_data["course_hours"],
                course_provider=course_provider,
            )

            return Response(
                {
                    "message": "Course created successfully",
                    "course": CourseSerializer(course).data,
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["PUT"])
@authentication_classes([HardcodedAuthentication])
# @permission_classes([IsLoggedIn, IsCourseProviderAdmin])
def update_course(request, course_id):
    """Update an existing course"""
    try:
        course = Course.objects.get(id=course_id)

        serializer = CourseSerializer(course, data=request.data, partial=True)
        if serializer.is_valid():
            updated_course = CourseUseCase.update_course(
                course_id=course_id,
                title=serializer.validated_data.get("title"),
                summary=serializer.validated_data.get("summary"),
                course_hours=serializer.validated_data.get("course_hours"),
                code=serializer.validated_data.get("code"),
            )
            return Response(
                {
                    "message": "Course updated successfully",
                    "course": CourseSerializer(updated_course).data,
                },
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    except Course.DoesNotExist:
        return Response({"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND)


@api_view(["DELETE"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsCourseProviderAdmin])
def delete_course(request, course_id):
    """Delete a course"""
    try:
        course = Course.objects.get(id=course_id)

        CourseUseCase.delete_course(course_id)
        return Response(
            {"message": "Course deleted successfully"}, status=status.HTTP_200_OK
        )

    except Course.DoesNotExist:
        return Response({"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND)


@api_view(["POST"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsCourseProviderAdmin])
def create_module(request, course_id):
    """Create a new module in a course"""
    try:
        course = Course.objects.get(id=course_id)
        serializer = ModuleSerializer(data=request.data)

        if serializer.is_valid():
            module = ModuleRepository.create_module(
                course=course,
                title=serializer.validated_data["title"],
                order_in_course=serializer.validated_data["order_in_course"],
            )

            return Response(
                {
                    "message": "Module created successfully",
                    "module": ModuleSerializer(module).data,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    except Course.DoesNotExist:
        return Response({"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND)


@api_view(["PUT"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsCourseProviderAdmin])
def update_module(request, course_id, module_id):
    """Update an existing module"""
    try:
        module = Module.objects.get(id=module_id, course_id=course_id)
        serializer = ModuleSerializer(module, data=request.data, partial=True)

        if serializer.is_valid():
            updated_module = ModuleRepository.update_module(
                module_id,
                title=serializer.validated_data.get("title"),
                order_in_course=serializer.validated_data.get("order_in_course"),
            )

            return Response(
                {
                    "message": "Module updated successfully",
                    "module": ModuleSerializer(updated_module).data,
                },
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    except Module.DoesNotExist:
        return Response({"error": "Module not found"}, status=status.HTTP_404_NOT_FOUND)


@api_view(["DELETE"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsCourseProviderAdmin])
def delete_module(request, course_id, module_id):
    """Delete a module"""
    try:
        module = Module.objects.get(id=module_id, course_id=course_id)
        ModuleRepository.delete_module(module_id)

        # Reorder remaining modules
        ModuleRepository.reorder_modules(course_id)

        return Response(
            {"message": "Module deleted successfully"}, status=status.HTTP_200_OK
        )

    except Module.DoesNotExist:
        return Response({"error": "Module not found"}, status=status.HTTP_404_NOT_FOUND)


@api_view(["POST"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsCourseProviderAdmin])
def upload_material(request):
    """Upload a reading material"""
    serializer = UploadMaterialSerializer(data=request.data)

    if serializer.is_valid():
        try:
            course = serializer.validated_data["course"]
            module = serializer.validated_data["module"]
            file_type = serializer.validated_data["file_type"]
            title = serializer.validated_data["title"]

            # Verify module belongs to course
            if module.course_id != course.id:
                raise ValueError("Module does not belong to the specified course")

            if file_type == "reading":
                # Get or create Upload object
                upload, created = Upload.objects.get_or_create(
                    title=title,
                    course=course,
                    module=module,
                    defaults={"blob_url": ""},  # Only used when creating new object
                )
                blob_path = f"{course.code}/{module.title}/Reading Resources/{title}"
            elif file_type == "video":
                # Get or create UploadVideo object
                upload, created = UploadVideo.objects.get_or_create(
                    title=title,
                    course=course,
                    module=module,
                    defaults={"blob_url": ""},  # Only used when creating new object
                )
                blob_path = f"{course.code}/{module.title}/Video Resources/{title}"

            # Handle file upload to blob storage only if it's a new upload or blob_url is empty
            if created or not upload.blob_url:
                blob_url = AssessmentUseCase.fetch_azure_storage_url(
                    blob_name=blob_path,
                    container_name=settings.AZURE_STORAGE_COURSE_MATERIALS_CONTAINER_NAME,
                )
                upload.blob_url = blob_url
                upload.save()

            return Response(
                {
                    "message": f"{'Created' if created else 'Updated'} {file_type} material Blob successfully",
                    "upload_id": upload.id,
                    "blob_url": upload.blob_url,
                },
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"error": f"Error uploading material: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["DELETE"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsCourseProviderAdmin])
def delete_material(request, type, upload_id):
    """Delete a reading material"""
    # Validate type parameter
    type_serializer = DeleteMaterialTypeSerializer(data={"type": type})
    if not type_serializer.is_valid():
        return Response(type_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Use appropriate model based on type
        if type == "reading":
            upload = Upload.objects.get(id=upload_id)
        elif type == "video":
            upload = UploadVideo.objects.get(id=upload_id)

        upload.delete()
        return Response(
            {"message": f"{type.capitalize()} material deleted successfully"},
            status=status.HTTP_200_OK,
        )
    except (Upload.DoesNotExist, UploadVideo.DoesNotExist):
        return Response(
            {"error": f"{type.capitalize()} material not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
