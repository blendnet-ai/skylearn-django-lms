import json
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views.generic import CreateView
from django_filters.views import FilterView

from accounts.authentication import FirebaseAuthentication
from accounts.decorators import lecturer_required, student_required, course_provider_admin_required,course_provider_admin_or_lecturer_required
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
from core.models import Semester
from course.filters import CourseAllocationFilter, ProgramFilter
from course.forms import (
    CourseAddForm,
    CourseAllocationForm,
    EditCourseAllocationForm,
    ProgramForm,
    # UploadFormFile,
    # UploadFormVideo,
)
from course.models import Course, CourseAllocation, Program, Upload, UploadVideo, Module
from course.serializers import (
    BatchSerializer,
    LiveClassDateRangeSerializer,
    LiveClassSeriesSerializer,
    LiveClassUpdateSerializer,
)
from course.usecases import (
    BatchUseCase,
    CourseUseCase,
    LiveClassSeriesBatchAllocationUseCase,
    LiveClassUsecase,
)
from meetings.models import Meeting, MeetingSeries
from meetings.usecases import MeetingSeriesUsecase, MeetingUsecase
from result.models import TakenCourse

from django.views.decorators.csrf import csrf_exempt

from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import (
    authentication_classes,
    permission_classes,
    api_view,
)
from rest_framework.response import Response

from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import ListModelMixin
from rest_framework.decorators import (
    authentication_classes,
    permission_classes,
    api_view,
)
from rest_framework.response import Response

from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import ListModelMixin

# ########################################################
# Program Views
# ########################################################


@method_decorator(firebase_drf_authentication(IsLoggedIn, IsCourseProviderAdminOrLecturer), name="dispatch")
class ProgramFilterView(FilterView):

    filterset_class = ProgramFilter
    template_name = "course/program_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Programs"
        return context


@api_view(["GET", "POST"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsCourseProviderAdminOrLecturer])
def program_add(request):
    if request.method == "POST":
        form = ProgramForm(request.POST)
        if form.is_valid():
            program = form.save()
            messages.success(request, f"{program.title} program has been created.")
            return redirect("programs")
        messages.error(request, "Correct the error(s) below.")
    else:
        form = ProgramForm()
    return render(
        request, "course/program_add.html", {"title": "Add Program", "form": form}
    )


@api_view(["GET"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn])
def program_detail(request, pk):
    program = get_object_or_404(Program, pk=pk)
    courses = Course.objects.filter(program_id=pk).order_by("-year")
    credits = courses.aggregate(total_credits=Sum("credit"))
    paginator = Paginator(courses, 10)
    page = request.GET.get("page")
    courses = paginator.get_page(page)
    return render(
        request,
        "course/program_single.html",
        {
            "title": program.title,
            "program": program,
            "courses": courses,
            "credits": credits,
        },
    )


@api_view(["GET", "POST"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsCourseProviderAdminOrLecturer])
def program_edit(request, pk):
    program = get_object_or_404(Program, pk=pk)
    if request.method == "POST":
        form = ProgramForm(request.POST, instance=program)
        if form.is_valid():
            program = form.save()
            messages.success(request, f"{program.title} program has been updated.")
            return redirect("programs")
        messages.error(request, "Correct the error(s) below.")
    else:
        form = ProgramForm(instance=program)
    return render(
        request, "course/program_add.html", {"title": "Edit Program", "form": form}
    )


@api_view(["DELETE"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsCourseProviderAdminOrLecturer])
def program_delete(request, pk):
    program = get_object_or_404(Program, pk=pk)
    title = program.title
    program.delete()
    messages.success(request, f"Program {title} has been deleted.")
    return redirect("programs")


# ########################################################
# Course Views
# ########################################################


@api_view(["GET"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn])
def course_single(request, slug):
    course = get_object_or_404(Course, slug=slug)
    files = Upload.objects.filter(course__slug=slug)
    videos = UploadVideo.objects.filter(course__slug=slug)
    lecturers = CourseAllocation.objects.filter(courses__pk=course.id)
    return render(
        request,
        "course/course_single.html",
        {
            "title": course.title,
            "course": course,
            "files": files,
            "videos": videos,
            "lecturers": lecturers,
            "media_url": settings.MEDIA_URL,
        },
    )


@api_view(["GET", "POST"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsCourseProviderAdminOrLecturer])
def course_add(request, pk):
    program = get_object_or_404(Program, pk=pk)
    if request.method == "POST":
        form = CourseAddForm(request.POST)
        if form.is_valid():
            course = form.save()
            messages.success(
                request, f"{course.title} ({course.code}) has been created."
            )
            return redirect("program_detail", pk=program.pk)
        messages.error(request, "Correct the error(s) below.")
    else:
        form = CourseAddForm(initial={"program": program})
    return render(
        request,
        "course/course_add.html",
        {"title": "Add Course", "form": form, "program": program},
    )


@api_view(["GET", "POST"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsCourseProviderAdminOrLecturer])
def course_edit(request, slug):
    course = get_object_or_404(Course, slug=slug)
    if request.method == "POST":
        form = CourseAddForm(request.POST, instance=course)
        if form.is_valid():
            course = form.save()
            messages.success(
                request, f"{course.title} ({course.code}) has been updated."
            )
            return redirect("program_detail", pk=course.program.pk)
        messages.error(request, "Correct the error(s) below.")
    else:
        form = CourseAddForm(instance=course)
    return render(
        request, "course/course_add.html", {"title": "Edit Course", "form": form}
    )


@api_view(["DELETE"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsCourseProviderAdminOrLecturer])
def course_delete(request, slug):
    course = get_object_or_404(Course, slug=slug)
    title = course.title
    program_id = course.program.id
    course.delete()
    messages.success(request, f"Course {title} has been deleted.")
    return redirect("program_detail", pk=program_id)


# ########################################################
# Course Allocation Views
# ########################################################


@method_decorator(firebase_drf_authentication(IsLoggedIn, IsCourseProviderAdminOrLecturer), name="dispatch")
class CourseAllocationFormView(CreateView):
    form_class = CourseAllocationForm
    template_name = "course/course_allocation_form.html"

    def form_valid(self, form):
        lecturer = form.cleaned_data["lecturer"]
        selected_courses = form.cleaned_data["courses"]
        allocation, created = CourseAllocation.objects.get_or_create(lecturer=lecturer)
        allocation.courses.set(selected_courses)
        messages.success(
            self.request, f"Courses allocated to {lecturer.get_full_name} successfully."
        )
        return redirect("course_allocation_view")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Assign Course"
        return context


@method_decorator(firebase_drf_authentication(IsLoggedIn, IsCourseProviderAdminOrLecturer), name="dispatch")
class CourseAllocationFilterView(FilterView):
    filterset_class = CourseAllocationFilter
    template_name = "course/course_allocation_view.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Course Allocations"
        return context



@api_view(["GET", "POST"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsCourseProviderAdminOrLecturer])
def edit_allocated_course(request, pk):
    allocation = get_object_or_404(CourseAllocation, pk=pk)
    if request.method == "POST":
        form = EditCourseAllocationForm(request.POST, instance=allocation)
        if form.is_valid():
            form.save()
            messages.success(request, "Course allocation has been updated.")
            return redirect("course_allocation_view")
        messages.error(request, "Correct the error(s) below.")
    else:
        form = EditCourseAllocationForm(instance=allocation)
    return render(
        request,
        "course/course_allocation_form.html",
        {"title": "Edit Course Allocation", "form": form},
    )


@api_view(["DELETE"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsCourseProviderAdminOrLecturer])
def deallocate_course(request, pk):
    allocation = get_object_or_404(CourseAllocation, pk=pk)
    allocation.delete()
    messages.success(request, "Successfully deallocated courses.")
    return redirect("course_allocation_view")


# ########################################################
# File Upload Views
# ########################################################


# @api_view(["GET", "POST"])
# @authentication_classes([FirebaseAuthentication])
# @permission_classes([IsLoggedIn, IsCourseProviderAdminOrLecturer])
# def handle_file_upload(request, slug):
#     course = get_object_or_404(Course, slug=slug)
#     if request.method == "POST":
#         form = UploadFormFile(request.POST, request.FILES)
#         if form.is_valid():
#             upload = form.save(commit=False)
#             upload.course = course
#             upload.save()
#             messages.success(request, f"{upload.title} has been uploaded.")
#             return redirect("course_detail", slug=slug)
#         messages.error(request, "Correct the error(s) below.")
#     else:
#         form = UploadFormFile()
#     return render(
#         request,
#         "upload/upload_file_form.html",
#         {"title": "File Upload", "form": form, "course": course},
#     )


# @api_view(["GET", "POST"])
# @authentication_classes([FirebaseAuthentication])
# @permission_classes([IsLoggedIn, IsCourseProviderAdminOrLecturer])
# def handle_file_edit(request, slug, file_id):
#     course = get_object_or_404(Course, slug=slug)
#     upload = get_object_or_404(Upload, pk=file_id)
#     if request.method == "POST":
#         form = UploadFormFile(request.POST, request.FILES, instance=upload)
#         if form.is_valid():
#             upload = form.save()
#             messages.success(request, f"{upload.title} has been updated.")
#             return redirect("course_detail", slug=slug)
#         messages.error(request, "Correct the error(s) below.")
#     else:
#         form = UploadFormFile(instance=upload)
#     return render(
#         request,
#         "upload/upload_file_form.html",
#         {"title": "Edit File", "form": form, "course": course},
#     )


@api_view(["DELETE"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsCourseProviderAdminOrLecturer])
def handle_file_delete(request, slug, file_id):
    upload = get_object_or_404(Upload, pk=file_id)
    title = upload.title
    upload.delete()
    messages.success(request, f"{title} has been deleted.")
    return redirect("course_detail", slug=slug)


# ########################################################
# Video Upload Views
# ########################################################


# @api_view(["GET", "POST"])
# @authentication_classes([FirebaseAuthentication])
# @permission_classes([IsLoggedIn, IsCourseProviderAdminOrLecturer])
# def handle_video_upload(request, slug):
#     course = get_object_or_404(Course, slug=slug)
#     if request.method == "POST":
#         form = UploadFormVideo(request.POST, request.FILES)
#         if form.is_valid():
#             video = form.save(commit=False)
#             video.course = course
#             video.save()
#             messages.success(request, f"{video.title} has been uploaded.")
#             return redirect("course_detail", slug=slug)
#         messages.error(request, "Correct the error(s) below.")
#     else:
#         form = UploadFormVideo()
#     return render(
#         request,
#         "upload/upload_video_form.html",
#         {"title": "Video Upload", "form": form, "course": course},
#     )


@api_view(["GET"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn])
def handle_video_single(request, slug, video_slug):
    course = get_object_or_404(Course, slug=slug)
    video = get_object_or_404(UploadVideo, slug=video_slug)
    return render(
        request,
        "upload/video_single.html",
        {"video": video, "course": course},
    )


# @api_view(["GET", "POST"])
# @authentication_classes([FirebaseAuthentication])
# @permission_classes([IsLoggedIn, IsCourseProviderAdminOrLecturer])
# def handle_video_edit(request, slug, video_slug):
#     course = get_object_or_404(Course, slug=slug)
#     video = get_object_or_404(UploadVideo, slug=video_slug)
#     if request.method == "POST":
#         form = UploadFormVideo(request.POST, request.FILES, instance=video)
#         if form.is_valid():
#             video = form.save()
#             messages.success(request, f"{video.title} has been updated.")
#             return redirect("course_detail", slug=slug)
#         messages.error(request, "Correct the error(s) below.")
#     else:
#         form = UploadFormVideo(instance=video)
#     return render(
#         request,
#         "upload/upload_video_form.html",
#         {"title": "Edit Video", "form": form, "course": course},
#     )


@api_view(["DELETE"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsCourseProviderAdminOrLecturer])
def handle_video_delete(request, slug, video_slug):
    video = get_object_or_404(UploadVideo, slug=video_slug)
    title = video.title
    video.delete()
    messages.success(request, f"{title} has been deleted.")
    return redirect("course_detail", slug=slug)


# ########################################################
# Course Registration Views
# ########################################################


@api_view(["GET", "POST"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsStudent])
def course_registration(request):
    if request.method == "POST":
        student = Student.objects.get(student__pk=request.user.id)
        ids = ()
        data = request.POST.copy()
        data.pop("csrfmiddlewaretoken", None)  # remove csrf_token
        for key in data.keys():
            ids = ids + (str(key),)
        for s in range(0, len(ids)):
            course = Course.objects.get(pk=ids[s])
            obj = TakenCourse.objects.create(student=student, course=course)
            obj.save()
        messages.success(request, "Courses registered successfully!")
        return redirect("course_registration")
    else:
        current_semester = Semester.objects.filter(is_current_semester=True).first()
        if not current_semester:
            messages.error(request, "No active semester found.")
            return render(request, "course/course_registration.html")

        # student = Student.objects.get(student__pk=request.user.id)
        student = get_object_or_404(Student, student__id=request.user.id)
        taken_courses = TakenCourse.objects.filter(student__student__id=request.user.id)
        t = ()
        for i in taken_courses:
            t += (i.course.pk,)

        courses = (
            Course.objects.filter(
                program__pk=student.program.id,
                level=student.level,
                semester=current_semester,
            )
            .exclude(id__in=t)
            .order_by("year")
        )
        all_courses = Course.objects.filter(
            level=student.level, program__pk=student.program.id
        )

        no_course_is_registered = False  # Check if no course is registered
        all_courses_are_registered = False

        registered_courses = Course.objects.filter(level=student.level).filter(id__in=t)
        if (
            registered_courses.count() == 0
        ):  # Check if number of registered courses is 0
            no_course_is_registered = True

        if registered_courses.count() == all_courses.count():
            all_courses_are_registered = True

        total_first_semester_credit = 0
        total_sec_semester_credit = 0
        total_registered_credit = 0
        for i in courses:
            if i.semester == "First":
                total_first_semester_credit += int(i.credit)
            if i.semester == "Second":
                total_sec_semester_credit += int(i.credit)
        for i in registered_courses:
            total_registered_credit += int(i.credit)
        context = {
            "is_calender_on": True,
            "all_courses_are_registered": all_courses_are_registered,
            "no_course_is_registered": no_course_is_registered,
            "current_semester": current_semester,
            "courses": courses,
            "total_first_semester_credit": total_first_semester_credit,
            "total_sec_semester_credit": total_sec_semester_credit,
            "registered_courses": registered_courses,
            "total_registered_credit": total_registered_credit,
            "student": student,
        }
        return render(request, "course/course_registration.html", context)


@api_view(["GET", "POST"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsStudent])
def course_drop(request):
    if request.method == "POST":
        student = get_object_or_404(Student, student__pk=request.user.id)
        course_ids = request.POST.getlist("course_ids")

        for course_id in course_ids:
            course = get_object_or_404(Course, pk=course_id)
            TakenCourse.objects.filter(student=student, course=course).delete()
        messages.success(request, "Courses dropped successfully!")
        return redirect("course_registration")


# ########################################################
# User Course List View
# ########################################################


@api_view(["GET"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn])
def user_course_list(request):
    if request.user.is_lecturer:
        courses = Course.objects.filter(allocated_course__lecturer__pk=request.user.id)
        return render(request, "course/user_course_list.html", {"courses": courses})

    if request.user.is_student:
        student = get_object_or_404(Student, student__pk=request.user.id)
        taken_courses = TakenCourse.objects.filter(student=student)
        return render(
            request,
            "course/user_course_list.html",
            {"student": student, "taken_courses": taken_courses},
        )

    # For other users
    return render(request, "course/user_course_list.html")


# admin/course provider
@api_view(["POST"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsCourseProviderAdmin])
def create_live_class_series(request):
    serializer = LiveClassSeriesSerializer(data=request.data)

    if serializer.is_valid():
        try:
            live_class_series_id, batches_allocated, batches_failed_to_allocate, presenter_assignement = (
                LiveClassUsecase.create_live_class_series(
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
                    "message": f"Live class created successfully.",
                    "id": live_class_series_id,
                    "batches_allocated": batches_allocated,
                    "batches_failed_to_allocate": batches_failed_to_allocate,
                    "presenter_assignment":presenter_assignement
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
            batches_allocated, batches_failed_to_allocate,presenter_assignement = (
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
                    "presenter_assignement":presenter_assignement
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
@permission_classes([IsLoggedIn,IsCourseProviderAdminOrLecturer])
def get_batches_by_course_id(request, course_id):
    try:
        #request.user=User.objects.get(id=30)
        user=request.user
        batches = BatchUseCase.get_batches_by_course_id(user,course_id)
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
    return Response({'module_data': module_data}, status=status.HTTP_200_OK)


@api_view(["GET"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn])
def user_courses_list(request):
    #request.user=User.objects.get(id=4)
    courses, role=CourseUseCase.get_courses_for_student_or_lecturer(request.user)
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
    #request.user=User.objects.get(id=4)
    meeting=MeetingUsecase.get_meeting_by_id(meeting_id)
    return Response({"data":meeting}, status=status.HTTP_200_OK)


@api_view(["GET"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn])
def get_live_class_details(request, series_id):
    #request.user=User.objects.get(id=4)
    meeting_series=MeetingSeriesUsecase.get_meeting_series(series_id)
    return Response({"data":meeting_series}, status=status.HTTP_200_OK)

@api_view(["GET"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn])
def get_sas_url(request):
    # Get the meeting_blob_url from query parameters
    blob_url = request.GET.get("blob_url")
    
    if not blob_url:
        return Response(
            {"error": "blob_url is required as a query parameter"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        sas_url = MeetingUsecase.get_sas_url_for_recording(blob_url)
        return Response({"url": sas_url}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Error generating SAS URL: {str(e)}"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn])
def get_recordings(request):
        user_id = request.user.id
        if request.user.is_student:
            role = 'student'
        elif request.user.is_lecturer:
            role = 'lecturer'
        elif request.user.is_course_provider_admin:
            role = 'course_provider_admin'
           
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
        {
            "students": students,
            "total_count": len(students)
        }, 
        status=status.HTTP_200_OK
    )
