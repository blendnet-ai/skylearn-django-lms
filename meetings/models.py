from django.db import models
from django.contrib.postgres.fields import ArrayField
from datetime import datetime, timedelta
from django.db.models.signals import post_save,pre_delete
from django.dispatch import receiver
from .tasks import create_teams_meeting_task, delete_teams_meeting_task, update_teams_meeting_task


class MeetingSeries(models.Model):
    RECURRENCE_TYPE_NOT_REPEATING = "not_repeating"
    RECURRENCE_TYPE_DAILY = "day"
    RECURRENCE_TYPE_WEEKLY = "week"
    RECURRENCE_TYPE_MONTHLY = "month"

    RECURRENCE_CHOICES = [
        (RECURRENCE_TYPE_NOT_REPEATING, "Not Repeating"),
        (RECURRENCE_TYPE_DAILY, "Daily"),
        (RECURRENCE_TYPE_WEEKLY, "Weekly"),
        (RECURRENCE_TYPE_MONTHLY, "Monthly"),
    ]

    title = models.CharField(max_length=255)
    start_time = models.TimeField()
    duration = models.DurationField()
    start_date = models.DateField()
    end_date = models.DateField()
    recurrence_type = models.CharField(
        max_length=20, choices=RECURRENCE_CHOICES, default="not_repeating"
    )
    weekday_schedule = ArrayField(
        models.BooleanField(),
        size=7,
        null=True,
        blank=True,
        help_text="Array of 7 booleans representing each weekday",
    )
    monthly_day = models.IntegerField(
        null=True, blank=True, help_text="Day of month for monthly recurring classes"
    )
    presenter_details = models.JSONField(
        null=True,
        blank=True,
        help_text="JSON containing presenter details (guid, name, email)",
    )

    class Meta:
        verbose_name = "Live Class Series"
        verbose_name_plural = "Live Class Series"


class Meeting(models.Model):
    series = models.ForeignKey(MeetingSeries, on_delete=models.CASCADE)
    start_date = models.DateField()
    title_override = models.CharField(max_length=255, null=True, blank=True)
    start_time_override = models.TimeField(null=True, blank=True)
    duration_override = models.DurationField(null=True, blank=True)
    link = models.URLField(max_length=500, null=True, blank=True)
    conference_id = models.CharField(max_length=255, null=True, blank=True)
    conference_metadata = models.JSONField(null=True, blank=True)
    first_notification_sent = models.BooleanField(default=False)
    second_notification_sent = models.BooleanField(default=False)


    def __str__(self):
        return f"{self.series} - {self.start_date}"

    @property
    def start_time(self) -> datetime:
        """
        Get the effective start time, considering overrides
        Returns combined datetime of start_date and effective start time
        """
        effective_time = self.start_time_override or self.series.start_time
        return datetime.combine(self.start_date, effective_time)

    @property
    def duration(self) -> timedelta:
        """
        Get the effective duration, considering overrides
        """
        return self.duration_override or self.series.duration

    @property
    def end_time(self) -> datetime:
        """
        Calculate the end time based on start time and duration
        """
        return self.start_time + self.duration

    @property
    def title(self) -> str:
        """
        Get the effective title, considering overrides
        """
        return self.title_override or self.series.title

    class Meta:
        verbose_name = "Live Class"
        verbose_name_plural = "Live Classes"


@receiver(post_save, sender=Meeting)
def meeting_post_save(sender, instance, created, **kwargs):
    """
    Signal handler to create Teams meeting when a new meeting is created
    """
    if created:
        create_teams_meeting_task.delay(instance.id)
    elif not created:
        #in case of update created is false
        update_teams_meeting_task.delay(instance.id)

@receiver(pre_delete, sender=Meeting)
def meeting_pre_delete(sender, instance, **kwargs):
    """
    Signal handler to delete Teams meeting when a meeting is deleted
    """
    delete_teams_meeting_task.delay(instance.id,instance.series.presenter_details,instance.conference_id)