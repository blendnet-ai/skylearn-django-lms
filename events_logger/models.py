from django.db import models
from django.conf import settings
from course.models import Upload,UploadVideo
from meetings.models import Meeting
from datetime import time, datetime, timedelta

class PageEvent(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date=models.DateField()
    pdf = models.ForeignKey(Upload, on_delete=models.CASCADE, null=True, blank=True,to_field='id')
    video = models.ForeignKey(UploadVideo, on_delete=models.CASCADE, null=True, blank=True,to_field='id')
    recording = models.ForeignKey(Meeting, on_delete=models.CASCADE, null=True, blank=True,to_field='id')
    watched=models.BooleanField(default=False)
    time_spent=models.DurationField(default=timedelta())
    
    class Meta:
        unique_together = (('user', 'pdf', 'video','recording','date'),)
