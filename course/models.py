from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import Q
from django.db.models.signals import pre_save, post_delete, post_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from course.utils import unique_slug_generator
from meetings.models import MeetingSeries, Meeting
from storage_service.azure_storage import AzureStorageService


class Module(models.Model):
    title = models.CharField(max_length=200)
    course = models.ForeignKey(
        "Course", related_name="modules_list", on_delete=models.CASCADE
    )
    assignment_configs = models.ManyToManyField(
        "evaluation.AssessmentGenerationConfig", related_name="modules", blank=True
    )
    order_in_course = models.IntegerField(null=True)

    class Meta:
        unique_together = ("course", "order_in_course")

    def __str__(self):
        return self.title


class Course(models.Model):
    slug = models.SlugField(unique=True, blank=True)
    title = models.CharField(max_length=200)
    code = models.CharField(max_length=200, unique=True)
    summary = models.TextField(max_length=200, blank=True)
    course_provider = models.ForeignKey(
        "accounts.courseprovider", on_delete=models.CASCADE
    )
    drive_folder_link = models.CharField(max_length=255, blank=True)
    course_hours = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.title} ({self.code})"

    def get_absolute_url(self):
        return reverse("course_detail", kwargs={"slug": self.slug})


class Batch(models.Model):
    title = models.CharField(max_length=200)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    lecturer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    form = models.ForeignKey(
        "Feedback.FeedbackForm", on_delete=models.CASCADE, null=True, blank=True
    )

    @property
    def students(self):
        return self.student_set.all()


class LiveClassSeriesBatchAllocation(models.Model):
    """Model to handle course allocations for live classes"""

    live_class_series = models.ForeignKey(
        MeetingSeries, on_delete=models.CASCADE, related_name="course_enrollments"
    )
    batch = models.ForeignKey(
        "course.Batch", on_delete=models.CASCADE, related_name="enrolled_batches"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["live_class_series", "batch"]

    def __str__(self):
        return f"{self.live_class_series} - {self.course.title}"


@receiver(post_save, sender=LiveClassSeriesBatchAllocation)
def attendance_record_creater(sender, instance, created, **kwargs):
    if created:
        from .tasks import create_attendance_records_task

        for meeting in Meeting.objects.filter(series=instance.live_class_series):
            create_attendance_records_task.delay(meeting.id)


@receiver(pre_save, sender=Course)
def course_pre_save_receiver(sender, instance, **kwargs):
    if not instance.slug:
        instance.slug = unique_slug_generator(instance)


class CourseAllocation(models.Model):
    lecturer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="allocated_lecturer",
    )
    courses = models.ManyToManyField(Course, related_name="allocated_course")

    def __str__(self):
        return self.lecturer.get_full_name


class Upload(models.Model):
    title = models.CharField(max_length=100)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    module = models.ForeignKey(
        Module, on_delete=models.CASCADE, related_name="uploads", null=True, blank=True
    )  # New field
    # file = models.FileField(
    #     upload_to="course_files/",
    #     help_text=_(
    #         "Valid Files: pdf, docx, doc, xls, xlsx, ppt, pptx, zip, rar, 7zip"
    #     ),
    #     validators=[
    #         FileExtensionValidator(
    #             [
    #                 "pdf",
    #                 "docx",
    #                 "doc",
    #                 "xls",
    #                 "xlsx",
    #                 "ppt",
    #                 "pptx",
    #                 "zip",
    #                 "rar",
    #                 "7zip",
    #             ]
    #         )
    #     ],
    #     null=True
    # )
    blob_url = models.CharField(max_length=255, blank=True)
    updated_date = models.DateTimeField(auto_now=True)
    upload_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title}"

    def get_extension_short(self):
        ext = self.file.name.split(".")[-1].lower()
        if ext in ("doc", "docx"):
            return "word"
        elif ext == "pdf":
            return "pdf"
        elif ext in ("xls", "xlsx"):
            return "excel"
        elif ext in ("ppt", "pptx"):
            return "powerpoint"
        elif ext in ("zip", "rar", "7zip"):
            return "archive"
        return "file"

    def delete(self, *args, **kwargs):
        AzureStorageService().delete_blob(self.blob_url)
        super().delete(*args, **kwargs)


class UploadVideo(models.Model):
    title = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name="video_uploads",
        null=True,
        blank=True,
    )  # New field
    # video = models.FileField(
    #     upload_to="course_videos/",
    #     help_text=_("Valid video formats: mp4, mkv, wmv, 3gp, f4v, avi, mp3"),
    #     validators=[
    #         FileExtensionValidator(["mp4", "mkv", "wmv", "3gp", "f4v", "avi", "mp3"])
    #     ],
    #     max_length=255,
    #     null=True
    # )
    blob_url = models.CharField(max_length=255, blank=True)
    summary = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title}"

    def get_absolute_url(self):
        return reverse(
            "video_single", kwargs={"slug": self.course.slug, "video_slug": self.slug}
        )

    def delete(self, *args, **kwargs):
        # Delete from blob storage
        AzureStorageService().delete_blob(self.blob_url)
        super().delete(*args, **kwargs)


@receiver(pre_save, sender=UploadVideo)
def video_pre_save_receiver(sender, instance, **kwargs):
    if not instance.slug:
        instance.slug = unique_slug_generator(instance)
