from django.conf import settings
from django.db import models
from django.contrib.postgres.fields import ArrayField  # Import ArrayField from the correct module

class UserInfo(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    email = models.EmailField(unique=True)
    telegram_chat_id = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.email


class NotificationIntent(models.Model):
    MEDIUM_CHOICES = [
        ('email', 'Email'),
        ('telegram', 'Telegram'),
    ]
    
    NOTIFICATION_TYPES = [
        ('meeting_24h', 'Meeting 24 Hour Reminder'),
        ('meeting_30m', 'Meeting 30 Minute Reminder'),
        ('user_inactive_past_7_days', 'User 7 Days Inactive Notification')
    ]

    message_template = models.TextField()
    variables = models.JSONField()
    user_ids = models.JSONField()  # List of user IDs
    medium = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    scheduled_at = models.DateTimeField(null=True, blank=True,auto_now=False)
    processed = models.BooleanField(default=False)
    notification_type = models.CharField(max_length=100, choices=NOTIFICATION_TYPES)
    
    # Optional fields for different notification types
    reference_id = models.IntegerField(null=True)  # Can be meeting_id, user_id, or any other entity id

    def __str__(self):
        return f"Intent {self.id} - {self.medium}"


class NotificationRecord(models.Model):
    record_id = models.AutoField(primary_key=True)
    intent = models.ForeignKey(NotificationIntent, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    medium=models.CharField(max_length=20)
    message = models.TextField()
    sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Record {self.record_id} for User {self.user.id}"
