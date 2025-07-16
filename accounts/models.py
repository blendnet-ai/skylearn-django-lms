
from django.contrib.auth.models import User
from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from django.conf import settings

from course.models import Batch


class UserConfigMapping(models.Model):
    email = models.EmailField(unique=True)
    config = models.JSONField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class CustomUserManager(UserManager):
    def search(self, query=None):
        queryset = self.get_queryset()
        if query is not None:
            or_lookup = (
                Q(username__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(email__icontains=query)
            )
            queryset = queryset.filter(
                or_lookup
            ).distinct()  # distinct() is often necessary with Q lookups
        return queryset

    def get_student_count(self):
        return self.model.objects.filter(is_student=True).count()

    def get_lecturer_count(self):
        return self.model.objects.filter(is_lecturer=True).count()

    def get_superuser_count(self):
        return self.model.objects.filter(is_superuser=True).count()


class User(AbstractUser):
    firebase_uid = models.CharField(max_length=150, unique=True, null=True)
    is_student = models.BooleanField(default=False)
    is_lecturer = models.BooleanField(default=False)
    is_course_provider_admin = models.BooleanField(default=False)
    email = models.EmailField(blank=True, null=True)
    needs_role_assignment = models.BooleanField(default=False)
    objects = CustomUserManager()

    class Meta:
        ordering = ("-date_joined",)

    @property
    def get_full_name(self):
        full_name = self.username
        if self.first_name or self.last_name:
            full_name = self.first_name + " " + self.last_name
        return full_name

    def __str__(self):
        return "{} ({})".format(self.username, self.get_full_name)

    @property
    def get_user_role(self):
        if self.is_superuser:
            role = _("Admin")
        elif self.is_student:
            role = _("Student")
        elif self.is_lecturer:
            role = _("Lecturer")
        elif self.is_course_provider_admin:
            role = _("Course Provider Admin")
        else:
            role = _("User")
        return role


class Student(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 0, "Active"
        INACTIVE = 1, "Inactive"
        SUSPENDED = 2, "Suspended"

    student = models.OneToOneField(User, on_delete=models.CASCADE)
    batches = models.ManyToManyField(Batch, blank=True)
    status = models.IntegerField(choices=Status.choices, default=int(Status.ACTIVE))

    class Meta:
        ordering = ("-student__date_joined",)

    def __str__(self):
        return self.student.get_full_name

    @classmethod
    def get_gender_count(cls):
        males_count = Student.objects.filter(student__gender="M").count()
        females_count = Student.objects.filter(student__gender="F").count()

        return {"M": males_count, "F": females_count}

    def delete(self, *args, **kwargs):
        self.student.delete()
        super().delete(*args, **kwargs)

    @property
    def status_string(self):
        status_map = {0: "Active", 1: "Inactive", 2: "Suspended"}
        return status_map.get(self.status, "Unknown")


class CourseProviderAdmin(models.Model):
    course_provider_admin = models.OneToOneField(User, on_delete=models.CASCADE)


class CourseProvider(models.Model):
    name = models.CharField(max_length=100)

    admins = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='course_providers', blank=True)
    teams_guid = models.CharField(max_length=50, null=False)
    teams_upn = models.CharField(max_length=100, null=False)
    zoom_gmail = models.CharField(max_length=100, null=False)


class Lecturer(models.Model):
    lecturer = models.OneToOneField(User, on_delete=models.CASCADE)
    guid = models.CharField(max_length=50, null=False)
    upn = models.CharField(max_length=100, null=False)
    zoom_gmail = models.CharField(max_length=100, null=False)
    course_provider = models.ForeignKey(CourseProvider, on_delete=models.CASCADE)

    def name(self):
        return f"{self.lecturer.first_name} {self.lecturer.last_name}"

    def presenter_details(self):
        return {
            "guid": self.guid,
            "name": self.name(),
            "upn": self.upn,
            "zoom_gmail": self.zoom_gmail,
        }
