from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from accounts.authentication import FirebaseAuthentication
from accounts.decorators import admin_required, lecturer_required
from accounts.models import User, Student
from accounts.permissions import IsLoggedIn, IsLecturer, IsSuperuser
from .forms import SessionForm, SemesterForm, NewsAndEventsForm
from .models import NewsAndEvents, ActivityLog, Session, Semester
from rest_framework.decorators import authentication_classes, permission_classes
from rest_framework.decorators import api_view
from urllib.parse import urlencode


# ########################################################
# Saksham
# ########################################################
@login_required
def sakshm_embed_view(request, path):
    query_params = request.GET.dict()

    query_string = "?" + urlencode(query_params)
    print("query_string", query_string)

    return render(
        request,
        "core/saksham_wrapper.html",
        {
            "path": "http://localhost:3000/" + path + query_string,
        },
    )


def sakshm_embed_view_with_slug(request, slug):
    return render(
        request,
        "core/saksham_wrapper.html",
        {
            "path": "http://localhost:3000/" + slug,
        },
    )


# ########################################################
# News & Events
# ########################################################


@api_view(["GET"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn])
def home_view(request):
    path = "http://localhost:3000/"
    if request.user.is_student or request.user.is_lecturer:
        path += "home-lms"
    else:
        path += "course-provider-admin/home-lms"

    return render(
        request,
        "core/index.html",
        {
            "path": path,
        },
    )
    


@api_view(["GET"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsSuperuser])
def dashboard_view(request):
    logs = ActivityLog.objects.all().order_by("-created_at")[:10]
    gender_count = Student.get_gender_count()
    context = {
        "student_count": User.objects.get_student_count(),
        "lecturer_count": User.objects.get_lecturer_count(),
        "superuser_count": User.objects.get_superuser_count(),
        "males_count": gender_count["M"],
        "females_count": gender_count["F"],
        "logs": logs,
    }
    return render(request, "core/dashboard.html", context)


@api_view(["GET", "POST"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn])
def post_add(request):
    if request.method == "POST":
        form = NewsAndEventsForm(request.POST)
        title = form.cleaned_data.get("title", "Post") if form.is_valid() else None
        if form.is_valid():
            form.save()
            messages.success(request, f"{title} has been uploaded.")
            return redirect("home")
        messages.error(request, "Please correct the error(s) below.")
    else:
        form = NewsAndEventsForm()
    return render(request, "core/post_add.html", {"title": "Add Post", "form": form})


@api_view(["GET"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsLecturer])
def edit_post(request, pk):
    instance = get_object_or_404(NewsAndEvents, pk=pk)
    if request.method == "POST":
        form = NewsAndEventsForm(request.POST, instance=instance)
        title = form.cleaned_data.get("title", "Post") if form.is_valid() else None
        if form.is_valid():
            form.save()
            messages.success(request, f"{title} has been updated.")
            return redirect("home")
        messages.error(request, "Please correct the error(s) below.")
    else:
        form = NewsAndEventsForm(instance=instance)
    return render(request, "core/post_add.html", {"title": "Edit Post", "form": form})


@api_view(["GET"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsLecturer])
def delete_post(request, pk):
    post = get_object_or_404(NewsAndEvents, pk=pk)
    post_title = post.title
    post.delete()
    messages.success(request, f"{post_title} has been deleted.")
    return redirect("home")


# ########################################################
# Session
# ########################################################
@api_view(["GET"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsLecturer])
def session_list_view(request):
    """Show list of all sessions"""
    sessions = Session.objects.all().order_by("-is_current_session", "-session")
    return render(request, "core/session_list.html", {"sessions": sessions})


@api_view(["GET", "POST"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsLecturer])
def session_add_view(request):
    """Add a new session"""
    if request.method == "POST":
        form = SessionForm(request.POST)
        if form.is_valid():
            if form.cleaned_data.get("is_current_session"):
                unset_current_session()
            form.save()
            messages.success(request, "Session added successfully.")
            return redirect("session_list")
    else:
        form = SessionForm()
    return render(request, "core/session_update.html", {"form": form})


@api_view(["GET", "POST"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsLecturer])
def session_update_view(request, pk):
    session = get_object_or_404(Session, pk=pk)
    if request.method == "POST":
        form = SessionForm(request.POST, instance=session)
        if form.is_valid():
            if form.cleaned_data.get("is_current_session"):
                unset_current_session()
            form.save()
            messages.success(request, "Session updated successfully.")
            return redirect("session_list")
    else:
        form = SessionForm(instance=session)
    return render(request, "core/session_update.html", {"form": form})


@api_view(["DELETE"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsLecturer])
def session_delete_view(request, pk):
    session = get_object_or_404(Session, pk=pk)
    if session.is_current_session:
        messages.error(request, "You cannot delete the current session.")
    else:
        session.delete()
        messages.success(request, "Session successfully deleted.")
    return redirect("session_list")


def unset_current_session():
    """Unset current session"""
    current_session = Session.objects.filter(is_current_session=True).first()
    if current_session:
        current_session.is_current_session = False
        current_session.save()


# ########################################################
# Semester
# ########################################################
@api_view(["GET"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsLecturer])
def semester_list_view(request):
    semesters = Semester.objects.all().order_by("-is_current_semester", "-semester")
    return render(request, "core/semester_list.html", {"semesters": semesters})


@api_view(["GET", "POST"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsLecturer])
def semester_add_view(request):
    if request.method == "POST":
        form = SemesterForm(request.POST)
        if form.is_valid():
            if form.cleaned_data.get("is_current_semester"):
                unset_current_semester()
                unset_current_session()
            form.save()
            messages.success(request, "Semester added successfully.")
            return redirect("semester_list")
    else:
        form = SemesterForm()
    return render(request, "core/semester_update.html", {"form": form})


@api_view(["GET", "POST"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsLecturer])
def semester_update_view(request, pk):
    semester = get_object_or_404(Semester, pk=pk)
    if request.method == "POST":
        form = SemesterForm(request.POST, instance=semester)
        if form.is_valid():
            if form.cleaned_data.get("is_current_semester"):
                unset_current_semester()
                unset_current_session()
            form.save()
            messages.success(request, "Semester updated successfully!")
            return redirect("semester_list")
    else:
        form = SemesterForm(instance=semester)
    return render(request, "core/semester_update.html", {"form": form})


@api_view(["DELETE"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsLecturer])
def semester_delete_view(request, pk):
    semester = get_object_or_404(Semester, pk=pk)
    if semester.is_current_semester:
        messages.error(request, "You cannot delete the current semester.")
    else:
        semester.delete()
        messages.success(request, "Semester successfully deleted.")
    return redirect("semester_list")


def unset_current_semester():
    """Unset current semester"""
    current_semester = Semester.objects.filter(is_current_semester=True).first()
    if current_semester:
        current_semester.is_current_semester = False
        current_semester.save()
