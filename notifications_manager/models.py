from django.db import models

# Create your models here.
class NotificationTemplate(models.Model):
    name = models.CharField(max_length=100)
    body = models.TextField()
    template_type = models.CharField(max_length=50,unique=True)  # e.g., 'meeting_24h', 'meeting_30m'
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    

class NotificationConfig(models.Model):
    notification_type = models.CharField(max_length=50)
    hours_before = models.IntegerField(null=True)
    minutes_before = models.IntegerField(null=True)
    mediums = models.JSONField()  # Store list of mediums like ["email", "telegram"]
    template_types = models.JSONField()  # Store mapping like {"email": "meeting_24h_email", "telegram": "meeting_24h_telegram"}
    
    class Meta:
        db_table = "notification_configs"