from django.db import models
from accounts.models import User

# Create your models here.
class chats_data(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    telegram_chat_id = models.CharField(max_length=20, null=False, unique=True)