from django.db import models

from django.contrib.postgres.fields import ArrayField


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

    class Meta:
        verbose_name = "Live Class Series"
        verbose_name_plural = "Live Class Series"


class Meeting(models.Model):
    series = models.ForeignKey(MeetingSeries, on_delete=models.CASCADE)
    start_date = models.DateField()
    title_override = models.CharField(max_length=255, null=True, blank=True)
    start_time_override = models.TimeField(null=True, blank=True)
    duration_override = models.DurationField(null=True, blank=True)
    link = models.URLField()
    first_notification_sent = models.BooleanField(default=False)
    second_notification_sent = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.series} - {self.start_date}"

    class Meta:
        verbose_name = "Live Class"
        verbose_name_plural = "Live Classes"
