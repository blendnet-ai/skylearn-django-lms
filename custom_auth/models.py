from django.db import models
from django.contrib.auth import get_user_model
from datetime import date
import random
import uuid

# from InstituteConfiguration.models import Institute

User = get_user_model()

def generate_random_number():
    # Generates a random number between 100000 and 999999
    return random.randint(100000, 999999)

class Form(models.Model):
    id = models.AutoField(primary_key=True)   
    form_name = models.CharField(max_length=100, unique=True)
    form_data = models.JSONField()
    

class UserProfile (models.Model):
    user_id = models.ForeignKey(User, on_delete=models.CASCADE, to_field='id')
    user_data = models.JSONField(null=True, blank=True)
    onboarding_complete = models.BooleanField(default=False)
    #Sanchit-TODO: to_field is not needed in most casss, only adds confusion. Discuss what is the thought behind this
    form_name = models.ForeignKey(Form, on_delete=models.DO_NOTHING, to_field='form_name', null=True, blank=True)
    name = models.CharField(max_length=100, default=None, null=True, blank=True)
    email = models.EmailField(default=None, null=True, blank=True)
    institute_roll_number = models.CharField(max_length=100, default=None, null=True, blank=True)
    age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, default=None, null=True, blank=True)
    languages = models.TextField(default=None, null=True, blank=True)
    phone = models.CharField(max_length=15, default=None, null=True, blank=True)
    city = models.CharField(max_length=50, default=None, null=True, blank=True)
    country = models.CharField(max_length=50, default=None, null=True, blank=True)
    interests = models.TextField(default=None, null=True, blank=True)
    daily_streak = models.IntegerField(default=0, null=True, blank=True)
    longest_streak = models.IntegerField(default=0, null=True, blank=True)
    last_task_date = models.DateField(null=True, blank=True)
    total_chat_count = models.IntegerField(default=0, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    otp = models.IntegerField(default=generate_random_number)
    cv_details = models.JSONField(null=True, blank=True)
    cv_score = models.IntegerField(null=True, blank=True)
    form_response = models.JSONField(null=True, blank=True)
    #institute = models.ForeignKey(Institute, on_delete=models.SET_NULL, null=True, blank=True)
    activity_dates = models.JSONField(default=list)
    #for doubt solving
    doubt_solving_uuid = models.UUIDField(default=None, editable=False, unique=True, null=True)
    doubt_solving_mapping_created = models.BooleanField(default=False)
    doubt_solving_token=models.CharField(max_length=8,null=True,blank=True)
    token_expiration_time=models.DateTimeField(null=True, blank=True)
    is_telegram_connected = models.BooleanField(default=False)
    is_telegram_onboarding_skipped= models.BooleanField(default=False)
    is_mobile_verified = models.BooleanField(default=False)

    def get_user_details_for_memgpt(self) -> str:
        return f"name={self.name}, email={self.email}, age={self.age}, gender={self.gender}, " \
               f"languages={self.languages}, city={self.city}, country={self.country}, interests={self.interests}"
