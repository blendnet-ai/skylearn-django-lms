from django.db import models
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from course.models import Batch
from datetime import timedelta
from django.conf import settings
from Feedback.utils import get_feedback_intervals


class FeedbackForm(models.Model):
    name = models.CharField(max_length=255)
    data = models.JSONField(help_text="The form json")
    is_mandatory = models.BooleanField(default=True)


class CourseFormEntry(models.Model):
    form = models.ForeignKey(FeedbackForm, on_delete=models.CASCADE)
    batch = models.ForeignKey("course.Batch", on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        unique_together = ("form", "batch", "start_date", "end_date")


class FeedbackResponse(models.Model):
    data = models.JSONField(help_text="The filled form json by user")
    user_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    course_feedback_entry = models.ForeignKey(
        CourseFormEntry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )


from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver


@receiver(pre_save, sender=Batch)
def store_old_end_date(sender, instance, **kwargs):
    """Store the old end_date before saving the instance"""
    if instance.id:  # Ensure this is an update, not a new entry
        try:
            old_instance = Batch.objects.get(id=instance.id)
            instance._old_end_date = (
                old_instance.end_date
            )  # Store old value in a temporary attribute
        except Batch.DoesNotExist:
            instance._old_end_date = None


@receiver(post_save, sender=Batch)
def create_feedback_entries(sender, instance, created, **kwargs):
    should_create = False

    if created:
        should_create = instance.form_id is not None
    else:
        # Use the stored old_end_date
        should_create = (
            hasattr(instance, "_old_end_date")
            and instance._old_end_date != instance.end_date
        )

    if should_create and instance.form_id:
        try:
            form = FeedbackForm.objects.get(id=instance.form_id)
            if instance.start_date and instance.end_date:
                intervals = get_feedback_intervals(
                    instance.start_date,
                    instance.end_date,
                    getattr(settings, "FEEDBACK_INTERVAL_DAYS", 7),
                )

                # Delete existing entries only if this is an update
                if not created:
                    CourseFormEntry.objects.filter(batch=instance, form=form).delete()

                for start_date, end_date in intervals:
                    CourseFormEntry.objects.create(
                        form=form,
                        batch=instance,
                        start_date=start_date,
                        end_date=end_date,
                    )
        except FeedbackForm.DoesNotExist:
            pass
