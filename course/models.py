from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import Q
from django.db.models.signals import pre_save, post_delete, post_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from core.models import ActivityLog, Semester
from core.utils import unique_slug_generator
from meetings.models import MeetingSeries,Meeting


class ProgramManager(models.Manager):
    def search(self, query=None):
        queryset = self.get_queryset()
        if query:
            or_lookup = Q(title__icontains=query) | Q(summary__icontains=query)
            queryset = queryset.filter(or_lookup).distinct()
        return queryset


class Program(models.Model):
    title = models.CharField(max_length=150, unique=True)
    summary = models.TextField(blank=True)

    objects = ProgramManager()

    def __str__(self):
        return f"{self.title}"

    def get_absolute_url(self):
        return reverse("program_detail", kwargs={"pk": self.pk})


@receiver(post_save, sender=Program)
def log_program_save(sender, instance, created, **kwargs):
    verb = "created" if created else "updated"
    ActivityLog.objects.create(message=_(f"The program '{instance}' has been {verb}."))


@receiver(post_delete, sender=Program)
def log_program_delete(sender, instance, **kwargs):
    ActivityLog.objects.create(message=_(f"The program '{instance}' has been deleted."))


class CourseManager(models.Manager):
    def search(self, query=None):
        queryset = self.get_queryset()
        if query:
            or_lookup = (
                Q(title__icontains=query)
                | Q(summary__icontains=query)
                | Q(code__icontains=query)
                | Q(slug__icontains=query)
            )
            queryset = queryset.filter(or_lookup).distinct()
        return queryset



class Module(models.Model):
    title = models.CharField(max_length=200)
    course = models.ForeignKey('Course', related_name='modules_list', on_delete=models.CASCADE)
    assignment_configs = models.ManyToManyField('evaluation.AssessmentGenerationConfig', related_name='modules', blank=True)
    order_in_course = models.IntegerField(null=True) 
    class Meta:
        unique_together = ('course', 'order_in_course')
    def __str__(self):
        return self.title
    
class Course(models.Model):
    slug = models.SlugField(unique=True, blank=True)
    title = models.CharField(max_length=200)
    code = models.CharField(max_length=200, unique=True)
    credit = models.IntegerField(default=0)
    summary = models.TextField(max_length=200, blank=True)
    level = models.CharField(max_length=25, choices=settings.LEVEL_CHOICES)
    year = models.IntegerField(choices=settings.YEARS, default=1)
    semester = models.CharField(choices=settings.SEMESTER_CHOICES, max_length=200)
    is_elective = models.BooleanField(default=False)
    assessment_generation_ids = models.JSONField(blank=True, default=list)
    course_provider= models.ForeignKey( 'accounts.courseprovider', on_delete=models.CASCADE)
    drive_folder_link = models.CharField(max_length=255, blank=True)

    objects = CourseManager()

    def __str__(self):
        return f"{self.title} ({self.code})"

    def get_absolute_url(self):
        return reverse("course_detail", kwargs={"slug": self.slug})

    @property
    def is_current_semester(self):

        current_semester = Semester.objects.filter(is_current_semester=True).first()
        return self.semester == current_semester.semester if current_semester else False


class Batch(models.Model):
    title = models.CharField(max_length=200)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    lecturer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
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
    

@receiver(post_save,sender=LiveClassSeriesBatchAllocation)
def attendance_record_creater(sender,instance,created,**kwargs):
    if created:
        from meetings.usecases import MeetingUsecase
        for meeting in Meeting.objects.filter(series=instance.live_class_series):
            MeetingUsecase.create_attendace_records(meeting=meeting)


@receiver(pre_save, sender=Course)
def course_pre_save_receiver(sender, instance, **kwargs):
    if not instance.slug:
        instance.slug = unique_slug_generator(instance)


@receiver(post_save, sender=Course)
def log_course_save(sender, instance, created, **kwargs):
    verb = "created" if created else "updated"
    ActivityLog.objects.create(message=_(f"The course '{instance}' has been {verb}."))


@receiver(post_delete, sender=Course)
def log_course_delete(sender, instance, **kwargs):
    ActivityLog.objects.create(message=_(f"The course '{instance}' has been deleted."))


class CourseAllocation(models.Model):
    lecturer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="allocated_lecturer",
    )
    courses = models.ManyToManyField(Course, related_name="allocated_course")
    session = models.ForeignKey(
        "core.Session", on_delete=models.CASCADE, blank=True, null=True
    )

    def __str__(self):
        return self.lecturer.get_full_name

    def get_absolute_url(self):
        return reverse("edit_allocated_course", kwargs={"pk": self.pk})


class Upload(models.Model):
    title = models.CharField(max_length=100)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='uploads', null=True, blank=True)  # New field
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
        self.file.delete(save=False)
        super().delete(*args, **kwargs)


@receiver(post_save, sender=Upload)
def log_upload_save(sender, instance, created, **kwargs):
    if created:
        message = _(
            f"The file '{instance.title}' has been uploaded to the course '{instance.course}'."
        )
    else:
        message = _(
            f"The file '{instance.title}' of the course '{instance.course}' has been updated."
        )
    ActivityLog.objects.create(message=message)


@receiver(post_delete, sender=Upload)
def log_upload_delete(sender, instance, **kwargs):
    ActivityLog.objects.create(
        message=_(
            f"The file '{instance.title}' of the course '{instance.course}' has been deleted."
        )
    )


class UploadVideo(models.Model):
    title = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='video_uploads', null=True, blank=True)  # New field
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
        self.video.delete(save=False)
        super().delete(*args, **kwargs)


@receiver(pre_save, sender=UploadVideo)
def video_pre_save_receiver(sender, instance, **kwargs):
    if not instance.slug:
        instance.slug = unique_slug_generator(instance)


@receiver(post_save, sender=UploadVideo)
def log_uploadvideo_save(sender, instance, created, **kwargs):
    if created:
        message = _(
            f"The video '{instance.title}' has been uploaded to the course '{instance.course}'."
        )
    else:
        message = _(
            f"The video '{instance.title}' of the course '{instance.course}' has been updated."
        )
    ActivityLog.objects.create(message=message)


@receiver(post_delete, sender=UploadVideo)
def log_uploadvideo_delete(sender, instance, **kwargs):
    ActivityLog.objects.create(
        message=_(
            f"The video '{instance.title}' of the course '{instance.course}' has been deleted."
        )
    )


class CourseOffer(models.Model):
    """NOTE: Only department head can offer semester courses"""

    dep_head = models.ForeignKey("accounts.DepartmentHead", on_delete=models.CASCADE)

    def __str__(self):
        return str(self.dep_head)
