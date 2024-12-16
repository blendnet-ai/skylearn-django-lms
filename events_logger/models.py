from django.db import models
from django.conf import settings
from course.models import Upload,UploadVideo
from datetime import time, datetime

class PageEvent(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    upload = models.ForeignKey(Upload, on_delete=models.CASCADE, null=True, blank=True,to_field='id')
    upload_video = models.ForeignKey(UploadVideo, on_delete=models.CASCADE, null=True, blank=True,to_field='id')
    watched=models.BooleanField(default=False)
    time_spent=models.TimeField(default=time(0, 0, 0))
    
    class Meta:
        unique_together = (('user', 'upload', 'upload_video'),)
