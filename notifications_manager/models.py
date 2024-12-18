from django.db import models

# Create your models here.
class NotificationTemplate(models.Model):
    name = models.CharField(max_length=100)
    subject = models.CharField(max_length=200, blank=True)
    body = models.TextField()
    template_type = models.CharField(max_length=50,unique=True)  # e.g., 'meeting_24h', 'meeting_30m'
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)