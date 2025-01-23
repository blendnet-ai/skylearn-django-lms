from accounts.authentication import FirebaseAuthentication
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
)
from course.usecases import (
    BatchUseCase,
    CourseUseCase,
    LiveClassSeriesBatchAllocationUseCase,
    LiveClassUsecase,
    BatchMessageUsecase,
    PersonalMessageUsecase,
    AssessmentModuleUsecase
)
from meetings.models import Meeting, MeetingSeries
from meetings.usecases import MeetingSeriesUsecase, MeetingUsecase


from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import (
    authentication_classes,
    permission_classes,
    api_view,
)
from rest_framework.response import Response
from accounts.usecases import StudentProfileUsecase

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
    user_id=request.user.id
    # extract module assessment_generation_configs
    assessment_generation_configs = AssessmentModuleUsecase.fetch_assessment_display_data(user_id,course_id,module_id)

    if not assessment_generation_configs or len(assessment_generation_configs)==0:
        return Response(
            {"error": f"No assessment configs for course {course_id} module {module_id}"},
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
    # Get the meeting_blob_url from query parameters
    blob_url = request.query_params.get("blob_url")

    if not blob_url:
        return Response(
            {"error": "blob_url is required as a query parameter"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        sas_url = MeetingUsecase.get_sas_url_for_recording(blob_url)
        return Response({"url": sas_url}, status=status.HTTP_200_OK)
    except Exception as e:
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

    except Exception as e:
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
            message=serializer.validated_data["message"]
        )
        return Response(
            {"message": "Messages sent"}, status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

